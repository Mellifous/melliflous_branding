# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Enforce invoice rename and delete, and keep e-invoice generation manual.

The rules live in invoice_admin.py. Running the installer again does not add a
second role, a second permission row, or a second settings user.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from melliflous_branding.invoice_admin import (
	INVOICE_DOCTYPES,
	ROLE_NAME,
	SEED_OWNER_EMAIL,
	audit_entry,
	can_generate_einvoice,
	can_manage_invoices,
	delete_block,
	gst_flags_to_clear,
	rename_block,
	seed_admin_names,
)

SETTINGS = "Melliflous Settings"
ADMIN_CHILD = "Invoice Admin User"


def listed_invoice_admins() -> list:
	if not frappe.db.table_exists(ADMIN_CHILD) or not frappe.db.table_exists(SETTINGS):
		return []
	return frappe.get_all(ADMIN_CHILD, filters={"parent": SETTINGS}, pluck="user") or []


def is_invoice_admin(user=None) -> bool:
	user = user or getattr(frappe.session, "user", None)
	return can_manage_invoices(user, listed_invoice_admins())


def allow_auto_einvoice() -> bool:
	try:
		if not frappe.db.table_exists(SETTINGS):
			return False
		if not frappe.db.has_column(SETTINGS, "allow_auto_einvoice"):
			return False
		return bool(cint(frappe.db.get_single_value(SETTINGS, "allow_auto_einvoice")))
	except Exception:
		return False


def apply_invoice_boot(bootinfo) -> None:
	user = getattr(frappe.session, "user", None)
	try:
		roles = frappe.get_roles(user) if user else []
	except Exception:
		roles = []
	listed = []
	try:
		listed = listed_invoice_admins()
	except Exception:
		frappe.logger("melliflous_branding").exception("Could not read Invoice Admin users")
	bootinfo.melliflous_invoice_admin = 1 if can_manage_invoices(user, listed) else 0
	bootinfo.melliflous_can_einvoice = 1 if can_generate_einvoice(user, listed, roles) else 0
	keep_einvoice_manual()


def guard_delete(doc, method=None):
	if doc.doctype not in INVOICE_DOCTYPES:
		return
	message = delete_block(
		getattr(frappe.session, "user", None),
		listed_invoice_admins(),
		doc.get("docstatus"),
		_irn(doc),
	)
	if message:
		frappe.throw(_(message), frappe.PermissionError)
	_write_audit(doc, "Delete", doc.name, "")
	_comment_party(doc, "Delete", doc.name, "")


def guard_rename(doc, method=None, old=None, new=None, merge=False):
	if doc.doctype not in INVOICE_DOCTYPES:
		return
	reason = getattr(frappe.flags, "invoice_rename_reason", None)
	message = rename_block(
		getattr(frappe.session, "user", None),
		listed_invoice_admins(),
		doc.get("docstatus"),
		reason,
	)
	if message:
		frappe.throw(_(message), frappe.PermissionError)


def log_rename(doc, method=None, old=None, new=None, merge=False):
	if doc.doctype not in INVOICE_DOCTYPES or not old:
		return
	reason = getattr(frappe.flags, "invoice_rename_reason", None) or ""
	_write_audit(doc, "Rename", old, new or doc.name, reason)
	_comment_party(doc, "Rename", old, new or doc.name, reason)
	frappe.flags.invoice_rename_reason = None


@frappe.whitelist()
def rename_invoice(doctype, old, new, reason=None):
	"""Rename one invoice. Submitted and cancelled invoices require a reason."""
	doctype = " ".join(str(doctype or "").split())
	old = " ".join(str(old or "").split())
	new = " ".join(str(new or "").split())
	if doctype not in INVOICE_DOCTYPES:
		frappe.throw(_("Choose a Sales Invoice or a Purchase Invoice."))
	if not old or not new:
		frappe.throw(_("Enter the current number and the new number."))
	if not frappe.db.exists(doctype, old):
		frappe.throw(_("Invoice {0} was not found.").format(old))
	doc = frappe.get_doc(doctype, old)
	message = rename_block(
		getattr(frappe.session, "user", None),
		listed_invoice_admins(),
		doc.docstatus,
		reason,
	)
	if message:
		frappe.throw(_(message), frappe.PermissionError)
	frappe.flags.invoice_rename_reason = " ".join(str(reason or "").split())
	from frappe.model.rename_doc import rename_doc

	rename_doc(doctype, old, new, force=True)
	return {"name": new}


