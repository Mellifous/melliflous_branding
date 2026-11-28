# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Enforce invoice rename and delete, and keep e-invoice generation manual.

The rules live in invoice_admin.py. Running the installer again does not add a
second role, a second permission row, or a second settings user.
"""

from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from melliflous_branding.invoice_admin import (
	INVOICE_DOCTYPES,
	ROLE_NAME,
	SEED_OWNER_EMAIL,
	DELETION_LOG_DOCTYPE,
	DELETION_LOG_LABEL,
	DELETE_DENIED,
	DELETE_NEEDS_REASON,
	audit_entry,
	can_generate_einvoice,
	can_manage_invoices,
	can_delete_invoices,
	delete_block,
	delete_permission_updates,
	deletion_log_entry,
	invoice_admin_row_plan,
	deletion_log_shortcut,
	gst_flags_to_clear,
	rename_block,
	role_keeps_invoice_delete,
	seed_admin_names,
)

SETTINGS = "Melliflous Settings"
ADMIN_CHILD = "Invoice Admin User"


def listed_invoice_admins() -> list:
	"""Saved Invoice Admin users, one row each. The Single's own table is not required."""
	rows = _invoice_admin_rows()
	plan = invoice_admin_row_plan(rows, [])
	return plan["keep"]


def _invoice_admin_rows() -> list:
	if not frappe.db.table_exists(ADMIN_CHILD):
		return []
	return frappe.db.sql(
		f"""select name, user, idx
		    from `tab{ADMIN_CHILD}`
		    where parent=%s
		    order by idx asc, name asc""",
		SETTINGS,
		as_dict=True,
	)


def _roles(user=None) -> list:
	user = user or getattr(frappe.session, "user", None)
	if not user:
		return []
	try:
		return frappe.get_roles(user)
	except Exception:
		return []


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
	# Same people as the settings list. A role by itself does not set this.
	bootinfo.melliflous_can_delete_invoice = 1 if can_delete_invoices(user, listed, roles) else 0
	bootinfo.melliflous_can_einvoice = 1 if can_generate_einvoice(user, listed, roles) else 0
	keep_einvoice_manual()


def guard_delete(doc, method=None):
	if doc.doctype not in INVOICE_DOCTYPES:
		return
	reason = getattr(frappe.flags, "invoice_delete_reason", None)
	message = delete_block(
		getattr(frappe.session, "user", None),
		listed_invoice_admins(),
		doc.get("docstatus"),
		_irn(doc),
		_roles(),
		reason,
		require_reason=doc.doctype == "Sales Invoice",
	)
	if message:
		frappe.throw(_(message), frappe.PermissionError)
	if doc.doctype == "Sales Invoice":
		_write_deletion_log(doc, reason)
	_write_audit(doc, "Delete", doc.name, "", reason or "")
	_comment_party(doc, "Delete", doc.name, "", reason or "")
	frappe.flags.invoice_delete_reason = None


@frappe.whitelist()
def delete_sales_invoices(names, reason=None):
	"""Delete draft or cancelled Sales Invoices. A reason is required.

	Only Administrator and users on the Invoice Admin list may call this.
	The standard Delete permission is off, so this runs with ignore_permissions
	after the list check.
	"""
	reason = " ".join(str(reason or "").split())
	if not reason:
		frappe.throw(_(DELETE_NEEDS_REASON))
	if isinstance(names, str):
		names = frappe.parse_json(names)
	chosen = [" ".join(str(name or "").split()) for name in (names or []) if " ".join(str(name or "").split())]
	if not chosen:
		frappe.throw(_("Select an invoice first."))
	if not can_manage_invoices(getattr(frappe.session, "user", None), listed_invoice_admins()):
		frappe.throw(_(DELETE_DENIED), frappe.PermissionError)
	deleted = []
	for name in chosen:
		_delete_one_sales_invoice(name, reason)
		deleted.append(name)
	return {"deleted": deleted}


@frappe.whitelist()
def may_delete_sales_invoice():
	"""1 when the signed-in user may delete a draft or cancelled Sales Invoice.

	The form asks this on refresh. Boot is not used. The delete itself checks again.
	"""
	allowed = can_manage_invoices(getattr(frappe.session, "user", None), listed_invoice_admins())
	return {"allowed": 1 if allowed else 0}


def _delete_one_sales_invoice(name, reason) -> None:
	if not frappe.db.exists("Sales Invoice", name):
		frappe.throw(_("Invoice {0} was not found.").format(name))
	doc = frappe.get_doc("Sales Invoice", name)
	message = delete_block(
		getattr(frappe.session, "user", None),
		listed_invoice_admins(),
		doc.docstatus,
		_irn(doc),
		_roles(),
		reason,
		require_reason=True,
	)
	if message:
		frappe.throw(_(message), frappe.PermissionError)
	frappe.flags.invoice_delete_reason = reason
	frappe.delete_doc("Sales Invoice", name, ignore_permissions=True)


