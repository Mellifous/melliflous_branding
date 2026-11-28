# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Who may rename or delete invoices, and which GST auto flags stay off.

No Frappe import. The owner's email is only a seed hint. It never grants access
by itself. Access is the Invoice Admin Users list, plus Administrator.
"""

from __future__ import annotations

INVOICE_DOCTYPES = ("Sales Invoice", "Purchase Invoice")
ROLE_NAME = "Invoice Admin"
SEED_OWNER_EMAIL = "akash@skgourmetspices.com"
DELETION_LOG_LABEL = "Invoice Deletion Log"
DELETION_LOG_DOCTYPE = "Invoice Deletion Log"
# Sales Invoice Delete is not a role grant. Purchase Invoice still keeps it
# only on the Invoice Admin role; the server still requires the settings list.
PURCHASE_DELETE_ROLE = "Invoice Admin"

DELETE_DENIED = "Only an Invoice Admin can rename or delete invoices."
CANCEL_FIRST = "Cancel this invoice before deleting it."
IRN_BLOCKS_DELETE = "This invoice has an IRN. Cancel the e-invoice before deleting it."
DELETE_NEEDS_REASON = "Enter a reason for deletion."
RENAME_NEEDS_REASON = "Enter a reason for renaming this invoice."
LOG_LOCKED = "Only Administrator can change an invoice deletion log."
GST_DELETE_WARNING = (
	"Deleting a submitted or cancelled invoice can break the GST invoice series, "
	"GSTR-1, and any e-invoice or e-way bill. Continue only if GST has been handled."
)

# Turn these off. Never touch enable_* or credentials.
KNOWN_AUTO_FIELDS = (
	"auto_generate_e_invoice",
	"auto_generate_e_waybill",
	"generate_e_waybill_with_e_invoice",
)
PROTECTED_PARTS = ("secret", "password", "credential", "username", "token", "gstin", "api_")


class InvoiceAdminError(PermissionError):
	"""The signed-in user may not rename or delete this invoice."""


def clean(value) -> str:
	return " ".join(str(value or "").split())


def can_manage_invoices(user, listed_users) -> bool:
	"""Administrator, or a user saved on Melliflous Settings. The email alone is not enough."""
	name = clean(user)
	if not name or name == "Guest":
		return False
	if name == "Administrator":
		return True
	allowed = {clean(row) for row in listed_users or [] if clean(row)}
	return name in allowed


def can_delete_invoices(user, listed_users, roles=None) -> bool:
	"""Who may delete a draft or a cancelled invoice.

	Administrator, or a user saved on Melliflous Settings. A role on its own,
	including Invoice Admin, Accounts Manager, and System Manager, does not.
	`roles` is accepted so older callers keep working and is ignored.
	Submitted invoices are still refused by delete_block.
	"""
	del roles
	return can_manage_invoices(user, listed_users)


def role_keeps_invoice_delete(role, doctype="Sales Invoice") -> bool:
	"""Sales Invoice Delete is never kept on a role. Purchase Invoice keeps it on Invoice Admin."""
	if clean(doctype) == "Sales Invoice":
		return False
	return clean(role) == PURCHASE_DELETE_ROLE


def delete_permission_updates(rows, doctype="Sales Invoice") -> list:
	"""Level-0 permission rows whose Delete tick should change.

	Sales Invoice is set to 0 for every role, including Accounts Manager.
	Purchase Invoice stays 1 only for Invoice Admin. Higher permlevels are left alone.
	"""
	updates = []
	for row in rows or []:
		if not isinstance(row, dict):
			continue
		if int(row.get("permlevel") or 0) != 0:
			continue
		wanted = 1 if role_keeps_invoice_delete(row.get("role"), doctype) else 0
		current = 1 if int(row.get("delete") or 0) else 0
		if current == wanted or not row.get("name"):
			continue
		updates.append({"name": row["name"], "delete": wanted})
	return updates


def can_generate_einvoice(user, listed_users, roles) -> bool:
	"""Invoice Admin, System Manager, or Administrator. Everyone else keeps the buttons hidden."""
	if can_manage_invoices(user, listed_users):
		return True
	return "System Manager" in set(roles or [])


def delete_block(user, listed_users, docstatus, irn, roles=None, reason=None, require_reason=False) -> str | None:
	"""None means the delete may proceed. A string is the error to throw."""
	if not can_delete_invoices(user, listed_users, roles):
		return DELETE_DENIED
	status = int(docstatus or 0)
	if status == 1:
		return CANCEL_FIRST
	if clean(irn):
		return IRN_BLOCKS_DELETE
	if require_reason and not clean(reason):
		return DELETE_NEEDS_REASON
	return None


def deletion_status(docstatus) -> str:
	status = int(docstatus or 0)
	if status == 2:
		return "Cancelled"
	if status == 1:
		return "Submitted"
	return "Draft"


def deletion_log_entry(invoice_name, invoice_no, company, customer, posting_date, grand_total, docstatus, reason, user, deleted_on) -> dict:
	"""One permanent row. The invoice number stored here can be offered again."""
	name = clean(invoice_name)
	return {
		"invoice_name": name,
		"invoice_no": clean(invoice_no) or name,
		"company": clean(company),
		"customer": clean(customer),
		"posting_date": posting_date,
		"grand_total": grand_total,
		"status": deletion_status(docstatus),
		"reason": clean(reason),
		"deleted_by": clean(user),
		"deleted_on": deleted_on,
	}


def deletion_log_block(user, is_new=False, deleting=False) -> str | None:
	"""None when this change is allowed. A new row can be inserted. Later edits and deletes cannot."""
	if is_new and not deleting:
		return None
	if clean(user) == "Administrator":
		return None
	return LOG_LOCKED


def deletion_log_shortcut() -> dict:
	return {
		"label": DELETION_LOG_LABEL,
		"link_to": DELETION_LOG_DOCTYPE,
		"type": "DocType",
		"icon": "trash-2",
		"color": "",
		"url": "",
		"stats_filter": "",
		"format": "",
		"doc_view": "List",
	}


def with_deletion_log_shortcut(shortcuts) -> list:
	"""Selling shortcuts plus the deletion log, without a second copy."""
	rows = [dict(row) for row in shortcuts or [] if isinstance(row, dict)]
	if any(clean(row.get("label")) == DELETION_LOG_LABEL for row in rows):
		return rows
	rows.append(deletion_log_shortcut())
	return rows


def rename_block(user, listed_users, docstatus, reason) -> str | None:
	"""Submitted and cancelled invoices need a reason. Drafts do not."""
	if not can_manage_invoices(user, listed_users):
		return DELETE_DENIED
	status = int(docstatus or 0)
	if status != 0 and not clean(reason):
		return RENAME_NEEDS_REASON
	return None


def needs_gst_warning(docstatus) -> bool:
	return int(docstatus or 0) in (1, 2)


def seed_admin_names(administrator_name, users_by_email, roles_by_user) -> list:
	"""Administrator, plus the owner when that user exists and is a System Manager.

	users_by_email maps an email address to the User name. The email does not
	grant access until this name is stored on Melliflous Settings.
	"""
	names = []
	admin = clean(administrator_name)
	if admin:
		names.append(admin)
	for email, name in (users_by_email or {}).items():
		if clean(email).lower() != SEED_OWNER_EMAIL:
			continue
		user_name = clean(name)
		roles = set(roles_by_user.get(user_name) or []) if user_name else set()
		if user_name and "System Manager" in roles and user_name not in names:
			names.append(user_name)
	return names


def gst_flags_to_clear(column_names, allow_auto=False) -> list:
	"""Write these GST Settings checks to 0, including ones the form still shows as the default tick.

	enable_e_invoice, enable_e_waybill, and credentials are not in the list.
	"""
	if allow_auto:
		return []
	# These are the India Compliance v16 GST Settings checks. A missing Singles
	# row makes the form show the field default, which is ticked, so they are
	# written even when the table column list has not caught up.
	forced = (
		"auto_generate_e_invoice",
		"auto_generate_e_waybill",
		"generate_e_waybill_with_e_invoice",
		"auto_cancel_e_invoice",
		"auto_cancel_e_waybill",
	)
	ordered = list(forced)
	for name in auto_fields_to_disable(column_names):
		if name not in ordered:
			ordered.append(name)
	return ordered


def auto_fields_to_disable(column_names) -> list:
	"""GST Settings checks that generate or cancel e-invoice and e-way bill on their own.

	enable_e_invoice, enable_e_waybill, and credential columns are left alone.
	"""
	chosen = []
	for name in column_names or []:
		folded = clean(name).lower()
		if not folded or folded.startswith("enable_"):
			continue
		if any(part in folded for part in PROTECTED_PARTS):
			continue
		if (
			folded in KNOWN_AUTO_FIELDS
			or "auto_generate" in folded
			or "generate_e_waybill_with" in folded
			or "auto_cancel" in folded
		):
			chosen.append(name)
	return chosen


def audit_entry(action, doctype, old_name, new_name, party, grand_total, posting_date, reason, user, timestamp) -> dict:
	return {
		"action": "Delete" if clean(action) == "Delete" else "Rename",
		"invoice_type": clean(doctype),
		"old_name": clean(old_name),
		"new_name": clean(new_name),
		"party": clean(party),
		"grand_total": grand_total,
		"posting_date": posting_date,
		"reason": clean(reason),
		"user": clean(user),
		"timestamp": timestamp,
	}