def keep_einvoice_manual() -> None:
	"""Turn automatic IRN and e-way bill generation off unless the setting allows it.

	enable_e_invoice, enable_e_waybill, and the API credentials are not changed.
	A flag that was switched back on is logged, then switched off again.
	"""
	if allow_auto_einvoice():
		return
	if not frappe.db.table_exists("GST Settings") or not frappe.db.exists("GST Settings", "GST Settings"):
		return
	columns = set(frappe.db.get_table_columns("GST Settings") or [])
	fields = gst_flags_to_clear(columns, allow_auto=False)
	if not fields:
		return
	current = frappe.db.get_value("GST Settings", "GST Settings", fields, as_dict=True) or {}
	# A missing tabSingles value comes back empty, and the form then shows the
	# DocType default, which is ticked. Always write 0 so the tick cannot remain.
	was_on = [name for name in fields if current.get(name) in (None, "") or cint(current.get(name))]
	if was_on:
		frappe.logger("melliflous_branding").warning(
			"Automatic e-invoice or e-way bill was on or still at the default (%s). Turning it off. "
			"Tick Allow auto e-Invoice/e-Way Bill on Melliflous Settings to keep it.",
			", ".join(was_on),
		)
	for name in fields:
		frappe.db.set_single_value("GST Settings", name, 0, update_modified=False)
		if frappe.db.has_column("GST Settings", name):
			frappe.db.set_value("GST Settings", "GST Settings", name, 0, update_modified=False)
	frappe.clear_cache(doctype="GST Settings")


def ensure_invoice_admin() -> None:
	"""Role, rename flag, delete rights, and the seeded user list. Safe to repeat."""
	if not frappe.db.exists("DocType", "Role"):
		return
	_ensure_role()
	for doctype in INVOICE_DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			_allow_rename(doctype)
			_restrict_delete(doctype)
	_seed_users()
	keep_einvoice_manual()


def _ensure_role() -> None:
	if frappe.db.exists("Role", ROLE_NAME):
		return
	role = frappe.get_doc({"doctype": "Role", "role_name": ROLE_NAME, "desk_access": 1})
	role.insert(ignore_permissions=True)


def _allow_rename(doctype) -> None:
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	make_property_setter(
		doctype,
		"",
		"allow_rename",
		"1",
		"Check",
		for_doctype=True,
		validate_fields_for_doctype=False,
	)


def _restrict_delete(doctype) -> None:
	"""Clear delete on every other role. Copy standard perms into Custom DocPerm once.

	Frappe uses Custom DocPerm instead of DocPerm as soon as one custom row exists,
	so the first run copies the current rows and only then adds Invoice Admin.
	Cancel and amend are copied as they are.
	"""
	if not frappe.db.table_exists("Custom DocPerm"):
		return
	custom_rows = frappe.get_all(
		"Custom DocPerm",
		filters={"parent": doctype},
		fields=["name", "role", "permlevel", "delete"],
	)
	if not custom_rows:
		for row in frappe.get_all("DocPerm", filters={"parent": doctype}, fields=["*"]):
			copied = {key: row.get(key) for key in row if key not in {"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx"}}
			copied["doctype"] = "Custom DocPerm"
			copied["parent"] = doctype
			copied["parenttype"] = "DocType"
			copied["parentfield"] = "permissions"
			if cint(copied.get("permlevel")) == 0 and copied.get("role") != ROLE_NAME:
				copied["delete"] = 0
			frappe.get_doc(copied).insert(ignore_permissions=True)
		custom_rows = frappe.get_all(
			"Custom DocPerm",
			filters={"parent": doctype},
			fields=["name", "role", "permlevel", "delete"],
		)
	for row in custom_rows:
		if cint(row.permlevel) == 0 and row.role != ROLE_NAME and cint(row.delete):
			frappe.db.set_value("Custom DocPerm", row.name, "delete", 0, update_modified=False)
	if any(row.role == ROLE_NAME and cint(row.permlevel) == 0 for row in custom_rows):
		return
	template = frappe.db.get_value(
		"Custom DocPerm",
		{"parent": doctype, "role": "System Manager", "permlevel": 0},
		["cancel", "amend", "submit", "create"],
		as_dict=True,
	) or {}
	frappe.get_doc(
		{
			"doctype": "Custom DocPerm",
			"parent": doctype,
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": ROLE_NAME,
			"permlevel": 0,
			"read": 1,
			"write": 1,
			"create": cint(template.get("create", 1)),
			"delete": 1,
			"submit": cint(template.get("submit", 1)),
			"cancel": cint(template.get("cancel", 1)),
			"amend": cint(template.get("amend", 1)),
			"print": 1,
			"email": 1,
			"report": 1,
			"export": 1,
			"share": 1,
		}
	).insert(ignore_permissions=True)