def guard_rename(doc, method=None, old=None, new=None, merge=False):
	if doc.doctype not in INVOICE_DOCTYPES:
		return
	# Invoice No on a draft, including the save that submits it. The flag is set
	# only for that rename. A submitted invoice with an IRN still needs an Invoice Admin.
	if (
		doc.doctype == "Sales Invoice"
		and int(doc.get("docstatus") or 0) in (0, 1)
		and getattr(frappe.flags, "melliflous_invoice_no_edit", None)
		and not _irn(doc)
	):
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
	if not frappe.db.exists("DocType", "GST Settings"):
		return
	columns = set()
	if frappe.db.table_exists("GST Settings"):
		columns = set(frappe.db.get_table_columns("GST Settings") or [])
	fields = gst_flags_to_clear(columns, allow_auto=False)
	if not fields:
		return
	current = {}
	readable = [name for name in fields if name in columns]
	try:
		if readable:
			current = frappe.db.get_value("GST Settings", "GST Settings", readable, as_dict=True) or {}
	except Exception:
		current = {}
	was_on = [name for name in readable if current.get(name) in (None, "") or cint(current.get(name))]
	if was_on:
		frappe.logger("melliflous_branding").warning(
			"Automatic e-invoice or e-way bill was on or still at the default (%s). Writing 0. "
			"Tick Allow auto e-Invoice/e-Way Bill on Melliflous Settings to keep it.",
			", ".join(was_on),
		)
	for name in fields:
		if not _safe_field(name):
			continue
		_write_single_zero("GST Settings", name)
		if name in columns:
			frappe.db.sql(f"update `tabGST Settings` set `{name}`=0")
	# A desk boot is a GET, and Frappe rolls a GET back. Commit here or the 0 never lands.
	frappe.db.commit()
	frappe.clear_cache(doctype="GST Settings")
	cache = getattr(frappe.db, "value_cache", None)
	if cache is not None:
		cache.pop("GST Settings", None)


def _safe_field(name) -> bool:
	return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(name or "")))


def _write_single_zero(doctype, field) -> None:
	"""Store the string 0. A missing Singles row makes the form use default 1, which is ticked."""
	frappe.db.sql("delete from `tabSingles` where doctype=%s and field=%s", (doctype, field))
	frappe.db.sql(
		"insert into `tabSingles` (`doctype`, `field`, `value`) values (%s, %s, '0')",
		(doctype, field),
	)


def ensure_invoice_admin() -> None:
	"""Role, rename flag, delete rights, and the seeded user list. Safe to repeat."""
	if not frappe.db.exists("DocType", "Role"):
		return
	_ensure_role()
	for doctype in INVOICE_DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			_allow_rename(doctype)
			_restrict_delete(doctype)
	sync_invoice_admin_list()
	keep_einvoice_manual()
	ensure_deletion_log_link()


def revoke_sales_invoice_delete() -> None:
	"""Level-0 Delete on Sales Invoice stays on only for the Invoice Admin role.

	Accounts Manager was ticked by hand and is turned off. System Manager is
	turned off too. Invoice Admin is turned on, so Frappe puts Sales Invoice
	in that user's can_delete list and draws the standard Delete item.
	"""
	if not frappe.db.exists("DocType", "Sales Invoice"):
		return
	for table in ("Custom DocPerm", "DocPerm"):
		if not frappe.db.table_exists(table):
			continue
		rows = frappe.get_all(
			table,
			filters={"parent": "Sales Invoice"},
			fields=["name", "role", "permlevel", "delete"],
		)
		for change in delete_permission_updates(rows, "Sales Invoice"):
			frappe.db.set_value(table, change["name"], "delete", change["delete"], update_modified=False)
	frappe.clear_cache(doctype="Sales Invoice")


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
			if cint(copied.get("permlevel")) == 0:
				copied["delete"] = 1 if role_keeps_invoice_delete(copied.get("role"), doctype) else 0
			frappe.get_doc(copied).insert(ignore_permissions=True)
		custom_rows = frappe.get_all(
			"Custom DocPerm",
			filters={"parent": doctype},
			fields=["name", "role", "permlevel", "delete"],
		)
	for change in delete_permission_updates(custom_rows, doctype):
		frappe.db.set_value("Custom DocPerm", change["name"], "delete", change["delete"], update_modified=False)
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
			"delete": 1 if role_keeps_invoice_delete(ROLE_NAME, doctype) else 0,
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


