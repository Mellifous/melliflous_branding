# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Customer documents and billing block. No Frappe import.

Billing status is separate from Customer.disabled. A blocked or blacklisted
customer cannot be billed until someone sets the status back to Active.
Aadhaar rows never keep a number.
"""

from __future__ import annotations

from melliflous_branding.targets import as_date

DOCUMENT_TYPES = (
	"GST Certificate",
	"PAN",
	"Aadhaar",
	"Agreement",
	"Cancelled Cheque",
	"Shop Photo",
	"FSSAI Licence",
	"Trade Licence",
	"Other",
)
BILLING_STATUSES = ("Active", "Blocked", "Blacklisted")
BLOCKED_STATUSES = frozenset({"Blocked", "Blacklisted"})
SELLING_DOCTYPES = ("Sales Invoice", "Sales Order", "Quotation", "Delivery Note")
EXPIRY_SOON_DAYS = 30

CUSTOMER_CUSTOM_FIELDS = (
	{
		"fieldname": "custom_billing_status",
		"label": "Billing Status",
		"fieldtype": "Select",
		"options": "Active\nBlocked\nBlacklisted",
		"default": "Active",
		"insert_after": "disabled",
		"in_standard_filter": 1,
		"description": "Separate from Disabled. Blocked and Blacklisted customers cannot be billed until this is set back to Active.",
	},
	{
		"fieldname": "custom_block_reason",
		"label": "Block Reason",
		"fieldtype": "Small Text",
		"insert_after": "custom_billing_status",
		"depends_on": "eval:doc.custom_billing_status=='Blocked' || doc.custom_billing_status=='Blacklisted'",
		"mandatory_depends_on": "eval:doc.custom_billing_status=='Blocked' || doc.custom_billing_status=='Blacklisted'",
	},
	{
		"fieldname": "custom_blocked_by",
		"label": "Blocked By",
		"fieldtype": "Link",
		"options": "User",
		"insert_after": "custom_block_reason",
		"read_only": 1,
	},
	{
		"fieldname": "custom_blocked_on",
		"label": "Blocked On",
		"fieldtype": "Datetime",
		"insert_after": "custom_blocked_by",
		"read_only": 1,
	},
	{
		"fieldname": "custom_documents_tab",
		"label": "Documents",
		"fieldtype": "Tab Break",
		"insert_after": "custom_blocked_on",
	},
	{
		"fieldname": "custom_customer_documents",
		"label": "Documents",
		"fieldtype": "Table",
		"options": "Customer Document",
		"insert_after": "custom_documents_tab",
	},
)


class ComplianceError(ValueError):
	"""A customer document or billing status cannot be saved."""


def clean_text(value) -> str:
	return " ".join(str(value or "").split())


def clean_billing_status(value) -> str:
	text = clean_text(value) or "Active"
	for status in BILLING_STATUSES:
		if status.casefold() == text.casefold():
			return status
	raise ComplianceError("Billing status must be Active, Blocked, or Blacklisted.")


def selling_party(doctype, quotation_to, party_name, customer) -> str:
	"""The customer on a selling document. A quotation for a lead is not a customer."""
	if clean_text(doctype) == "Quotation":
		if clean_text(quotation_to) != "Customer":
			return ""
		return clean_text(party_name)
	return clean_text(customer)


def block_message(customer, status, action) -> str | None:
	"""Why this selling document cannot be saved. Active customers return None."""
	try:
		shown = clean_billing_status(status)
	except ComplianceError:
		shown = "Active"
	if shown not in BLOCKED_STATUSES:
		return None
	who = clean_text(customer) or "This customer"
	step = clean_text(action) or "saving this document"
	return f"{who} is {shown}. Unblock the customer before {step}."


def plan_billing(previous_status, previous_reason, status, reason, user, now, blocked_by=None, blocked_on=None) -> dict:
	"""Fields to store, and a comment when the status or the reason changes.

	Returning to Active clears the reason and the stamp. There is no one-time override.
	"""
	shown = clean_billing_status(status)
	previous = clean_billing_status(previous_status or "Active")
	text = clean_text(reason)
	actor = clean_text(user) or "Someone"
	if shown == "Active":
		comment = None if previous == "Active" else f"{actor} set billing status to Active."
		return {
			"status": "Active",
			"reason": "",
			"blocked_by": None,
			"blocked_on": None,
			"comment": comment,
		}
	if not text:
		raise ComplianceError(f"Enter a block reason. Billing status is {shown}.")
	if previous != shown:
		comment = f"{actor} set billing status to {shown}. Reason: {text}"
		stamp_by, stamp_on = actor, now
	elif clean_text(previous_reason) != text:
		comment = f"{actor} updated the block reason to: {text}"
		stamp_by, stamp_on = blocked_by or actor, blocked_on
	else:
		comment = None
		stamp_by, stamp_on = blocked_by or actor, blocked_on or now
	return {
		"status": shown,
		"reason": text,
		"blocked_by": stamp_by,
		"blocked_on": stamp_on,
		"comment": comment,
	}


def clean_document(row) -> dict:
	"""One child row. Aadhaar keeps the file and never the number."""
	row = row or {}
	kind = clean_text(row.get("document_type"))
	matched = next((name for name in DOCUMENT_TYPES if name.casefold() == kind.casefold()), "")
	if not matched:
		raise ComplianceError("Choose a document type.")
	number = clean_text(row.get("document_no"))
	if matched == "Aadhaar":
		if number:
			raise ComplianceError("Do not store an Aadhaar number. Attach the masked copy only.")
		number = ""
	attach = clean_text(row.get("attach"))
	if not attach:
		raise ComplianceError("Attach the file.")
	return {
		"document_type": matched,
		"attach": attach,
		"document_no": number,
		"valid_till": as_date(row.get("valid_till")),
		"notes": clean_text(row.get("notes")),
	}


def expiry_tone(valid_till, today) -> str:
	"""Expired is red. A date inside the next 30 days is amber. No date stays neutral."""
	day = as_date(valid_till)
	today_day = as_date(today)
	if not day or not today_day:
		return "neutral"
	delta = (day - today_day).days
	if delta < 0:
		return "red"
	if delta < EXPIRY_SOON_DAYS:
		return "amber"
	return "green"


def present_documents(rows, today) -> list:
	shown = []
	for row in rows or []:
		try:
			cleaned = clean_document(row)
		except ComplianceError:
			continue
		tone = expiry_tone(cleaned["valid_till"], today)
		day = cleaned["valid_till"]
		today_day = as_date(today)
		days_left = None if not day or not today_day else (day - today_day).days
		shown.append({**cleaned, "tone": tone, "days_left": days_left})
	rank = {"red": 0, "amber": 1, "green": 2, "neutral": 3}
	shown.sort(key=lambda row: (rank.get(row["tone"], 9), row["document_type"]))
	return shown


def document_summary(rows) -> dict:
	return {
		"total": len(rows or []),
		"expired": sum(1 for row in rows or [] if row.get("tone") == "red"),
		"soon": sum(1 for row in rows or [] if row.get("tone") == "amber"),
	}
