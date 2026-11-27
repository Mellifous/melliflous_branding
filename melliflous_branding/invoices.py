# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Quick Invoice amounts. No Frappe import.

Classic price lists store a GST-inclusive rate at 5 percent. The Sales Invoice
and the Quotation store the rate before GST. Tax is split into CGST and SGST
because MIMT bills inside the state.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

MIMT_COMPANY = "Melliflous International Multi Trade Pvt Ltd"
MIMT_ABBR = "MIMT"
CLASSIC_PRICE_LISTS: tuple[str, ...] = (
	"Classic Distributor",
	"Classic Retailer",
	"Classic MRP",
)
STANDARD_PRICE_LIST = "Standard Selling"
ITEM_TAX_5 = "GST 5% - MIMT"
OUTPUT_GST_5 = "Output GST 5% In-state - MIMT"
INCLUSIVE_DIVISOR = Decimal("1.05")
CENTS = Decimal("0.01")


class InvoiceError(ValueError):
	"""Something on the Quick Invoice form cannot be saved yet."""


def fold(value) -> str:
	return " ".join(str(value or "").split()).casefold()


def money(value) -> float:
	"""Rupees to the paisa, half up, as a float the document can store."""
	quantized = Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)
	return float(quantized)


def is_classic_price_list(price_list) -> bool:
	folded = fold(price_list)
	return any(fold(name) == folded for name in CLASSIC_PRICE_LISTS)


def is_five_percent(tax_percent) -> bool:
	if tax_percent is None or tax_percent == "":
		return False
	try:
		rate = Decimal(str(tax_percent))
	except Exception:
		return False
	return rate == Decimal("5") or rate == Decimal("5.0")


def exclusive_rate(rate, price_list, tax_percent) -> float:
	"""Invoice rate. Classic 5 percent prices are divided by 1.05.

	Any other price list, and a Classic list whose item is not taxed at
	5 percent, keeps the price-list rate. A negative rate is rejected.
	"""
	try:
		amount = Decimal(str(0 if rate is None or rate == "" else rate))
	except Exception as error:
		raise InvoiceError("Rate has to be a number.") from error
	if amount < 0:
		raise InvoiceError("Rate cannot be negative.")
	if is_classic_price_list(price_list) and is_five_percent(tax_percent):
		amount = amount / INCLUSIVE_DIVISOR
	return money(amount)


def choose_taxes_template(item_templates, company_default) -> str | None:
	"""Output GST 5 percent when every item uses the 5 percent MIMT template.

	A blank template, or any other template, falls through to the company
	default. No items yet is not "all items are 5 percent".
	"""
	names = [" ".join(str(row or "").split()) for row in (item_templates or [])]
	if names and all(fold(name) == fold(ITEM_TAX_5) for name in names):
		return OUTPUT_GST_5
	default = " ".join(str(company_default or "").split())
	return default or None


def line_amount(qty, rate) -> float:
	return money(Decimal(str(qty)) * Decimal(str(rate)))


def tax_split(amount, tax_percent) -> tuple[float, float]:
	"""CGST and SGST. The two halves add back to the rounded tax."""
	try:
		percent = Decimal(str(0 if tax_percent is None or tax_percent == "" else tax_percent))
	except Exception:
		percent = Decimal(0)
	if percent == 0:
		return 0.0, 0.0
	tax = money(Decimal(str(amount)) * percent / Decimal(100))
	cgst = money(Decimal(str(tax)) / Decimal(2))
	sgst = money(Decimal(str(tax)) - Decimal(str(cgst)))
	return cgst, sgst


def invoice_totals(lines) -> dict:
	"""Taxable value, CGST, SGST, and grand total for the lines on screen.

	Each line is a mapping with qty, rate (already exclusive), and tax_percent.
	"""
	taxable = Decimal("0")
	cgst = Decimal("0")
	sgst = Decimal("0")
	for line in lines or []:
		qty = line.get("qty") or 0
		rate = line.get("rate") or 0
		amount = Decimal(str(line_amount(qty, rate)))
		part_cgst, part_sgst = tax_split(amount, line.get("tax_percent"))
		taxable += amount
		cgst += Decimal(str(part_cgst))
		sgst += Decimal(str(part_sgst))
	taxable_f = money(taxable)
	cgst_f = money(cgst)
	sgst_f = money(sgst)
	return {
		"taxable": taxable_f,
		"cgst": cgst_f,
		"sgst": sgst_f,
		"grand_total": money(Decimal(str(taxable_f)) + Decimal(str(cgst_f)) + Decimal(str(sgst_f))),
	}


def validate_draft(payload) -> list[str]:
	"""Friendly reasons the draft cannot be saved yet. Empty means it can."""
	payload = payload or {}
	errors = []
	if not " ".join(str(payload.get("customer") or "").split()):
		errors.append("Choose a customer first.")
	if not " ".join(str(payload.get("price_list") or "").split()):
		errors.append("Choose a price list.")
	items = payload.get("items") or []
	if not items:
		errors.append("Add at least one item.")
	for index, row in enumerate(items, start=1):
		row = row or {}
		item = " ".join(str(row.get("item_code") or "").split())
		if not item:
			errors.append(f"Pick an item on row {index}.")
			continue
		try:
			qty = Decimal(str(row.get("qty")))
		except Exception:
			errors.append(f"Enter a quantity for {item}.")
			continue
		if qty <= 0:
			errors.append(f"Enter a quantity greater than zero for {item}.")
	return errors


def price_list_choices(customer_default=None) -> list[str]:
	"""The four selling lists, plus the customer's own list when it is different."""
	ordered = []
	seen = set()

	def add(name):
		cleaned = " ".join(str(name or "").split())
		if not cleaned or fold(cleaned) in seen:
			return
		seen.add(fold(cleaned))
		ordered.append(cleaned)

	for name in (*CLASSIC_PRICE_LISTS, STANDARD_PRICE_LIST):
		add(name)
	add(customer_default)
	return ordered


def choose_price_list(customer_default, existing=None) -> str:
	"""The list to select. The customer's list wins, including one we do not ship."""
	default = " ".join(str(customer_default or "").split())
	if default:
		return default
	have = [" ".join(str(name).split()) for name in (existing or []) if str(name or "").strip()]
	for preferred in (STANDARD_PRICE_LIST, *CLASSIC_PRICE_LISTS):
		for name in have:
			if fold(name) == fold(preferred):
				return name
	if have:
		return have[0]
	return STANDARD_PRICE_LIST
