# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Save a draft Sales Invoice or Quotation from Quick Invoice.

The document is inserted and left in Draft. This module never calls submit.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, today

from melliflous_branding.access import require_desk_user
from melliflous_branding.invoices import (
	ITEM_TAX_5,
	MIMT_COMPANY,
	InvoiceError,
	choose_price_list,
	choose_taxes_template,
	exclusive_rate,
	is_classic_price_list,
	is_five_percent,
	price_list_choices,
	validate_draft,
)

DRAFT_DOCTYPES = {"Sales Invoice": "Sales Invoice", "Quotation": "Quotation"}


@frappe.whitelist()
def form_options(customer: str | None = None) -> dict:
	"""Price lists for the form, and the one to select for this customer."""
	require_desk_user()
	customer = " ".join(str(customer or "").split())
	default = ""
	if customer and frappe.db.exists("Customer", customer):
		default = frappe.db.get_value("Customer", customer, "default_price_list") or ""
	existing = []
	if frappe.db.exists("DocType", "Price List"):
		existing = frappe.get_all("Price List", filters={"selling": 1, "enabled": 1}, pluck="name")
	return {
		"company": MIMT_COMPANY,
		"price_lists": price_list_choices(default),
		"price_list": choose_price_list(default, existing),
		"item_tax_template": ITEM_TAX_5,
	}


@frappe.whitelist()
def item_quote(item_code: str, price_list: str, customer: str | None = None, qty: str | float | None = None) -> dict:
	"""Rate before GST, the item tax, and the batch last used on a bill."""
	require_desk_user()
	item_code = " ".join(str(item_code or "").split())
	price_list = " ".join(str(price_list or "").split())
	customer = " ".join(str(customer or "").split())
	if not item_code:
		frappe.throw(_("Pick an item."))
	if not frappe.db.exists("Item", item_code):
		frappe.throw(_("That item is not on this site. Search again and pick one from the list."))
	if not price_list:
		frappe.throw(_("Choose a price list."))
	details = _item_details(item_code, price_list, customer, qty or 1)
	raw_rate = flt(details.get("price_list_rate") or details.get("rate") or 0)
	template = details.get("item_tax_template") or ""
	percent = _tax_percent(template)
	try:
		rate = exclusive_rate(raw_rate, price_list, percent)
	except InvoiceError as error:
		frappe.throw(_(str(error)))
	return {
		"item_code": item_code,
		"item_name": details.get("item_name") or frappe.db.get_value("Item", item_code, "item_name") or item_code,
		"rate": rate,
		"price_list_rate": raw_rate,
		"tax_percent": percent if percent is not None else 0,
		"item_tax_template": template,
		"batch_no": _last_batch(item_code),
		"uom": details.get("uom") or details.get("stock_uom") or "",
		"inclusive": bool(is_classic_price_list(price_list) and is_five_percent(percent)),
	}


@frappe.whitelist(methods=["POST"])
def save_draft(payload) -> dict:
	"""Create a draft Sales Invoice or Quotation and return its name.

	`payload` is the form: customer, price_list, doctype, and items.
	doctype is Sales Invoice unless it is Quotation. The document is not submitted.
	"""
	require_desk_user()
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	payload = payload or {}
	doctype = " ".join(str(payload.get("doctype") or "Sales Invoice").split())
	if doctype not in DRAFT_DOCTYPES:
		frappe.throw(_("Choose an invoice or a quotation."))
	errors = validate_draft(payload)
	if errors:
		frappe.throw(_(errors[0]))
	if not frappe.has_permission(doctype, "create"):
		frappe.throw(_("You are not allowed to create a {0}.").format(doctype), frappe.PermissionError)
	_require_company()
	customer = " ".join(str(payload.get("customer") or "").split())
	price_list = " ".join(str(payload.get("price_list") or "").split())
	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("That customer is not on this site. Search again and pick one from the list."))
	if not frappe.db.exists("Price List", price_list):
		frappe.throw(
			_("The price list {0} is not on this site yet. Pick another, or ask an admin to add it.").format(
				price_list
			)
		)
	prepared = _prepare_rows(payload.get("items") or [], price_list, customer)
	doc = _build_doc(doctype, customer, price_list, prepared)
	doc.insert()
	return {
		"name": doc.name,
		"doctype": doc.doctype,
		"message": _("Draft {0} {1} saved. It is not submitted.").format(doctype, doc.name),
	}


def _require_company() -> None:
	if not frappe.db.exists("Company", MIMT_COMPANY):
		frappe.throw(_("Company {0} is not on this site.").format(MIMT_COMPANY))


def _prepare_rows(items, price_list, customer) -> list[dict]:
	prepared = []
	for index, row in enumerate(items, start=1):
		row = row or {}
		item_code = " ".join(str(row.get("item_code") or "").split())
		if not frappe.db.exists("Item", item_code):
			frappe.throw(_("Row {0}: that item is not on this site.").format(index))
		details = _item_details(item_code, price_list, customer, row.get("qty") or 1)
		template = details.get("item_tax_template") or ""
		percent = _tax_percent(template)
		raw_rate = flt(details.get("price_list_rate") or details.get("rate") or 0)
		try:
			rate = exclusive_rate(raw_rate, price_list, percent)
		except InvoiceError as error:
			frappe.throw(_(str(error)))
		batch = " ".join(str(row.get("batch_no") or "").split()) or _last_batch(item_code)
		if batch and not frappe.db.exists("Batch", batch):
			frappe.throw(_("Row {0}: batch {1} is not on this site.").format(index, batch))
		prepared.append(
			{
				"item_code": item_code,
				"qty": flt(row.get("qty")),
				"rate": rate,
				"uom": details.get("uom") or details.get("stock_uom"),
				"item_tax_template": template,
				"batch_no": batch,
				"tax_percent": percent,
			}
		)
	return prepared


