# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Sales Invoice numbers. No Frappe import.

The document name is the invoice number GST and e-invoice use. It is at most
16 characters: a letter or digit first, then letters, digits, / and -.
Cancelled invoices keep their number so it cannot be reused, and they do not
take part in posting-date order. Drafts and submitted invoices do.
"""

from __future__ import annotations

import re
from datetime import date, datetime

# Same shape India Compliance uses for a GST document number.
GST_INVOICE_NO = re.compile(r"^[^\W_][A-Za-z0-9\-/]{0,15}$")
PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-/]*$")
MAX_LEN = 16

INVOICE_NO_FIELD = {
	"fieldname": "custom_invoice_no",
	"label": "Invoice No",
	"fieldtype": "Data",
	"insert_after": "customer_section",
	"bold": 1,
	"length": MAX_LEN,
	"no_copy": 1,
	"translatable": 0,
	"description": (
		"This is the invoice number on the bill and on GST. "
		"Letters, numbers, / and - only, up to 16 characters."
	),
}


class InvoiceNumberError(ValueError):
	"""The invoice number cannot be used."""


def clean(value) -> str:
	return " ".join(str(value or "").split())


def clean_invoice_no(value) -> str:
	return str(value or "").strip()


def as_date(value):
	"""A posting date, or None when the value is blank or not a date."""
	if value is None or value == "":
		return None
	if isinstance(value, datetime):
		return value.date()
	if isinstance(value, date):
		return value
	text = str(value).strip()
	if not text:
		return None
	try:
		return datetime.strptime(text[:10], "%Y-%m-%d").date()
	except ValueError:
		return None


def format_dmy(value) -> str:
	day = as_date(value)
	if not day:
		return ""
	return day.strftime("%d-%m-%Y")


def format_problem(invoice_no) -> str | None:
	"""None when the number is a legal GST invoice number with a serial at the end."""
	text = clean_invoice_no(invoice_no)
	if not text:
		return "Enter an invoice number."
	if len(text) > MAX_LEN or not GST_INVOICE_NO.fullmatch(text):
		if len(text) > MAX_LEN:
			return (
				f"Invoice no {text} is longer than 16 characters. "
				"GST allows only letters, numbers, / and -."
			)
		return (
			f"Invoice no {text} can only use letters, numbers, / and -. "
			"GST allows at most 16 characters."
		)
	if not text[-1].isdigit():
		return f"Invoice no {text} needs a serial at the end, such as 0042."
	return None


def duplicate_message(invoice_no, next_free) -> str:
	"""The sentence shown when a serial is already taken."""
	if next_free:
		return (
			f"Invoice no {invoice_no} is already used. "
			f"Please change it (next free number: {next_free})."
		)
	return (
		f"Invoice no {invoice_no} is already used. "
		"No free number fits this date. Please change the date."
	)


def validate_prefix(prefix) -> str | None:
	"""None when the prefix can sit in front of a serial inside 16 characters."""
	text = clean(prefix)
	if not text:
		return None
	if not PREFIX_RE.fullmatch(text) or len(text) > 14:
		return (
			f"Prefix {text} can only use letters, numbers, / and -, "
			"must start with a letter or number, and must leave room for the serial "
			"(14 characters or fewer)."
		)
	return None


def validate_series_settings(rows) -> list[str]:
	"""Problems on the per-company prefix and starting number. Empty means it can be saved."""
	errors = []
	seen = set()
	for row in rows or []:
		row = row or {}
		company = clean(row.get("company") if hasattr(row, "get") else "")
		if not company:
			errors.append("Choose a company for each invoice number series.")
			continue
		key = company.casefold()
		if key in seen:
			errors.append(f"Invoice numbers for {company} are listed twice.")
		seen.add(key)
		problem = validate_prefix(row.get("prefix"))
		if problem:
			errors.append(problem)
		start = row.get("starting_number")
		if start in (None, "", 0, "0"):
			continue
		try:
			number = int(start)
		except (TypeError, ValueError):
			errors.append(f"Starting number for {company} has to be a whole number.")
			continue
		if number < 1:
			errors.append(f"Starting number for {company} has to be 1 or more.")
	return errors


def series_prefix(pattern, when, abbr="") -> tuple[str, int]:
	"""Resolve a Frappe naming series to the prefix and the width of the counter.

	`ACC-SINV-.YYYY.-` on 27 Nov 2026 is prefix `ACC-SINV-2026-` and 5 digits.
	A series with no `#` gets five digits, which is what Frappe appends.
	"""
	text = clean(pattern)
	day = as_date(when) or date.today()
	if not text:
		return "", 5
	if "#" not in text:
		text = text + ".#####"
	prefix = []
	digits = 5
	seen_counter = False
	for part in text.split("."):
		if not part:
			continue
		if not seen_counter and set(part) == {"#"}:
			digits = len(part)
			seen_counter = True
			continue
		if part == "YYYY":
			prefix.append(f"{day.year:04d}")
		elif part == "YY":
			prefix.append(f"{day.year % 100:02d}")
		elif part == "MM":
			prefix.append(f"{day.month:02d}")
		elif part == "DD":
			prefix.append(f"{day.day:02d}")
		elif part == "ABBR":
			prefix.append(clean(abbr))
		else:
			prefix.append(part)
	return "".join(prefix), digits


def detect_prefix(invoice_no) -> str | None:
	"""The series prefix: everything before the trailing serial. None when there is no serial."""
	text = clean_invoice_no(invoice_no)
	if not text or not text[-1].isdigit():
		return None
	index = len(text)
	while index > 0 and text[index - 1].isdigit():
		index -= 1
	return text[:index]


def split_serial(name, prefix) -> tuple[int, int] | None:
	"""Serial value and digit width when `name` belongs to this prefix."""
	text = clean_invoice_no(name)
	head = "" if prefix is None else str(prefix)
	if head:
		if not text.casefold().startswith(head.casefold()):
			return None
		rest = text[len(head) :]
	else:
		rest = text
	if not rest.isdigit():
		return None
	return int(rest), len(rest)


def render_number(prefix, serial, width) -> str:
	"""Prefix plus the serial, padded, kept inside 16 characters."""
	head = "" if prefix is None else str(prefix)
	room = MAX_LEN - len(head)
	if room < 1:
		raise InvoiceNumberError(
			"The invoice prefix is too long for a 16-character GST invoice number. "
			"Set a shorter prefix on Melliflous Settings."
		)
	text = str(int(serial))
	if len(text) > room:
		raise InvoiceNumberError(
			f"Invoice no {head}{text} is longer than 16 characters. "
			"Set a shorter prefix on Melliflous Settings."
		)
	pad = max(len(text), min(int(width or len(text)), room))
	return head + text.zfill(pad)


def plan_invoice(
	prefix,
	rows,
	posting_date,
	*,
	starting_number=None,
	digits=None,
	current_name=None,
	chosen=None,
) -> dict:
	"""Suggest the next number, and say why `chosen` cannot be saved.

	`rows` are existing invoices for one company and this prefix. Each row has
	name, posting_date, and docstatus. Drafts (0) and submitted (1) set the
	date order. Cancelled (2) only block the serial.

	A back-dated invoice is one with an active invoice on a later posting date.
	Its suggestion is a free serial between those neighbours. The latest date
	continues from the highest serial already used, including cancelled ones.
	"""
	day = as_date(posting_date)
	parsed = _parse_rows(prefix, rows, current_name)
	floor_row, ceiling_row, same_max, used, widths = _bounds(parsed, day)
	width = _width(widths, digits, prefix)
	start = _starting(starting_number)
	suggested_serial = _suggest_serial(used, floor_row, ceiling_row, same_max, start)
	suggested = None
	warning = None
	if suggested_serial is None:
		warning = _no_fit_warning(day, floor_row, ceiling_row)
	else:
		try:
			suggested = render_number(prefix, suggested_serial, width)
		except InvoiceNumberError as exc:
			warning = str(exc)
	result = {"suggested": suggested, "warning": warning, "error": None}
	if not chosen:
		return result
	problem = format_problem(chosen)
	if problem:
		result["error"] = problem
		return result
	serial = split_serial(chosen, prefix)
	if serial is None:
		result["error"] = format_problem(chosen) or f"Invoice no {chosen} needs a serial at the end, such as 0042."
		return result
	value = serial[0]
	if _name_or_serial_used(chosen, value, parsed):
		result["error"] = duplicate_message(chosen, suggested)
		return result
	clash = _order_clash(value, floor_row, ceiling_row)
	if clash and day:
		other, direction = clash
		result["error"] = _order_message(
			chosen,
			day,
			other,
			direction,
			prefix,
			width,
			floor_row,
			ceiling_row,
			used,
		)
	return result


def _parse_rows(prefix, rows, current_name):
	current = clean_invoice_no(current_name).casefold()
	parsed = []
	for row in rows or []:
		row = row or {}
		name = clean_invoice_no(row.get("name"))
		if not name or (current and name.casefold() == current):
			continue
		split = split_serial(name, prefix)
		if not split:
			continue
		try:
			status = int(row.get("docstatus") or 0)
		except (TypeError, ValueError):
			status = 0
		parsed.append(
			{
				"name": name,
				"serial": split[0],
				"width": split[1],
				"posting_date": as_date(row.get("posting_date")),
				"docstatus": status,
			}
		)
	return parsed


def _bounds(parsed, posting_date):
	used = set()
	widths = []
	floor_row = None
	ceiling_row = None
	same_max = None
	for row in parsed:
		used.add(row["serial"])
		widths.append(row["width"])
		if row["docstatus"] == 2 or not row["posting_date"] or not posting_date:
			continue
		if row["posting_date"] < posting_date:
			if _prefer_floor(row, floor_row):
				floor_row = row
		elif row["posting_date"] > posting_date:
			if _prefer_ceiling(row, ceiling_row):
				ceiling_row = row
		elif same_max is None or row["serial"] > same_max:
			same_max = row["serial"]
	return floor_row, ceiling_row, same_max, used, widths


def _prefer_floor(row, current) -> bool:
	if current is None:
		return True
	if row["serial"] != current["serial"]:
		return row["serial"] > current["serial"]
	return row["posting_date"] > current["posting_date"]


def _prefer_ceiling(row, current) -> bool:
	if current is None:
		return True
	if row["serial"] != current["serial"]:
		return row["serial"] < current["serial"]
	return row["posting_date"] < current["posting_date"]


def _width(widths, digits, prefix) -> int:
	width = max(widths) if widths else 0
	try:
		hint = int(digits or 0)
	except (TypeError, ValueError):
		hint = 0
	if hint > 0:
		width = max(width, hint)
	if width < 1:
		width = 4
	room = MAX_LEN - len("" if prefix is None else str(prefix))
	if room > 0:
		width = min(width, room)
	return max(width, 1)


def _starting(value):
	if value in (None, "", 0, "0"):
		return None
	try:
		number = int(value)
	except (TypeError, ValueError):
		return None
	return number if number > 0 else None


def _suggest_serial(used, floor_row, ceiling_row, same_max, starting):
	floor = floor_row["serial"] if floor_row else None
	ceiling = ceiling_row["serial"] if ceiling_row else None

	def allowed(number):
		if number < 1 or number in used:
			return False
		if floor is not None and number <= floor:
			return False
		if ceiling is not None and number >= ceiling:
			return False
		if starting is not None and number < starting:
			return False
		return True

	if ceiling is None:
		highest = max(used) if used else 0
		number = max(highest + 1, starting or 1, (floor + 1) if floor is not None else 1)
		guard = 0
		while not allowed(number):
			number += 1
			guard += 1
			if guard > 100000:
				return None
		return number

	anchor = 0
	if floor is not None:
		anchor = max(anchor, floor)
	if same_max is not None:
		anchor = max(anchor, same_max)
	if anchor:
		number = anchor + 1
		if starting is not None:
			number = max(number, starting)
		while number < ceiling:
			if allowed(number):
				return number
			number += 1
	number = ceiling - 1
	while number >= 1:
		if allowed(number):
			return number
		number -= 1
	return None


def _name_or_serial_used(chosen, serial, parsed) -> bool:
	folded = clean_invoice_no(chosen).casefold()
	for row in parsed:
		if row["name"].casefold() == folded or row["serial"] == serial:
			return True
	return False


def _order_clash(serial, floor_row, ceiling_row):
	if ceiling_row and serial >= ceiling_row["serial"]:
		return ceiling_row, "lower"
	if floor_row and serial <= floor_row["serial"]:
		return floor_row, "higher"
	return None


def _order_message(chosen, day, other, direction, prefix, width, floor_row, ceiling_row, used) -> str:
	choice = _range_clause(prefix, width, floor_row, ceiling_row, used)
	return (
		f"Invoice no {chosen} on {format_dmy(day)} is out of order: "
		f"invoice {other['name']} dated {format_dmy(other['posting_date'])} already uses a {direction} number. "
		f"{choice}"
	)


def _range_clause(prefix, width, floor_row, ceiling_row, used) -> str:
	low = floor_row["serial"] + 1 if floor_row else 1
	high = ceiling_row["serial"] - 1 if ceiling_row else None
	if high is not None and low > high:
		return "No free number fits this date. Please change the date."
	first, last = _first_last_free(low, high, used)
	if first is None:
		return "No free number fits this date. Please change the date."
	try:
		first_no = render_number(prefix, first, width)
		if high is None:
			return f"Please choose a number from {first_no} upwards or change the date."
		if last == first:
			return f"Please choose invoice no {first_no} or change the date."
		last_no = render_number(prefix, last, width)
	except InvoiceNumberError:
		return "No free number fits this date. Please change the date."
	return f"Please choose a number between {first_no} and {last_no} or change the date."


def _first_last_free(low, high, used):
	if high is None:
		number = max(low, 1)
		guard = 0
		while number in used:
			number += 1
			guard += 1
			if guard > 100000:
				return None, None
		return number, None
	if low > high:
		return None, None
	first = None
	number = low
	while number <= high:
		if number not in used:
			first = number
			break
		number += 1
	if first is None:
		return None, None
	last = None
	number = high
	while number >= first:
		if number not in used:
			last = number
			break
		number -= 1
	return first, last


def _no_fit_warning(day, floor_row, ceiling_row) -> str:
	when = format_dmy(day) or "this date"
	if floor_row and ceiling_row:
		return (
			f"No free invoice number fits {when}. "
			f"Invoice {floor_row['name']} dated {format_dmy(floor_row['posting_date'])} and "
			f"invoice {ceiling_row['name']} dated {format_dmy(ceiling_row['posting_date'])} "
			"leave no number between them. Please change the date."
		)
	if ceiling_row:
		return (
			f"No free invoice number fits {when}. "
			f"Invoice {ceiling_row['name']} dated {format_dmy(ceiling_row['posting_date'])} "
			"leaves no free number before it. Please change the date."
		)
	return f"No free invoice number fits {when}. Please change the date."