def sync_invoice_admin_list() -> None:
	"""Drop duplicate and blank Invoice Admin rows, then add akash once.

	Reads the child table directly and writes only the rows that are missing
	or repeated. A second run finds one Administrator and one akash and saves
	nothing. Saving the Settings document is avoided, because that save was
	appending the same two users again.
	"""
	if not frappe.db.table_exists(ADMIN_CHILD) or not frappe.db.exists("DocType", SETTINGS):
		return
	if not frappe.db.exists(SETTINGS, SETTINGS):
		return
	plan = invoice_admin_row_plan(_invoice_admin_rows(), _required_invoice_admins())
	for name in plan["delete"]:
		frappe.db.delete(ADMIN_CHILD, {"name": name})
	if plan["add"]:
		existing = _invoice_admin_rows()
		idx = max([int(row.idx or 0) for row in existing] or [0])
		have = { " ".join(str(row.user or "").split()).casefold() for row in existing if row.user }
		for user in plan["add"]:
			if user.casefold() in have:
				continue
			if user != "Administrator" and not frappe.db.exists("User", user):
				continue
			idx += 1
			frappe.get_doc(
				{
					"doctype": ADMIN_CHILD,
					"parent": SETTINGS,
					"parenttype": SETTINGS,
					"parentfield": "invoice_admin_users",
					"user": user,
					"idx": idx,
				}
			).insert(ignore_permissions=True)
			have.add(user.casefold())
	_sync_roles(set(listed_invoice_admins()))


def _required_invoice_admins() -> list:
	users_by_email = {}
	if frappe.db.table_exists("User"):
		rows = frappe.get_all(
			"User",
			or_filters=[
				["email", "=", SEED_OWNER_EMAIL],
				["name", "=", SEED_OWNER_EMAIL],
			],
			fields=["name", "email"],
		)
		for row in rows:
			users_by_email[row.email or row.name] = row.name
	return seed_admin_names("Administrator", users_by_email, {})


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


def _write_deletion_log(doc, reason) -> None:
	"""Permanent row. A failure here stops the delete so the number is not lost."""
	if not frappe.db.table_exists(DELETION_LOG_DOCTYPE):
		frappe.throw(_("The invoice deletion log is not ready. Update the site, then delete the invoice."))
	number = " ".join(str(doc.get("custom_invoice_no") or doc.name or "").split())
	entry = deletion_log_entry(
		doc.name,
		number,
		doc.get("company"),
		doc.get("customer"),
		doc.get("posting_date"),
		doc.get("grand_total"),
		doc.get("docstatus"),
		reason,
		getattr(frappe.session, "user", None),
		now_datetime(),
	)
	frappe.get_doc({"doctype": DELETION_LOG_DOCTYPE, **entry}).insert(ignore_permissions=True)


def ensure_deletion_log_link() -> None:
	"""Show the log on the Selling workspace and the Melliflous sidebar."""
	_ensure_deletion_sidebar()
	_ensure_selling_shortcut()


def _ensure_deletion_sidebar() -> None:
	if not frappe.db.exists("Sidebar", "Melliflous Branding"):
		return
	doc = frappe.get_doc("Sidebar", "Melliflous Branding")
	have = {(row.link_type, row.link_to) for row in (doc.items or [])}
	if ("DocType", DELETION_LOG_DOCTYPE) in have:
		return
	doc.append(
		"items",
		{
			"type": "Link",
			"label": DELETION_LOG_LABEL,
			"link_type": "DocType",
			"link_to": DELETION_LOG_DOCTYPE,
			"icon": "trash-2",
			"hidden": 0,
		},
	)
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)


def _ensure_selling_shortcut() -> None:
	if not frappe.db.table_exists("Workspace") or not frappe.db.exists("Workspace", "Selling"):
		return
	doc = frappe.get_doc("Workspace", "Selling")
	original = doc.modified
	if any(" ".join(str(row.label or "").split()) == DELETION_LOG_LABEL for row in (doc.shortcuts or [])):
		return
	doc.append("shortcuts", deletion_log_shortcut())
	try:
		content = frappe.parse_json(doc.content) if doc.content else []
	except Exception:
		content = []
	if isinstance(content, list):
		content.append(
			{
				"id": "mb-invoice-deletion-log",
				"type": "shortcut",
				"data": {"shortcut_name": DELETION_LOG_LABEL, "col": 3},
			}
		)
		doc.content = frappe.as_json(content)
	link_labels = {" ".join(str(row.label or "").split()) for row in (doc.links or [])}
	if DELETION_LOG_LABEL not in link_labels:
		doc.append(
			"links",
			{
				"type": "Link",
				"label": DELETION_LOG_LABEL,
				"link_type": "DocType",
				"link_to": DELETION_LOG_DOCTYPE,
				"hidden": 0,
				"is_query_report": 0,
				"link_count": 0,
				"onboard": 0,
			},
		)
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.flags.ignore_mandatory = True
	doc.save(ignore_permissions=True)
	if original:
		frappe.db.sql("update `tabWorkspace` set modified=%s where name=%s", (original, "Selling"))


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
