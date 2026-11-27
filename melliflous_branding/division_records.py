# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Division field, defaults, and the two seeded MIMT divisions."""

from __future__ import annotations

import frappe
from frappe import _

from melliflous_branding.divisions import (
	MIMT_COMPANY,
	SEEDED_DIVISIONS,
	DivisionError,
	choose_division,
	fields_for,
	validate_division,
)


def ensure_divisions() -> None:
	if not frappe.db.exists("DocType", "Division"):
		return
	_ensure_fields()
	_seed_mimt()


def apply_division(doc, method=None):
	"""Default new documents, then refuse a division from another company."""
	if not _ready(doc):
		return
	meta = frappe.get_meta(doc.doctype)
	is_new = bool(getattr(doc, "is_new", lambda: False)())
	if is_new:
		if meta.has_field("company") and not doc.get("company"):
			doc.company = frappe.defaults.get_user_default("company")
		if not doc.get("division"):
			chosen = frappe.defaults.get_user_default("division")
			if chosen and _belongs(chosen, doc.get("company") if meta.has_field("company") else None):
				doc.division = chosen
	if not doc.get("division") or not meta.has_field("company") or not doc.get("company"):
		return
	company = frappe.db.get_value("Division", doc.division, "company")
	try:
		validate_division(company, doc.company)
	except DivisionError as exc:
		frappe.throw(str(exc))


def divisions_for_boot(company) -> dict:
	if not frappe.db.exists("DocType", "Division"):
		return {"divisions": [], "division": None}
	rows = frappe.get_list(
		"Division",
		filters={"is_active": 1},
		fields=["name", "division_name", "company", "abbreviation", "colour"],
		order_by="division_name asc",
		limit_page_length=200,
	)
	saved = frappe.defaults.get_user_default("division")
	current = choose_division(rows, company, saved)
	return {
		"divisions": [dict(row) for row in rows],
		"division": current or None,
	}


def resolve_division(company, division=None) -> str:
	"""A division of this company the user can see, or blank when the company has none."""
	if not frappe.db.exists("DocType", "Division"):
		return ""
	rows = frappe.get_list(
		"Division",
		filters={"is_active": 1, "company": company},
		fields=["name", "division_name", "company", "is_active"],
		order_by="division_name asc",
		limit_page_length=200,
	)
	return choose_division(rows, company, division)


def _ensure_fields() -> None:
	wanted = [name for name in (
		"Customer",
		"Quotation",
		"Sales Order",
		"Sales Invoice",
		"Delivery Note",
		"Payment Entry",
		"Item",
		"Purchase Order",
		"Purchase Invoice",
		"CRM Lead",
		"CRM Deal",
	) if frappe.db.exists("DocType", name)]
	specs = fields_for(wanted)
	if not specs:
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(specs, update=True)


def _seed_mimt() -> None:
	if not frappe.db.exists("Company", MIMT_COMPANY):
		return
	for row in SEEDED_DIVISIONS:
		if frappe.db.exists("Division", row["division_name"]):
			continue
		frappe.get_doc(
			{
				"doctype": "Division",
				"division_name": row["division_name"],
				"company": MIMT_COMPANY,
				"abbreviation": row["abbreviation"],
				"colour": row["colour"],
				"is_active": 1,
			}
		).insert(ignore_permissions=True)


def _ready(doc) -> bool:
	if not doc or not frappe.db.exists("DocType", "Division"):
		return False
	meta = frappe.get_meta(doc.doctype)
	return bool(meta.has_field("division"))


def _belongs(division, company) -> bool:
	if not division or not frappe.db.exists("Division", division):
		return False
	row = frappe.db.get_value("Division", division, ["company", "is_active"], as_dict=True)
	if not row or not row.is_active:
		return False
	if company and row.company != company:
		return False
	return True
