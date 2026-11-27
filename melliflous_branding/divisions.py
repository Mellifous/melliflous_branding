# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Company and division rules. No Frappe import.

A division belongs to one company. The desk switcher keeps the user's
division inside the company they just picked.
"""

from __future__ import annotations

MIMT_COMPANY = "Melliflous International Multi Trade Pvt Ltd"
SEEDED_DIVISIONS = (
	{"division_name": "SK Gourmet Spices", "abbreviation": "SK", "colour": "#C8102E"},
	{"division_name": "Sunkeera", "abbreviation": "SUN", "colour": "#1F9D55"},
)

# Doctypes that receive a Division link. CRM rows are created only when that
# DocType is installed. Credit notes are Sales Invoices with is_return, so the
# Sales Invoice field covers them.
DIVISION_DOCTYPES = (
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
)
COMPANY_DOCTYPES = frozenset(
	{
		"Quotation",
		"Sales Order",
		"Sales Invoice",
		"Delivery Note",
		"Payment Entry",
		"Purchase Order",
		"Purchase Invoice",
	}
)


class DivisionError(ValueError):
	"""A division does not belong to the document's company."""


def clean(value) -> str:
	return " ".join(str(value or "").split())


def division_field(insert_after, filtered) -> dict:
	row = {
		"fieldname": "division",
		"label": "Division",
		"fieldtype": "Link",
		"options": "Division",
		"insert_after": insert_after,
		"in_standard_filter": 1,
	}
	if filtered:
		row["link_filters"] = '[["Division","company","=","eval:doc.company"]]'
	return row


def fields_for(doctypes) -> dict:
	"""Custom field specs keyed by DocType. Only installed names are passed in."""
	out = {}
	for doctype in doctypes or []:
		filtered = doctype in COMPANY_DOCTYPES
		anchor = "company" if filtered else "customer_name" if doctype == "Customer" else "item_name" if doctype == "Item" else "name"
		out[doctype] = [division_field(anchor, filtered)]
	return out


def choose_division(divisions, company, current) -> str:
	"""Keep the current division when it belongs to the company. Otherwise the first active one."""
	company = clean(company)
	current = clean(current)
	matching = []
	for row in divisions or []:
		if clean(row.get("company")) != company:
			continue
		if row.get("is_active") in (0, "0", False):
			continue
		name = clean(row.get("name") or row.get("division_name"))
		if name:
			matching.append(name)
	matching.sort(key=str.casefold)
	if current and current in matching:
		return current
	return matching[0] if matching else ""


def validate_division(division_company, doc_company) -> None:
	"""Both blank is fine. A division set on a company document has to match."""
	division_company = clean(division_company)
	doc_company = clean(doc_company)
	if division_company and doc_company and division_company != doc_company:
		raise DivisionError(f"Division belongs to {division_company}, not {doc_company}.")
