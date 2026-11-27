# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Invoice and item checks. No Frappe import.

Warnings are collected into one list. A save is blocked only for a value that
cannot be right: a negative quantity or rate, a GSTIN that fails the format or
the check digit, or an HSN that contains letters or an impossible length.
Missing HSN, a short HSN, the wrong tax type, and the e-way bill reminder stay
warnings. Nothing here writes an Item or a tax row.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date

from melliflous_branding.hsn_catalog import (
	MIN_HSN_DIGITS,
	clean_hsn,
	find_rate_rule,
	hsn_fits,
	hsn_has_letters,
	hsn_in_master,
	match_categories,
	rate_conflict,
	rates_label,
)

# Rule 138 of the CGST Rules: e-way bill when the consignment value exceeds Rs 50,000,
# tax included. Bihar S.O. 14 dated 14 January 2019 raises that to Rs 1,00,000 when the
# movement starts and ends inside Bihar.
EWAY_INTER_STATE = 50000
EWAY_BIHAR_INTRA = 100000
PRICE_LIST_GAP = 0.20
GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")

STATE_NAMES = {
	"01": "Jammu and Kashmir",
	"02": "Himachal Pradesh",
	"03": "Punjab",
	"04": "Chandigarh",
	"05": "Uttarakhand",
	"06": "Haryana",
	"07": "Delhi",
	"08": "Rajasthan",
	"09": "Uttar Pradesh",
	"10": "Bihar",
	"11": "Sikkim",
	"12": "Arunachal Pradesh",
	"13": "Nagaland",
	"14": "Manipur",
	"15": "Mizoram",
	"16": "Tripura",
	"17": "Meghalaya",
	"18": "Assam",
	"19": "West Bengal",
	"20": "Jharkhand",
	"21": "Odisha",
	"22": "Chhattisgarh",
	"23": "Madhya Pradesh",
	"24": "Gujarat",
	"26": "Dadra and Nagar Haveli and Daman and Diu",
	"27": "Maharashtra",
	"29": "Karnataka",
	"30": "Goa",
	"31": "Lakshadweep",
	"32": "Kerala",
	"33": "Tamil Nadu",
	"34": "Puducherry",
	"35": "Andaman and Nicobar Islands",
	"36": "Telangana",
	"37": "Andhra Pradesh",
	"38": "Ladakh",
	"96": "Other Country",
	"97": "Other Territory",
}
STATE_BY_NAME = {}
for _code, _name in STATE_NAMES.items():
	STATE_BY_NAME[_name.lower()] = _code
STATE_BY_NAME["jammu & kashmir"] = "01"
STATE_BY_NAME["orissa"] = "21"
STATE_BY_NAME["dadra and nagar haveli"] = "26"
STATE_BY_NAME["daman and diu"] = "26"
STATE_BY_NAME["pondicherry"] = "34"
STATE_BY_NAME["other country"] = "96"

REGISTERED_CATEGORIES = {
	"registered regular",
	"registered composition",
	"sez",
	"deemed export",
	"tax deductor",
	"tax collector",
	"uin holders",
	"input service distributor",
}
MOVEMENT_DOCTYPES = {"Sales Invoice", "Delivery Note", "Purchase Invoice"}