def _build_doc(doctype: str, customer: str, price_list: str, prepared: list[dict]):
	doc = frappe.new_doc(doctype)
	doc.company = MIMT_COMPANY
	doc.selling_price_list = price_list
	if doctype == "Sales Invoice":
		doc.customer = customer
		doc.posting_date = today()
		doc.update_stock = 0
	else:
		doc.quotation_to = "Customer"
		doc.party_name = customer
		doc.transaction_date = today()
		doc.order_type = "Sales"
	if hasattr(doc, "set_missing_values"):
		doc.set_missing_values()
	doc.company = MIMT_COMPANY
	doc.selling_price_list = price_list
	if doctype == "Sales Invoice":
		doc.update_stock = 0
		if not doc.get("due_date"):
			doc.due_date = doc.posting_date or today()
	for row in prepared:
		doc.append(
			"items",
			{
				"item_code": row["item_code"],
				"qty": row["qty"],
				"rate": row["rate"],
				"price_list_rate": row["rate"],
				"uom": row["uom"],
				"item_tax_template": row["item_tax_template"] or None,
				"batch_no": row["batch_no"] or None,
			},
		)
	# set_missing_values and the item hook can put the inclusive rate back.
	for child, row in zip(doc.items, prepared, strict=True):
		child.rate = row["rate"]
		child.price_list_rate = row["rate"]
		if row["item_tax_template"]:
			child.item_tax_template = row["item_tax_template"]
		if row["batch_no"]:
			child.batch_no = row["batch_no"]
	_apply_taxes(doc, [row["item_tax_template"] for row in prepared])
	if hasattr(doc, "calculate_taxes_and_totals"):
		doc.calculate_taxes_and_totals()
	return doc


def _apply_taxes(doc, templates) -> None:
	company_default = _company_tax_template()
	chosen = choose_taxes_template(templates, company_default)
	if not chosen or not frappe.db.exists("Sales Taxes and Charges Template", chosen):
		return
	doc.taxes_and_charges = chosen
	try:
		from erpnext.controllers.accounts_controller import get_taxes_and_charges

		doc.taxes = []
		for tax in get_taxes_and_charges("Sales Taxes and Charges Template", chosen):
			doc.append("taxes", tax)
	except Exception:
		frappe.logger("melliflous_branding").exception("Could not copy the tax template %s", chosen)


def _company_tax_template() -> str | None:
	return frappe.db.get_value(
		"Sales Taxes and Charges Template",
		{"company": MIMT_COMPANY, "disabled": 0, "is_default": 1},
		"name",
	)


def _item_details(item_code: str, price_list: str, customer: str, qty) -> dict:
	currency = frappe.db.get_value("Company", MIMT_COMPANY, "default_currency") or "INR"
	args = {
		"item_code": item_code,
		"company": MIMT_COMPANY,
		"customer": customer,
		"price_list": price_list,
		"qty": flt(qty) or 1,
		"doctype": "Sales Invoice",
		"currency": currency,
		"conversion_rate": 1,
		"plc_conversion_rate": 1,
		"update_stock": 0,
	}
	try:
		from erpnext.stock.get_item_details import get_item_details

		details = get_item_details(args)
		return dict(details or {})
	except Exception:
		frappe.logger("melliflous_branding").exception("Item details failed for %s", item_code)
		rate = _value("Item Price", {"item_code": item_code, "price_list": price_list}, "price_list_rate")
		template = _value("Item Tax", {"parent": item_code, "item_tax_template": ITEM_TAX_5}, "item_tax_template")
		return {
			"price_list_rate": rate or 0,
			"rate": rate or 0,
			"item_tax_template": template or "",
			"item_name": _value("Item", item_code, "item_name"),
			"stock_uom": _value("Item", item_code, "stock_uom"),
		}


def _value(doctype, filters, field):
	try:
		return frappe.db.get_value(doctype, filters, field)
	except Exception:
		return None


def _tax_percent(template: str | None):
	name = " ".join(str(template or "").split())
	if not name:
		return None
	if fold_same(name, ITEM_TAX_5):
		return 5.0
	if not frappe.db.exists("Item Tax Template", name):
		return None
	rows = frappe.get_all("Item Tax Template Detail", filters={"parent": name}, fields=["tax_rate"])
	if not rows:
		return None
	return sum(flt(row.tax_rate) for row in rows)


def _last_batch(item_code: str) -> str:
	"""The batch most recently used on a sales line, else the latest batch of the item."""
	try:
		batch = frappe.db.get_value(
			"Sales Invoice Item",
			{"item_code": item_code, "batch_no": ["is", "set"]},
			"batch_no",
			order_by="modified desc",
		)
		if batch:
			return batch
		return (
			frappe.db.get_value(
				"Batch",
				{"item": item_code, "disabled": 0},
				"name",
				order_by="creation desc",
			)
			or ""
		)
	except Exception:
		return ""


def fold_same(left, right) -> bool:
	return " ".join(str(left or "").split()).casefold() == " ".join(str(right or "").split()).casefold()
