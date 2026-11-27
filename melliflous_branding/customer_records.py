# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Install customer document and billing fields, and refuse blocked customers.

The rules live in customer_compliance.py. Running the installer again updates
the same custom fields and does not add a second copy.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from melliflous_branding.customer_compliance import (
	CUSTOMER_CUSTOM_FIELDS,
	ComplianceError,
	block_message,
	clean_billing_status,
	clean_document,
	plan_billing,
	selling_party,
)


def ensure_customer_fields() -> None:
	"""Create or update the Customer custom fields. Safe to run more than once."""
	if not frappe.db.exists("DocType", "Customer") or not frappe.db.exists("DocType", "Customer Document"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Customer": [dict(row) for row in CUSTOMER_CUSTOM_FIELDS]}, update=True)


def validate_customer(doc, method=None):
	if not _has_billing_column():
		return
	previous_status, previous_reason, previous_by, previous_on = _previous_billing(doc)
	try:
		planned = plan_billing(
			previous_status,
			previous_reason,
			doc.get("custom_billing_status"),
			doc.get("custom_block_reason"),
			getattr(frappe.session, "user", None),
			now_datetime(),
			previous_by,
			previous_on,
		)
	except ComplianceError as exc:
		frappe.throw(str(exc), frappe.ValidationError)
	doc.custom_billing_status = planned["status"]
	doc.custom_block_reason = planned["reason"]
	doc.custom_blocked_by = planned["blocked_by"]
	doc.custom_blocked_on = planned["blocked_on"]
	doc.flags.billing_comment = planned["comment"]
	_validate_document_rows(doc)


def remember_billing_change(doc, method=None):
	"""A comment on the customer, plus the version row Frappe already stores."""
	comment = getattr(doc.flags, "billing_comment", None) if getattr(doc, "flags", None) else None
	if not comment or not doc.name:
		return
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Customer",
			"reference_name": doc.name,
			"content": comment,
		}
	).insert(ignore_permissions=True)


def block_selling(doc, method=None):
	"""Stop save and submit. Unblock the customer first. There is no one-time bypass."""
	if not _has_billing_column():
		return
	party = selling_party(doc.doctype, doc.get("quotation_to"), doc.get("party_name"), doc.get("customer"))
	if not party or not frappe.db.exists("Customer", party):
		return
	info = customer_billing(party)
	message = block_message(party, info["status"], f"saving this {doc.doctype}")
	if message:
		frappe.throw(_(message), frappe.ValidationError)


def customer_billing(name) -> dict:
	"""Status for one customer. Missing fields mean Active, not disabled."""
	name = " ".join(str(name or "").split())
	if not name or not _has_billing_column() or not frappe.db.exists("Customer", name):
		return {"status": "Active", "reason": "", "message": None}
	status, reason = frappe.db.get_value(
		"Customer", name, ["custom_billing_status", "custom_block_reason"]
	) or (None, None)
	shown = clean_billing_status(status)
	return {
		"status": shown,
		"reason": reason or "",
		"message": block_message(name, shown, "creating this draft"),
	}


@frappe.whitelist()
def add_customer_document(customer, document_type, attach, document_no=None, valid_till=None, notes=None):
	"""Append one file on the customer. Aadhaar is stored without a number."""
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	customer = " ".join(str(customer or "").split())
	if not customer or not frappe.db.exists("Customer", customer):
		frappe.throw(_("Pick a customer."))
	if not frappe.has_permission("Customer", "write", customer):
		frappe.throw(_("You cannot add documents for this customer."), frappe.PermissionError)
	try:
		cleaned = clean_document(
			{
				"document_type": document_type,
				"attach": attach,
				"document_no": document_no,
				"valid_till": valid_till,
				"notes": notes,
			}
		)
	except ComplianceError as exc:
		frappe.throw(str(exc), frappe.ValidationError)
	doc = frappe.get_doc("Customer", customer)
	doc.append(
		"custom_customer_documents",
		{
			"document_type": cleaned["document_type"],
			"attach": cleaned["attach"],
			"document_no": cleaned["document_no"],
			"valid_till": cleaned["valid_till"],
			"notes": cleaned["notes"],
		},
	)
	doc.save()
	return {"customer": doc.name, "documents": len(doc.get("custom_customer_documents") or [])}


def _validate_document_rows(doc):
	rows = []
	for row in doc.get("custom_customer_documents") or []:
		try:
			cleaned = clean_document(row)
		except ComplianceError as exc:
			frappe.throw(str(exc), frappe.ValidationError)
		row.document_type = cleaned["document_type"]
		row.document_no = cleaned["document_no"]
		row.attach = cleaned["attach"]
		row.notes = cleaned["notes"]
		rows.append(cleaned)
	return rows


def _has_billing_column() -> bool:
	if not frappe.db.table_exists("Customer"):
		return False
	columns = set(frappe.db.get_table_columns("Customer") or [])
	return "custom_billing_status" in columns


def _previous_billing(doc):
	if doc.is_new() or not doc.name or not frappe.db.exists("Customer", doc.name):
		return "Active", "", None, None
	row = frappe.db.get_value(
		"Customer",
		doc.name,
		["custom_billing_status", "custom_block_reason", "custom_blocked_by", "custom_blocked_on"],
		as_dict=True,
	)
	if not row:
		return "Active", "", None, None
	return row.custom_billing_status, row.custom_block_reason, row.custom_blocked_by, row.custom_blocked_on