def gstin_check_digit(first14) -> str:
	"""NIC check digit. Factor 2 starts at the right-hand character of the first 14."""
	factor = 2
	total = 0
	for char in reversed(first14):
		code = GSTIN_CHARS.index(char)
		product = factor * code
		total += (product // 36) + (product % 36)
		factor = 1 if factor == 2 else 2
	return GSTIN_CHARS[(36 - (total % 36)) % 36]


def normalise_gstin(value) -> str:
	return re.sub(r"\s+", "", str(value or "")).upper()


def check_gstin(value) -> str | None:
	"""None when the GSTIN is empty or valid. Otherwise a short reason."""
	gstin = normalise_gstin(value)
	if not gstin:
		return None
	if not GSTIN_PATTERN.match(gstin):
		return "A GSTIN is 15 characters: state code, PAN, entity code, Z, and a check character."
	state = gstin[:2]
	if state not in STATE_NAMES or state == "96":
		return f"GSTIN state code {state} is not a state code used on a GSTIN."
	expected = gstin_check_digit(gstin[:14])
	if gstin[14] != expected:
		return f"The check character should be {expected}."
	return None


def state_code_from_gstin(value) -> str:
	gstin = normalise_gstin(value)
	if len(gstin) >= 2 and gstin[:2] in STATE_NAMES:
		return gstin[:2]
	return ""


def state_code_from_text(value) -> str:
	text = " ".join(str(value or "").replace("_", " ").split())
	if not text:
		return ""
	head = text.split("-", 1)[0].strip()
	if head.isdigit() and head.zfill(2) in STATE_NAMES:
		return head.zfill(2)
	folded = text.lower()
	if folded in STATE_BY_NAME:
		return STATE_BY_NAME[folded]
	for name, code in sorted(STATE_BY_NAME.items(), key=lambda item: len(item[0]), reverse=True):
		if re.search(rf"(?<![a-z]){re.escape(name)}(?![a-z])", folded):
			return code
	return ""


def state_label(code) -> str:
	return STATE_NAMES.get(code or "", code or "this state")


def _as_date(value):
	if isinstance(value, date):
		return value
	text = str(value or "")[:10]
	if len(text) < 10:
		return None
	try:
		year, month, day = (int(part) for part in text.split("-"))
		return date(year, month, day)
	except (TypeError, ValueError):
		return None


def _number(value):
	if value is None or value == "":
		return None
	try:
		return float(value)
	except (TypeError, ValueError):
		return None


def _issue(code, severity, title, detail, suggestion, **extra) -> dict:
	row = {
		"code": code,
		"severity": severity,
		"title": title,
		"detail": detail,
		"suggestion": suggestion,
	}
	row.update(extra)
	return row


def _fits_any(categories, hsn) -> bool:
	return any(hsn_fits(category, hsn) for category in categories)


def _choice_text(categories) -> str:
	parts = []
	for category in categories:
		parts.append(f"{category['name']}: {category['hsn']} ({rates_label(category['rates'])})")
	return " ".join(parts)


def build_suggestion(categories, rule=None) -> dict | None:
	if not categories and not rule:
		return None
	if len(categories) > 1:
		headings = {clean_hsn(category["hsn"])[:4] for category in categories}
		if len(headings) > 1 or len({category["hsn"] for category in categories}) > 1:
			return {
				"hsn": None,
				"rate": None,
				"rates": [],
				"apply_template": False,
				"ambiguous": True,
				"note": "More than one heading fits this name. " + _choice_text(categories),
				"choices": [
					{
						"name": category["name"],
						"hsn": category["hsn"],
						"rate": category["rates"][0] if category["rates"] else None,
					}
					for category in categories
				],
			}
	category = categories[0] if categories else None
	if category:
		rates = category["rates"]
		note = category["note"]
		return {
			"hsn": category["hsn"],
			"rate": rates[0] if rates else None,
			"rates": list(rates),
			"apply_template": len(rates) == 1 and rates[0] > 0,
			"ambiguous": category["ambiguous"],
			"note": note,
			"label": category["name"],
			"source": category["source"],
		}
	if rule and rule["rates"] and rule["kind"] != "excluded":
		return {
			"hsn": None,
			"rate": rule["rates"][0],
			"rates": list(rule["rates"]),
			"apply_template": False,
			"ambiguous": rule["kind"] == "packing",
			"note": rule["label"],
			"source": rule["source"],
		}
	return None


def review_item(
	*,
	item_code="",
	item_name="",
	item_group="",
	hsn="",
	templates=None,
	known_hsn=None,
	strict=False,
) -> dict:
	"""Issues for one item. ``strict`` turns a nonsense HSN into a blocking error."""
	categories = match_categories(item_name, item_code, item_group)
	digits = clean_hsn(hsn)
	raw = str(hsn or "").strip()
	issues = []
	format_severity = "error" if strict else "warning"
	item_bits = {"item_code": item_code or item_name}

	if digits.startswith("99"):
		return {"issues": [], "suggestion": None, "categories": []}

	suggestion = build_suggestion(categories, find_rate_rule(digits))
	suggested_hsn = (suggestion or {}).get("hsn") or ""
	suggested_rate = (suggestion or {}).get("rate")
	rate_text = ""
	if suggestion and suggestion.get("rates"):
		rate_text = rates_label(suggestion["rates"])
	elif suggested_rate is not None:
		rate_text = rates_label((suggested_rate,))
	fix = ""
	if suggested_hsn:
		fix = f"Suggested HSN {suggested_hsn}"
		if rate_text:
			fix += f", {rate_text}"
		fix += "."
		if suggestion and suggestion.get("note"):
			fix += " " + suggestion["note"]
	elif suggestion and suggestion.get("note"):
		fix = suggestion["note"]

	def add(code, severity, title, detail, suggestion_text=None):
		issues.append(
			_issue(
				code,
				severity,
				title,
				detail,
				suggestion_text if suggestion_text is not None else fix,
				suggested_hsn=suggested_hsn,
				suggested_rate=suggested_rate,
				**item_bits,
			)
		)

	if not raw:
		if categories or strict:
			who = item_name or item_code or "This item"
			add(
				"hsn_missing",
				"warning",
				f"{who} has no HSN",
				"A B2B invoice for a business with turnover above Rs 5 crore needs at least 6 digits.",
			)
	elif hsn_has_letters(raw) or len(digits) not in {4, 6, 8}:
		add(
			"hsn_format",
			format_severity,
			f"HSN {raw} is not a valid code",
			"Use 6 or 8 digits, with no letters. A 4-digit heading is too short for this company's invoices.",
		)
	elif len(digits) < MIN_HSN_DIGITS:
		if categories and not _fits_any(categories, digits):
			detail = f"HSN {digits} is only {len(digits)} digits, and it does not match this product."
		else:
			detail = (
				f"HSN {digits} is only {len(digits)} digits. "
				"Invoices need at least 6 when turnover in the previous year was above Rs 5 crore."
			)
		add("hsn_short", "warning", "HSN is too short", detail)
	else:
		if categories and not _fits_any(categories, digits):
			names = ", ".join(category["name"] for category in categories)
			add(
				"hsn_mismatch",
				"warning",
				"HSN does not match this product",
				f"{item_name or item_code or 'This item'} looks like {names}, but the HSN is {digits}.",
			)
		else:
			found = hsn_in_master(digits, known_hsn)
			if found is False:
				add(
					"hsn_master",
					"warning",
					"HSN is not in the GST HSN master",
					f"{digits} was not found on GST HSN Code, including as a parent or a longer item code.",
				)
			rule = find_rate_rule(digits)
			if rule and rule["kind"] == "excluded":
				add(
					"hsn_excluded",
					"warning",
					f"HSN {digits} is {rule['label']}",
					"That code was left out of the 22 September 2025 food-rate cut. Do not use it for these products.",
					rule["source"],
				)
			elif rate_conflict(digits) and suggested_hsn and suggested_hsn != digits:
				add(
					"hsn_imprecise",
					"warning",
					"HSN covers more than one rate",
					f"{digits} includes items that are not all taxed the same way.",
				)

	rule = find_rate_rule(digits) if digits else None
	if rule is None and suggestion and suggestion.get("rates"):
		allowed = tuple(suggestion["rates"])
		kind = "packing" if len(allowed) > 1 else "standard"
	elif rule:
		allowed = tuple(rule["rates"])
		kind = rule["kind"]
	else:
		allowed = ()
		kind = ""

	if kind != "excluded" and allowed:
		seen = templates or []
		if not seen:
			if categories or rule:
				expect = rates_label(allowed)
				add(
					"tax_missing",
					"warning",
					"No item tax template",
					f"The expected rate is {expect}.",
					_tax_suggestion(allowed, suggestion),
				)
		else:
			for template in seen:
				rate = template.get("rate") if isinstance(template, dict) else template
				if rate is None:
					continue
				if any(abs(float(rate) - float(ok)) < 0.05 for ok in allowed):
					continue
				name = template.get("name") if isinstance(template, dict) else ""
				expect = rates_label(allowed)
				label = f" ({name})" if name else ""
				add(
					"tax_mismatch",
					"warning",
					"Item tax rate does not match the HSN",
					f"The template{label} is GST { _trim_rate(rate) }%. The HSN points to {expect}.",
					_tax_suggestion(allowed, suggestion),
				)

	return {"issues": issues, "suggestion": suggestion if issues else None, "categories": [c["name"] for c in categories]}


def _trim_rate(rate) -> str:
	number = float(rate)
	return str(int(number)) if number.is_integer() else str(number)


def _tax_suggestion(allowed, suggestion) -> str:
	if len(allowed) == 1 and allowed[0] > 0:
		text = f"Use an item tax template of GST {_trim_rate(allowed[0])}%."
	elif 0 in allowed:
		text = "Use GST 5% when the pack is pre-packaged and labelled, and nil when it is sold loose."
	else:
		text = f"Expected {rates_label(allowed)}."
	note = (suggestion or {}).get("note")
	if note:
		text += " " + note
	return text


def _line_templates(line) -> list[dict]:
	if line.get("item_tax_template") or line.get("tax_rate") is not None:
		return [{"name": line.get("item_tax_template") or "", "rate": line.get("tax_rate")}]
	return []


def _supply_kind(company_state, place_state, gst_category) -> str:
	category = (gst_category or "").strip().lower()
	if category in {"overseas", "sez"} or place_state in {"96"}:
		return "igst"
	if not company_state or not place_state:
		return ""
	if company_state == place_state:
		return "intra"
	return "inter"


def _tax_kinds(heads) -> set[str]:
	found = set()
	for head in heads or []:
		folded = str(head or "").lower()
		if "igst" in folded:
			found.add("igst")
		if "cgst" in folded:
			found.add("cgst")
		if "sgst" in folded or "utgst" in folded:
			found.add("sgst")
	return found


def _expects_positive_tax(lines, reviews) -> bool:
	for line, review in zip(lines, reviews, strict=False):
		rule = find_rate_rule(line.get("hsn"))
		rates = ()
		if rule:
			rates = rule["rates"]
		elif review["suggestion"] and review["suggestion"].get("rates"):
			rates = tuple(review["suggestion"]["rates"])
		if not rates or (0 in rates and len(rates) > 1):
			rate = line.get("tax_rate")
			if rate is not None and float(rate) > 0:
				return True
			continue
		if rates == (0,):
			continue
		rate = line.get("tax_rate")
		if rate is None or float(rate) > 0:
			return True
	return False


def _previous_month(posting, today) -> bool:
	if today.month == 1:
		return posting.year == today.year - 1 and posting.month == 12
	return posting.year == today.year and posting.month == today.month - 1


def review_document(payload) -> dict:
	"""One list of issues for a selling or purchase document. Does not save anything."""
	data = payload or {}
	doctype = data.get("doctype") or "Sales Invoice"
	issues = []
	lines = list(data.get("items") or [])
	known = data.get("known_hsn")
	reviews = []
	seen = {}
	for index, line in enumerate(lines, start=1):
		item_code = line.get("item_code") or ""
		review = review_item(
			item_code=item_code,
			item_name=line.get("item_name") or "",
			item_group=line.get("item_group") or "",
			hsn=line.get("hsn") or "",
			templates=_line_templates(line),
			known_hsn=known,
			strict=True,
		)
		reviews.append(review)
		for issue in review["issues"]:
			issue["row"] = index
			if item_code:
				issue["title"] = f"Row {index} ({item_code}): {issue['title']}"
			else:
				issue["title"] = f"Row {index}: {issue['title']}"
			issues.append(issue)
		if item_code:
			seen.setdefault(item_code, []).append(index)

		qty = _number(line.get("qty"))
		rate = _number(line.get("rate"))
		label = item_code or f"Row {index}"
		if qty is None:
			issues.append(_issue("qty_missing", "warning", f"{label}: quantity is empty", "Enter the quantity.", "Put a quantity greater than zero.", item_code=item_code, row=index))
		elif qty < 0:
			issues.append(_issue("qty_negative", "error", f"{label}: quantity is negative", "A negative quantity cannot be saved here.", "Enter a quantity greater than zero, or make a return document.", item_code=item_code, row=index))
		elif qty == 0:
			issues.append(_issue("qty_zero", "warning", f"{label}: quantity is zero", "This row will not bill anything.", "Enter the quantity, or remove the row.", item_code=item_code, row=index))
		if rate is not None and rate < 0:
			issues.append(_issue("rate_negative", "error", f"{label}: rate is negative", "A negative rate is not a discount.", "Enter the price, or use a return document for a credit.", item_code=item_code, row=index))
		elif rate == 0:
			issues.append(_issue("rate_zero", "warning", f"{label}: rate is zero", "This row adds no value.", "Enter the price list rate, or remove the row if it is not being billed.", item_code=item_code, row=index))
		else:
			valuation = _number(line.get("valuation_rate"))
			price = _number(line.get("price_list_rate"))
			if rate is not None and valuation and valuation > 0 and rate < valuation - max(1, valuation * 0.01):
				issues.append(
					_issue(
						"rate_below_valuation",
						"warning",
						f"{label}: rate is below valuation",
						f"The rate is {rate:g} and the valuation rate is {valuation:g}.",
						"Check the price before you save. Selling under cost may be a data entry slip.",
						item_code=item_code,
						row=index,
					)
				)
			if rate is not None and price and price > 0 and rate < price * (1 - PRICE_LIST_GAP):
				issues.append(
					_issue(
						"rate_below_price_list",
						"warning",
						f"{label}: rate is well below the price list",
						f"The rate is {rate:g}. The price list rate is {price:g}, which is more than {int(PRICE_LIST_GAP * 100)}% higher.",
						"Confirm the discount. A large gap is often the wrong price list or a missing zero.",
						item_code=item_code,
						row=index,
					)
				)
		uom = " ".join(str(line.get("uom") or "").split()).lower()
		stock_uom = " ".join(str(line.get("stock_uom") or "").split()).lower()
		factor = _number(line.get("conversion_factor"))
		if uom and stock_uom and uom != stock_uom and (factor is None or factor == 0 or factor == 1):
			issues.append(
				_issue(
					"uom_mismatch",
					"warning",
					f"{label}: UOM does not match the stock UOM",
					f"The row is in {line.get('uom')} and the item stock UOM is {line.get('stock_uom')}, with conversion {factor if factor is not None else 'blank'}.",
					"Set the conversion factor, or bill in the stock UOM.",
					item_code=item_code,
					row=index,
				)
			)

	for item_code, rows in seen.items():
		if len(rows) > 1:
			issues.append(
				_issue(
					"duplicate_item",
					"warning",
					f"{item_code} is on more than one row",
					f"Rows {', '.join(str(row) for row in rows)} use the same item.",
					"Combine them unless the batch or the rate is meant to differ.",
					item_code=item_code,
				)
			)

	today = _as_date(data.get("today")) or date.today()
	posting = _as_date(data.get("posting_date"))
	if posting is None:
		issues.append(_issue("date_missing", "warning", "No posting date", "The document has no date to file in a GST month.", "Set the posting date."))
	elif posting > today:
		issues.append(_issue("date_future", "warning", "Posting date is in the future", f"The date is {posting.isoformat()}.", "Use today, or a date that has already happened."))
	elif posting < today.replace(day=1):
		if _previous_month(posting, today) and today.day < 11:
			detail = (
				f"{posting.strftime('%B %Y')} is the previous GST month. "
				"A monthly GSTR-1 for that month is due on the 11th of this month."
			)
		elif _previous_month(posting, today):
			detail = (
				f"{posting.strftime('%B %Y')} is the previous GST month and the 11th of this month has passed. "
				"A monthly GSTR-1 for that month is past its usual due date."
			)
		else:
			detail = f"{posting.strftime('%B %Y')} is an earlier GST month. That return may already be filed."
		issues.append(_issue("date_previous_gst", "warning", "Posting date is in an earlier GST month", detail, "Save only if this period is still open."))

	company_gstin = normalise_gstin(data.get("company_gstin"))
	party_gstin = normalise_gstin(data.get("party_gstin"))
	company_state = state_code_from_gstin(company_gstin)
	place_state = state_code_from_text(data.get("place_of_supply"))
	billing_state = state_code_from_text(data.get("billing_state")) or state_code_from_text(data.get("billing_state_code"))
	gst_category = str(data.get("gst_category") or "")
	party_type = str(data.get("party_type") or "")
	skip_party = data.get("doctype") == "Quotation" and str(data.get("quotation_to") or "Customer") not in {"", "Customer"}

	if not company_gstin:
		issues.append(
			_issue(
				"company_gstin_missing",
				"warning",
				"Company GSTIN is missing",
				"The intra-state check needs the company GSTIN.",
				"Set the GSTIN on the company, then pick that company again.",
			)
		)
	else:
		problem = check_gstin(company_gstin)
		if problem:
			issues.append(_issue("gstin_format", "error", "Company GSTIN is not valid", problem, "Correct the GSTIN on the company."))

	if not skip_party:
		looks_b2b = gst_category.strip().lower() in REGISTERED_CATEGORIES or (
			not gst_category.strip() and party_type.strip().lower() == "company"
		)
		if looks_b2b and not party_gstin:
			who = "supplier" if doctype == "Purchase Invoice" else "customer"
			issues.append(
				_issue(
					"gstin_missing",
					"warning",
					f"This looks like a B2B {who} with no GSTIN",
					f"GST category is {gst_category or 'blank'} and the party type is {party_type or 'blank'}.",
					"Add the GSTIN, or set the GST category to Unregistered if they are not registered.",
				)
			)
		if party_gstin:
			problem = check_gstin(party_gstin)
			if problem:
				issues.append(_issue("gstin_format", "error", "Party GSTIN is not valid", problem, "Correct the GSTIN, or clear it if this party is unregistered."))
			elif billing_state and state_code_from_gstin(party_gstin) != billing_state:
				gst_state = state_code_from_gstin(party_gstin)
				issues.append(
					_issue(
						"gstin_state",
						"warning",
						"GSTIN state does not match the billing address",
						f"The GSTIN starts with {gst_state} ({state_label(gst_state)}) and the billing address is {state_label(billing_state)}.",
						"Use the GSTIN that belongs to that billing address, or correct the address.",
					)
				)

	if not data.get("has_address"):
		issues.append(_issue("address_missing", "warning", "No billing address", "Place of supply is read from the address.", "Add the billing address."))
	if not str(data.get("place_of_supply") or "").strip():
		issues.append(
			_issue(
				"place_missing",
				"warning",
				"Place of supply is empty",
				"CGST and SGST are for a supply inside the company's state. IGST is for a supply to another state.",
				"Set the place of supply.",
			)
		)

	kind = _supply_kind(company_state, place_state, gst_category)
	heads = _tax_kinds(data.get("tax_heads"))
	if kind == "intra" and "igst" in heads:
		where = state_label(company_state)
		issues.append(
			_issue(
				"tax_type",
				"warning",
				f"IGST on a supply within {where}",
				f"The company and the place of supply are both {where}.",
				"Use CGST and SGST. Keep IGST for a supply to another state.",
			)
		)
	elif kind == "intra" and not heads and _expects_positive_tax(lines, reviews):
		issues.append(
			_issue(
				"tax_type",
				"warning",
				"No CGST or SGST on an intra-state supply",
				f"This supply stays inside {state_label(company_state)} and the items are taxable.",
				"Add the intra-state output template (CGST and SGST).",
			)
		)
	elif kind == "inter" and ({"cgst", "sgst"} & heads):
		issues.append(
			_issue(
				"tax_type",
				"warning",
				"CGST or SGST on an inter-state supply",
				f"The company is in {state_label(company_state)} and the place of supply is {state_label(place_state)}.",
				"Use IGST.",
			)
		)
	elif kind == "inter" and "igst" not in heads and _expects_positive_tax(lines, reviews):
		issues.append(
			_issue(
				"tax_type",
				"warning",
				"No IGST on an inter-state supply",
				f"The company is in {state_label(company_state)} and the place of supply is {state_label(place_state)}.",
				"Add the IGST output template.",
			)
		)
	elif kind == "igst" and ({"cgst", "sgst"} & heads):
		issues.append(
			_issue(
				"tax_type",
				"warning",
				"CGST or SGST on an export or SEZ supply",
				"Exports and SEZ supplies are not charged as a local CGST and SGST sale.",
				"Use IGST, or the without-payment treatment if that is how this supply is filed.",
			)
		)

	total = _number(data.get("grand_total"))
	if doctype in MOVEMENT_DOCTYPES and total is not None and not _eway_present(data):
		limit = _eway_limit(kind, company_state)
		if abs(total) > limit:
			if company_state == "10" and kind == "intra":
				why = (
					"Movement that starts and ends in Bihar needs an e-way bill above Rs 1,00,000 "
					"(Bihar S.O. 14 dated 14 January 2019)."
				)
			else:
				why = (
					"Inter-state movement, and intra-state movement outside the Bihar limit, needs an e-way bill "
					"above Rs 50,000 (Rule 138 of the CGST Rules). The value includes tax."
				)
			issues.append(
				_issue(
					"eway_missing",
					"warning",
					"E-way bill details are missing",
					f"The total is {abs(total):g}, over the Rs {limit:g} limit. {why}",
					"Generate the e-way bill yourself. This app will not generate it, and it will not turn the automatic flags on.",
				)
			)

	errors = [issue for issue in issues if issue["severity"] == "error"]
	warnings = [issue for issue in issues if issue["severity"] != "error"]
	return {
		"issues": issues,
		"errors": errors,
		"warnings": warnings,
		"fingerprint": issue_fingerprint(warnings),
		"can_save": not errors,
	}


def _eway_present(data) -> bool:
	for key in ("ewaybill", "e_waybill", "eway_bill_no"):
		if str(data.get(key) or "").strip():
			return True
	return False


def _eway_limit(kind, company_state) -> float:
	if kind == "intra" and company_state == "10":
		return EWAY_BIHAR_INTRA
	return EWAY_INTER_STATE


def issue_fingerprint(issues) -> str:
	parts = sorted(
		f"{issue.get('severity')}|{issue.get('code')}|{issue.get('item_code')}|{issue.get('row')}|{issue.get('title')}"
		for issue in issues
	)
	return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


def format_issues(issues) -> str:
	lines = []
	for issue in issues:
		suggestion = issue.get("suggestion") or ""
		lines.append(f"{issue['title']}. {issue['detail']} {suggestion}".strip())
	return "\n".join(lines)