def _seed_users() -> None:
	if not frappe.db.table_exists(ADMIN_CHILD):
		return
	users_by_email = {}
	roles_by_user = {}
	if frappe.db.table_exists("User"):
		for row in frappe.get_all("User", filters={"email": SEED_OWNER_EMAIL}, fields=["name", "email"]):
			users_by_email[row.email] = row.name
			roles_by_user[row.name] = frappe.get_roles(row.name)
	wanted = seed_admin_names("Administrator", users_by_email, roles_by_user)
	already = {" ".join(str(name or "").split()).casefold() for name in listed_invoice_admins()}
	if not frappe.db.exists(SETTINGS, SETTINGS):
		return
	doc = frappe.get_doc(SETTINGS)
	changed = False
	for name in wanted:
		if name.casefold() in already:
			continue
		if name != "Administrator" and not frappe.db.exists("User", name):
			continue
		doc.append("invoice_admin_users", {"user": name})
		already.add(name.casefold())
		changed = True
	if changed:
		doc.flags.ignore_permissions = True
		frappe.flags.melliflous_settings_sync = True
		try:
			doc.save(ignore_permissions=True)
		finally:
			frappe.flags.melliflous_settings_sync = False
	_sync_roles(set(listed_invoice_admins()))


def sync_invoice_admin_roles() -> None:
	"""Give the Invoice Admin role to the saved users, and take it off anyone removed."""
	if not frappe.db.exists("Role", ROLE_NAME):
		return
	_sync_roles(set(listed_invoice_admins()))


def _sync_roles(wanted) -> None:
	wanted = {name for name in wanted if name and name != "Administrator" and frappe.db.exists("User", name)}
	if not frappe.db.table_exists("Has Role"):
		return
	current = frappe.get_all(
		"Has Role",
		filters={"role": ROLE_NAME, "parenttype": "User"},
		fields=["name", "parent"],
	)
	for row in current:
		if row.parent not in wanted:
			frappe.db.delete("Has Role", row.name)
	for name in wanted:
		if any(row.parent == name for row in current):
			continue
		user = frappe.get_doc("User", name)
		user.add_roles(ROLE_NAME)


def _irn(doc) -> str:
	return " ".join(str(doc.get("irn") or "").split())


def _party(doc) -> str:
	return " ".join(str(doc.get("customer") or doc.get("supplier") or "").split())


def _write_audit(doc, action, old, new, reason="") -> None:
	if not frappe.db.table_exists("Invoice Audit Log"):
		return
	entry = audit_entry(
		action,
		doc.doctype,
		old,
		new,
		_party(doc),
		doc.get("grand_total"),
		doc.get("posting_date"),
		reason,
		getattr(frappe.session, "user", None),
		now_datetime(),
	)
	try:
		frappe.get_doc({"doctype": "Invoice Audit Log", **entry}).insert(ignore_permissions=True)
	except Exception:
		frappe.logger("melliflous_branding").exception("Could not write the invoice audit log")


def _comment_party(doc, action, old, new, reason="") -> None:
	party = _party(doc)
	party_type = "Customer" if doc.get("customer") else "Supplier" if doc.get("supplier") else ""
	if not party or not party_type or not frappe.db.exists(party_type, party):
		return
	text = f"{getattr(frappe.session, 'user', '')} {action.lower()}d invoice {old}"
	if new and new != old:
		text += f" to {new}"
	if reason:
		text += f". Reason: {reason}"
	try:
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": party_type,
				"reference_name": party,
				"content": text,
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.logger("melliflous_branding").exception("Could not comment on the invoice party")
