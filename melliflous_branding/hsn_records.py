# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Load GST context and apply an HSN only when a person asks.

``ensure_hsn_catalog`` writes HSN Category Map rows from the researched table.
It does not read or write Item, and it does not turn on e-invoice or e-way bill.
"""

from __future__ import annotations

import re

import frappe
from frappe.utils import cint, escape_html, flt, today

from melliflous_branding.gst_checks import (
	issue_fingerprint,
	review_document,
	review_item,
)
from melliflous_branding.hsn_catalog import clean_hsn, fixture_records

RATE_IN_NAME = re.compile(r"GST\s*([0-9]+(?:\.[0-9]+)?)\s*%", re.I)
PROBLEM_CODES = {
	"missing hsn": "hsn_missing",
	"short hsn": "hsn_short",
	"format": "hsn_format",
	"not in master": "hsn_master",
	"category": "hsn_mismatch",
	"tax rate": "tax_mismatch",
	"tax missing": "tax_missing",
	"imprecise": "hsn_imprecise",
}


def validate_item(doc, method=None):
	if _skipped(doc) or not _has_field("Item", "gst_hsn_code"):
		return
	_surface(doc, _pack(review_loaded_item(doc)))


def validate_document(doc, method=None):
	if _skipped(doc):
		return
	_surface(doc, review_document(build_payload(doc)))


def _skipped(doc) -> bool:
	flags = getattr(doc, "flags", None)
	return bool(flags and flags.get("ignore_hsn_guard"))


def _surface(doc, result):
	if result["errors"]:
		frappe.throw(
			_html(result["errors"] + result["warnings"]),
			title="Fix these before saving",
		)
	if not result["warnings"]:
		return
	if _acked(doc.doctype, result["fingerprint"]):
		return
	frappe.msgprint(
		_html(result["warnings"]),
		title="Check this before you rely on it",
		indicator="orange",
	)


def _html(issues) -> str:
	rows = []
	for issue in issues:
		title = escape_html(issue.get("title") or "")
		detail = escape_html(issue.get("detail") or "")
		suggestion = escape_html(issue.get("suggestion") or "")
		rows.append(f"<li><strong>{title}</strong><br>{detail} {suggestion}</li>")
	return "<ul class='melliflous-hsn-list'>" + "".join(rows) + "</ul>"


def _ack_key(doctype, fingerprint) -> str:
	user = getattr(frappe.session, "user", None) or ""
	return f"melliflous-hsn-ack:{user}:{doctype}:{fingerprint}"


def _acked(doctype, fingerprint) -> bool:
	if not fingerprint:
		return False
	return frappe.cache.get_value(_ack_key(doctype, fingerprint)) == "1"


def _pack(result) -> dict:
	issues = result["issues"]
	errors = [issue for issue in issues if issue["severity"] == "error"]
	warnings = [issue for issue in issues if issue["severity"] != "error"]
	return {
		"issues": issues,
		"errors": errors,
		"warnings": warnings,
		"fingerprint": issue_fingerprint(warnings),
		"can_save": not errors,
		"suggestion": result.get("suggestion"),
	}


def _desk_user():
	if getattr(frappe.session, "user", None) in (None, "Guest"):
		frappe.throw("Sign in to use this.", frappe.PermissionError)


@frappe.whitelist()
def acknowledge(fingerprint, doctype):
	"""Remember that this person already saw this warning set. Expires in two minutes."""
	_desk_user()
	if fingerprint and doctype:
		frappe.cache.set_value(_ack_key(doctype, fingerprint), "1", expires_in_sec=120)
	return {"ok": True}


@frappe.whitelist()
def check_item(item):
	_desk_user()
	result = _pack(review_loaded_item(_parse(item)))
	result["suggestion"] = _public_suggestion(
		_with_template(result.get("suggestion"), frappe.defaults.get_user_default("company"))
	)
	return result


@frappe.whitelist()
def check_document(doc):
	_desk_user()
	result = review_document(build_payload(_parse(doc)))
	result["suggestion"] = None
	return result


@frappe.whitelist()
def audit_items(item_group=None, problem=None):
	_desk_user()
	return {
		"rows": collect_audit(item_group, problem),
		"can_apply": "System Manager" in set(frappe.get_roles()),
	}


@frappe.whitelist()
def apply_selected(item_codes):
	"""Write the suggested HSN. System Manager only, and only for the rows they ticked."""
	frappe.only_for("System Manager")
	changed = []
	skipped = []
	for code in _as_list(item_codes):
		try:
			frappe.db.savepoint("hsn_apply")
			outcome = _apply_one(code)
			if outcome.get("changed"):
				changed.append(outcome)
			else:
				skipped.append(outcome)
		except Exception as exc:
			frappe.db.rollback(save_point="hsn_apply")
			skipped.append({"item_code": code, "reason": str(exc)[:300]})
	return {"changed": changed, "skipped": skipped}


def report_rows(filters=None):
	filters = filters or {}
	rows = collect_audit(filters.get("item_group"), filters.get("problem"))
	columns = [
		{"label": "Item", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
		{"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 180},
		{
			"label": "Item Group",
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 140,
		},
		{"label": "HSN", "fieldname": "hsn", "fieldtype": "Data", "width": 110},
		{"label": "Problem", "fieldname": "problem", "fieldtype": "Data", "width": 260},
		{"label": "Suggested HSN", "fieldname": "suggested_hsn", "fieldtype": "Data", "width": 130},
		{"label": "Suggested GST %", "fieldname": "suggested_rate", "fieldtype": "Float", "width": 130},
		{"label": "Suggested template", "fieldname": "item_tax_template", "fieldtype": "Data", "width": 170},
		{"label": "What to do", "fieldname": "suggestion", "fieldtype": "Data", "width": 420},
	]
	return columns, rows


def ensure_hsn_catalog():
	"""Insert or refresh HSN Category Map. Does not update any Item."""
	if not frappe.db.table_exists("HSN Category Map"):
		return
	for row in fixture_records():
		name = row["category_name"]
		if frappe.db.exists("HSN Category Map", name):
			doc = frappe.get_doc("HSN Category Map", name)
			if _copy_reference(doc, row):
				doc.save(ignore_permissions=True)
		else:
			frappe.get_doc(row).insert(ignore_permissions=True)


def _copy_reference(doc, row) -> bool:
	changed = False
	for key, value in row.items():
		if key in {"doctype", "name"}:
			continue
		current = doc.get(key)
		if key == "gst_rate":
			same = flt(current) == flt(value)
		elif key == "ambiguous":
			same = cint(current) == cint(value)
		elif key == "effective_from":
			same = str(current or "")[:10] == str(value)[:10]
		else:
			same = (current or "") == (value or "")
		if not same:
			doc.set(key, value)
			changed = True
	return changed


def collect_audit(item_group=None, problem=None) -> list[dict]:
	if not frappe.db.table_exists("Item"):
		return []
	fields = ["name", "item_code", "item_name", "item_group"]
	has_hsn = _has_field("Item", "gst_hsn_code")
	if has_hsn:
		fields.append("gst_hsn_code")
	filters = {"disabled": 0}
	if item_group:
		filters["item_group"] = item_group
	items = frappe.get_all("Item", filters=filters, fields=fields, limit_page_length=0)
	taxes = {}
	if frappe.db.table_exists("Item Tax"):
		for row in frappe.get_all(
			"Item Tax",
			fields=["parent", "item_tax_template"],
			limit_page_length=0,
		):
			taxes.setdefault(row.parent, []).append(row.item_tax_template)
	known = known_hsn_codes()
	rates = _template_rates()
	company = frappe.defaults.get_user_default("company")
	wanted = PROBLEM_CODES.get(str(problem or "").strip().lower())
	rows = []
	for item in items:
		templates = []
		for name in taxes.get(item.name) or []:
			if name:
				templates.append({"name": name, "rate": rates.get(name)})
		result = review_item(
			item_code=item.item_code,
			item_name=item.item_name,
			item_group=item.item_group,
			hsn=item.get("gst_hsn_code") if has_hsn else "",
			templates=templates,
			known_hsn=known,
		)
		if not result["issues"]:
			continue
		codes = [issue["code"] for issue in result["issues"]]
		if wanted and wanted not in codes:
			continue
		suggestion = _with_template(result["suggestion"], company)
		rows.append(
			{
				"item_code": item.item_code,
				"item_name": item.item_name,
				"item_group": item.item_group or "",
				"hsn": (item.get("gst_hsn_code") if has_hsn else "") or "",
				"problem": "; ".join(issue["title"] for issue in result["issues"]),
				"suggested_hsn": (suggestion or {}).get("hsn") or "",
				"suggested_rate": (suggestion or {}).get("rate"),
				"item_tax_template": (suggestion or {}).get("item_tax_template") or "",
				"suggestion": " ".join(
					part for part in (issue.get("suggestion") or "" for issue in result["issues"]) if part
				),
				"ambiguous": 1 if (suggestion or {}).get("ambiguous") else 0,
				"codes": codes,
			}
		)
	rows.sort(key=lambda row: (row["item_group"], row["item_code"]))
	return rows


def _apply_one(item_code) -> dict:
	if not frappe.db.exists("Item", item_code):
		return {"item_code": item_code, "reason": "Item was not found."}
	if not _has_field("Item", "gst_hsn_code"):
		return {"item_code": item_code, "reason": "Item has no GST HSN field. India Compliance adds it."}
	item = frappe.get_doc("Item", item_code)
	company = frappe.defaults.get_user_default("company")
	suggestion = _with_template(review_loaded_item(item).get("suggestion"), company)
	if not suggestion or not suggestion.get("hsn"):
		return {"item_code": item_code, "reason": "There is no single HSN to apply. Pick the code yourself."}
	item.gst_hsn_code = suggestion["hsn"]
	template = suggestion.get("item_tax_template") if suggestion.get("apply_template") else None
	if template:
		_set_template(item, template)
	item.flags.ignore_hsn_guard = True
	item.save()
	return {
		"changed": True,
		"item_code": item_code,
		"hsn": suggestion["hsn"],
		"item_tax_template": template or "",
	}


def _set_template(item, template):
	rows = list(item.get("taxes") or [])
	for row in rows:
		if _get(row, "item_tax_template") == template:
			return
	for row in rows:
		name = str(_get(row, "item_tax_template") or "")
		if not name or "gst" in name.lower():
			row.item_tax_template = template
			return
	item.append("taxes", {"item_tax_template": template})


def review_loaded_item(doc) -> dict:
	templates = []
	rates = _template_rates()
	for row in _get(doc, "taxes") or []:
		name = _get(row, "item_tax_template")
		if not name:
			continue
		rate = rates.get(name)
		if rate is None:
			rate = rate_from_name(name)
		templates.append({"name": name, "rate": rate})
	return review_item(
		item_code=_get(doc, "item_code") or "",
		item_name=_get(doc, "item_name") or "",
		item_group=_get(doc, "item_group") or "",
		hsn=_get(doc, "gst_hsn_code") or "",
		templates=templates,
		known_hsn=known_hsn_codes(),
	)


def build_payload(doc) -> dict:
	codes = [code for code in (_get(row, "item_code") for row in (_get(doc, "items") or [])) if code]
	masters = _item_masters(codes)
	rates = _template_rates()
	document_rate = _document_tax_rate(doc)
	items = []
	for row in _get(doc, "items") or []:
		code = _get(row, "item_code") or ""
		master = masters.get(code) or {}
		template_name = _get(row, "item_tax_template") or ""
		if template_name:
			tax_rate = rates.get(template_name)
			if tax_rate is None:
				tax_rate = rate_from_name(template_name)
		else:
			tax_rate = document_rate
		items.append(
			{
				"item_code": code,
				"item_name": _get(row, "item_name") or master.get("item_name") or "",
				"item_group": master.get("item_group") or _get(row, "item_group") or "",
				"hsn": _get(row, "gst_hsn_code") or master.get("gst_hsn_code") or "",
				"qty": _get(row, "qty"),
				"rate": _get(row, "rate"),
				"price_list_rate": _get(row, "price_list_rate"),
				"valuation_rate": master.get("valuation_rate"),
				"uom": _get(row, "uom"),
				"stock_uom": _get(row, "stock_uom") or master.get("stock_uom"),
				"conversion_factor": _get(row, "conversion_factor"),
				"item_tax_template": template_name,
				"tax_rate": tax_rate,
			}
		)
	address_name = _first(doc, "customer_address", "supplier_address")
	address = _address(address_name)
	company = _get(doc, "company")
	party_gstin = _first(doc, "billing_address_gstin", "customer_gstin", "supplier_gstin")
	if not party_gstin:
		party_gstin = address.get("gstin") or _party_field(doc, "gstin")
	return {
		"doctype": _get(doc, "doctype"),
		"posting_date": str(_first(doc, "posting_date", "transaction_date") or "")[:10],
		"today": today(),
		"company_gstin": _first(doc, "company_gstin") or _company_gstin(company),
		"party_gstin": party_gstin or "",
		"gst_category": _first(doc, "gst_category") or _party_field(doc, "gst_category"),
		"party_type": _party_field(doc, "customer_type"),
		"quotation_to": _get(doc, "quotation_to"),
		"place_of_supply": _get(doc, "place_of_supply"),
		"billing_state": address.get("gst_state") or address.get("state") or "",
		"has_address": bool(address_name),
		"grand_total": _first(doc, "grand_total", "rounded_total") or 0,
		"ewaybill": _first(doc, "ewaybill", "e_waybill", "eway_bill_no"),
		"items": items,
		"tax_heads": [
			f"{_get(tax, 'account_head') or ''} {_get(tax, 'description') or ''}"
			for tax in (_get(doc, "taxes") or [])
		],
		"known_hsn": known_hsn_codes(),
	}


def known_hsn_codes():
	cached = frappe.cache.get_value("melliflous-hsn-master")
	if cached == "missing":
		return None
	if isinstance(cached, list):
		return {clean_hsn(code) for code in cached if clean_hsn(code)} or None
	if not frappe.db.table_exists("GST HSN Code") or not frappe.db.has_column("GST HSN Code", "hsn_code"):
		frappe.cache.set_value("melliflous-hsn-master", "missing", expires_in_sec=3600)
		return None
	codes = [clean_hsn(code) for code in (frappe.get_all("GST HSN Code", pluck="hsn_code") or [])]
	codes = [code for code in codes if code]
	if not codes:
		return None
	frappe.cache.set_value("melliflous-hsn-master", codes, expires_in_sec=3600)
	return set(codes)


def _template_rates() -> dict:
	if not frappe.db.table_exists("Item Tax Template"):
		return {}
	details = {}
	if frappe.db.table_exists("Item Tax Template Detail") and frappe.db.has_column("Item Tax Template Detail", "tax_rate"):
		for row in frappe.get_all(
			"Item Tax Template Detail",
			fields=["parent", "tax_type", "tax_rate"],
			limit_page_length=0,
		):
			details.setdefault(row.parent, []).append({"account": row.tax_type, "rate": row.tax_rate})
	rates = {}
	for name in frappe.get_all("Item Tax Template", pluck="name") or []:
		if details.get(name):
			rates[name] = combined_rate(details[name])
		else:
			rates[name] = rate_from_name(name)
	return rates


def combined_rate(rows) -> float | None:
	igst = 0.0
	split = 0.0
	other = 0.0
	seen = False
	for row in rows:
		rate = flt(row.get("rate"))
		account = str(row.get("account") or "").lower()
		seen = True
		if "igst" in account:
			igst += rate
		elif "cgst" in account or "sgst" in account or "utgst" in account:
			split += rate
		else:
			other += rate
	if not seen:
		return None
	if igst and split:
		return max(igst, split)
	if igst:
		return igst
	if split:
		return split
	return other


def _document_tax_rate(doc):
	rows = [
		{
			"account": f"{_get(tax, 'account_head') or ''} {_get(tax, 'description') or ''}",
			"rate": _get(tax, "rate"),
		}
		for tax in (_get(doc, "taxes") or [])
	]
	if not rows:
		return None
	return combined_rate(rows)


def rate_from_name(name):
	match = RATE_IN_NAME.search(str(name or ""))
	if not match:
		return None
	return flt(match.group(1))


def find_template(rate, company=None):
	if rate in (None, ""):
		return None
	matches = []
	for name, found in _template_rates().items():
		parsed = found if found is not None else rate_from_name(name)
		if parsed is None or abs(flt(parsed) - flt(rate)) > 0.05:
			continue
		matches.append(name)
	abbr = ""
	if company and frappe.db.exists("Company", company) and frappe.db.has_column("Company", "abbr"):
		abbr = frappe.db.get_value("Company", company, "abbr") or ""
	if abbr:
		preferred = [name for name in matches if abbr.lower() in name.lower()]
		if preferred:
			matches = preferred
	if len(matches) == 1:
		return matches[0]
	return None


def _with_template(suggestion, company):
	if not suggestion:
		return None
	suggestion = dict(suggestion)
	suggestion["item_tax_template"] = None
	if suggestion.get("apply_template") and suggestion.get("rate") not in (None, ""):
		suggestion["item_tax_template"] = find_template(suggestion["rate"], company)
	return suggestion


def _public_suggestion(suggestion):
	if not suggestion:
		return None
	return {
		"hsn": suggestion.get("hsn"),
		"rate": suggestion.get("rate"),
		"rates": suggestion.get("rates") or [],
		"apply_template": bool(suggestion.get("apply_template")),
		"ambiguous": bool(suggestion.get("ambiguous")),
		"note": suggestion.get("note") or "",
		"item_tax_template": suggestion.get("item_tax_template") or "",
		"choices": suggestion.get("choices") or [],
	}


def _item_masters(codes) -> dict:
	if not codes or not frappe.db.table_exists("Item"):
		return {}
	fields = ["name", "item_code", "item_name", "item_group", "stock_uom", "valuation_rate"]
	if _has_field("Item", "gst_hsn_code"):
		fields.append("gst_hsn_code")
	rows = frappe.get_all("Item", filters={"name": ["in", list(set(codes))]}, fields=fields, limit_page_length=0)
	return {row.item_code or row.name: row for row in rows}


def _address(name) -> dict:
	if not name or not frappe.db.exists("Address", name):
		return {}
	fields = ["state"]
	for extra in ("gstin", "gst_state", "gst_state_number"):
		if frappe.db.has_column("Address", extra):
			fields.append(extra)
	return frappe.db.get_value("Address", name, fields, as_dict=True) or {}


def _company_gstin(company) -> str:
	if not company or not frappe.db.has_column("Company", "gstin"):
		return ""
	return frappe.db.get_value("Company", company, "gstin") or ""


def _party_field(doc, fieldname) -> str:
	doctype = _get(doc, "doctype")
	if doctype == "Purchase Invoice":
		party, target = _get(doc, "supplier"), "Supplier"
	elif doctype == "Quotation":
		if (_get(doc, "quotation_to") or "Customer") != "Customer":
			return ""
		party, target = _get(doc, "party_name"), "Customer"
	else:
		party, target = _get(doc, "customer"), "Customer"
	if not party or not frappe.db.exists(target, party) or not frappe.db.has_column(target, fieldname):
		return ""
	return frappe.db.get_value(target, party, fieldname) or ""


def _has_field(doctype, fieldname) -> bool:
	try:
		return bool(frappe.get_meta(doctype).has_field(fieldname))
	except Exception:
		return False


def _parse(value):
	if isinstance(value, str):
		return frappe.parse_json(value) or {}
	return value or {}


def _as_list(value) -> list[str]:
	parsed = _parse(value) if isinstance(value, str) else value
	if isinstance(parsed, str):
		parsed = [parsed]
	return [str(code) for code in (parsed or []) if str(code).strip()]


def _get(doc, field):
	if doc is None:
		return None
	if isinstance(doc, dict):
		return doc.get(field)
	getter = getattr(doc, "get", None)
	if getter:
		return getter(field)
	return getattr(doc, field, None)


def _first(doc, *names):
	for name in names:
		value = _get(doc, name)
		if value not in (None, ""):
			return value
	return None
