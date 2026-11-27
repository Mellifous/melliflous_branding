# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Rules for distributor profiles, visits, stock, complaints, and follow-up.

No Frappe import. Invoice amounts use the same credit-note rule as targets:
a return subtracts, whether the stored number is negative or positive.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from melliflous_branding.targets import MONTHS, as_date, as_flag, clean_text, month_bounds, signed_amount

VISIT_FREQUENCIES = ("Weekly", "Fortnightly", "Monthly")
COMPLAINT_TYPES = ("Quality", "Damage", "Short Supply", "Expiry", "Pricing", "Other")
COMPLAINT_STATUSES = ("Open", "In Progress", "Resolved", "Closed")
OPEN_COMPLAINTS = frozenset({"Open", "In Progress"})
EDIT_ROLES = frozenset({"System Manager", "Sales Manager"})
TILE_ROLES = frozenset({"System Manager", "Sales Manager", "Sales User"})
DISTRIBUTOR_360_APP = "distributor_360"
DISTRIBUTOR_360_ROUTE = "/desk/distributor-360"
DISTRIBUTOR_360_LOGO = "/assets/melliflous_branding/images/distributor_360.png"
DISTRIBUTOR_360_SEQUENCE = 13
READ_PTYPES = frozenset({"read", "report", "export", "print", "email", "select"})
WRITE_PTYPES = frozenset({"read", "write", "create", "report", "export", "print", "email", "select"})
VISIT_IDENTITY = ("owner", "salesman")
STATEMENT_IDENTITY = ("owner",)
COMPLAINT_IDENTITY = ("owner", "assigned_to")
GROWTH_DEFAULT = 10.0
DEFAULT_SILENCE_DAYS = 30
ACHIEVEMENT_FLOOR = 70.0
RECENT_LIMIT = 12
TOP_PRODUCTS = 8
MIX_PRODUCTS = 5
CHART_MONTHS = 12

# Shortcuts on Quick Actions and the Melliflous Branding sidebar.
DISTRIBUTOR_LINKS = (
	{
		"label": "Distributor 360",
		"link_to": "distributor-360",
		"link_type": "Page",
		"icon": "users",
		"type": "Link",
	},
	{
		"label": "Distributor Visits",
		"link_to": "Distributor Visit",
		"link_type": "DocType",
		"icon": "map-pin",
		"type": "Link",
	},
	{
		"label": "Stock Statements",
		"link_to": "Distributor Stock Statement",
		"link_type": "DocType",
		"icon": "package",
		"type": "Link",
	},
	{
		"label": "Complaints",
		"link_to": "Distributor Complaint",
		"link_type": "DocType",
		"icon": "triangle-alert",
		"type": "Link",
	},
	{
		"label": "Distributor Follow-up",
		"link_to": "Distributor Follow-up",
		"link_type": "Report",
		"icon": "bell",
		"type": "Link",
		"report_ref_doctype": "Distributor Profile",
	},
)
DISTRIBUTOR_CARD = "Distributors"


class DistributorError(ValueError):
	"""A distributor record the user typed cannot be saved."""


def _field(doc, name):
	if isinstance(doc, dict):
		return doc.get(name)
	return getattr(doc, name, None)


def _number(value, label) -> float:
	if value is None or value == "":
		return 0.0
	try:
		return float(value)
	except (TypeError, ValueError):
		raise DistributorError(f"{label} has to be a number.")


def money(value) -> float:
	return round(_number(value, "Amount"), 2)


def qty(value) -> float:
	return round(_number(value, "Quantity"), 3)


def clean_count(value, label) -> int:
	if value is None or value == "":
		return 0
	try:
		number = int(float(value))
	except (TypeError, ValueError):
		raise DistributorError(f"{label} has to be a whole number.")
	if number < 0:
		raise DistributorError(f"{label} cannot be negative.")
	return number


def clean_growth(value, default=GROWTH_DEFAULT) -> float:
	if value is None or value == "":
		return float(default)
	number = _number(value, "Growth percent")
	if number < -50 or number > 200:
		raise DistributorError("Growth percent has to be between -50 and 200.")
	return round(number, 2)


def clean_days(value, default=DEFAULT_SILENCE_DAYS) -> int:
	"""Blank or zero uses the default. A typed number has to sit between 1 and 3650."""
	if value is None or value == "" or value == 0 or value == "0":
		return int(default)
	number = clean_count(value, "Days since the last order")
	if number < 1 or number > 3650:
		raise DistributorError("Days since the last order has to be between 1 and 3650.")
	return number


def add_months(day, count) -> date:
	"""Same day on another month. 31 January lands on the last day of February."""
	day = as_date(day)
	if not day:
		raise DistributorError("Pick a date.")
	month_index = day.month - 1 + int(count)
	year = day.year + month_index // 12
	month = month_index % 12 + 1
	if month == 12:
		last = 31
	else:
		last = (date(year, month + 1, 1) - timedelta(days=1)).day
	return date(year, month, min(day.day, last))


def trailing_months(today, count) -> list:
	"""First day of each calendar month in the window, oldest first. The last month is today's."""
	today = as_date(today)
	if not today:
		raise DistributorError("Today is missing.")
	cursor = add_months(date(today.year, today.month, 1), -(int(count) - 1))
	months = []
	for _ in range(int(count)):
		months.append(cursor)
		cursor = add_months(cursor, 1)
	return months


def month_label(day) -> str:
	day = as_date(day)
	if not day:
		return ""
	return f"{MONTHS[day.month - 1]} {day.year}"


def next_visit_due(last_visit, frequency, today):
	"""Last visit plus the frequency. No visit yet leaves the date empty."""
	frequency = clean_text(frequency) or "Monthly"
	if frequency not in VISIT_FREQUENCIES:
		raise DistributorError("Visit frequency must be Weekly, Fortnightly, or Monthly.")
	last = as_date(last_visit)
	if not last:
		return None
	if frequency == "Weekly":
		return last + timedelta(days=7)
	if frequency == "Fortnightly":
		return last + timedelta(days=14)
	return add_months(last, 1)


def prepare_profile_values(row, today) -> dict:
	customer = clean_text(row.get("customer"))
	company = clean_text(row.get("company"))
	if not customer:
		raise DistributorError("Pick a customer.")
	if not company:
		raise DistributorError("Pick a company.")
	frequency = clean_text(row.get("visit_frequency")) or "Monthly"
	active = row.get("is_active")
	if active in (None, ""):
		active = 1
	return {
		"customer": customer,
		"company": company,
		"visit_frequency": frequency,
		"counters": clean_count(row.get("counters"), "Counters served"),
		"is_active": 1 if as_flag(active) or active in (1, "1") else 0,
		"area": clean_text(row.get("area")) or None,
		"next_visit_due": next_visit_due(row.get("last_visit_date"), frequency, today),
	}


def clean_stock_row(row) -> dict:
	item = clean_text(row.get("item"))
	if not item:
		raise DistributorError("Each stock row needs an item.")
	if row.get("qty") in (None, ""):
		raise DistributorError("Each stock row needs a quantity.")
	quantity = qty(row.get("qty"))
	if quantity < 0:
		raise DistributorError("Stock quantity cannot be negative.")
	return {
		"item": item,
		"qty": quantity,
		"uom": clean_text(row.get("uom")) or None,
		"batch_no": clean_text(row.get("batch_no")) or None,
	}


def clean_visit(row, stock_rows) -> list:
	if not clean_text(row.get("distributor")):
		raise DistributorError("Pick a distributor.")
	if not as_date(row.get("visit_date")):
		raise DistributorError("Pick a visit date.")
	if row.get("order_amount") not in (None, ""):
		amount = money(row.get("order_amount"))
		if amount < 0:
			raise DistributorError("Order amount cannot be negative.")
	if row.get("counters_visited") not in (None, ""):
		clean_count(row.get("counters_visited"), "Counters visited")
	return [clean_stock_row(stock) for stock in stock_rows or []]


def statement_period(month) -> tuple:
	start, end = month_bounds(month)
	return start, end


def statement_period_key(distributor, company, from_date) -> str:
	start = as_date(from_date)
	if not start:
		raise DistributorError("Pick a month.")
	return f"{clean_text(distributor)}|{clean_text(company)}|{start.isoformat()}"


def find_duplicate_statement(rows, distributor, company, from_date, current_name=None):
	"""One statement per distributor, company, and calendar month. Any day in the month matches."""
	start, _end = statement_period(from_date)
	for row in rows or []:
		name = row.get("name")
		if current_name and name == current_name:
			continue
		if clean_text(row.get("distributor")) != clean_text(distributor):
			continue
		if clean_text(row.get("company")) != clean_text(company):
			continue
		other = as_date(row.get("from_date"))
		if other and other.year == start.year and other.month == start.month:
			return row
	return None


def apply_statement_line(row, previous_closing, received_qty) -> dict:
	"""Closing is opening + primary received - secondary, unless the row keeps a typed closing.

	previous_closing is None when last month has no row for the item. Zero is a real opening.
	"""
	item = clean_text(row.get("item"))
	if not item:
		raise DistributorError("Each stock row needs an item.")
	if as_flag(row.get("opening_edited")) or previous_closing is None:
		opening = qty(row.get("opening_qty"))
	else:
		opening = qty(previous_closing)
	if opening < 0:
		raise DistributorError("Opening stock cannot be negative.")
	primary = qty(received_qty or 0)
	secondary = qty(row.get("secondary_qty"))
	if secondary < 0:
		raise DistributorError("Secondary sales cannot be negative.")
	formula = qty(opening + primary - secondary)
	edited = as_flag(row.get("closing_edited"))
	closing = qty(row.get("closing_qty")) if edited else formula
	rate = money(row.get("rate"))
	if rate < 0:
		raise DistributorError("Rate cannot be negative.")
	return {
		"item": item,
		"item_name": clean_text(row.get("item_name")),
		"uom": clean_text(row.get("uom")) or None,
		"opening_qty": opening,
		"opening_edited": 1 if as_flag(row.get("opening_edited")) else 0,
		"primary_qty": primary,
		"secondary_qty": secondary,
		"closing_qty": closing,
		"closing_edited": 1 if edited else 0,
		"rate": rate,
		"closing_value": money(closing * rate),
		"secondary_value": money(secondary * rate),
	}


def normalize_lines(entered, previous, received) -> tuple:
	"""previous maps item -> closing qty. received maps item -> net qty, credit notes already signed."""
	seen = set()
	lines = []
	for row in entered or []:
		item = clean_text(row.get("item"))
		if item and item in seen:
			raise DistributorError(f"{item} is on this statement twice.")
		if item:
			seen.add(item)
		previous_closing = None if not item or item not in (previous or {}) else (previous or {})[item]
		got = (received or {}).get(item, 0) if item else 0
		lines.append(apply_statement_line(row, previous_closing, got))
	totals = {
		"total_opening_qty": qty(sum(line["opening_qty"] for line in lines)),
		"total_primary_qty": qty(sum(line["primary_qty"] for line in lines)),
		"total_secondary_qty": qty(sum(line["secondary_qty"] for line in lines)),
		"total_secondary_value": money(sum(line["secondary_value"] for line in lines)),
		"total_closing_qty": qty(sum(line["closing_qty"] for line in lines)),
		"total_closing_value": money(sum(line["closing_value"] for line in lines)),
	}
	return lines, totals


def received_by_item(lines) -> dict:
	"""Net stock qty per item. A credit note subtracts."""
	totals = {}
	for line in lines or []:
		item = clean_text(line.get("item"))
		if not item:
			continue
		quantity = line.get("stock_qty")
		if quantity is None:
			quantity = line.get("qty")
		totals[item] = totals.get(item, 0) + signed_amount(quantity, line.get("is_return"))
	return {item: qty(amount) for item, amount in totals.items()}


def prefill_rows(previous_rows, invoice_lines) -> list:
	"""Opening from last month's closing, primary from this month's invoices.

	An item with a zero closing and nothing received this month is left off, so a sold-out
	range does not grow forever. A zero closing that still had stock last month stays.
	"""
	received = received_by_item(invoice_lines)
	opening = {}
	meta = {}
	for row in previous_rows or []:
		item = clean_text(row.get("item"))
		if not item:
			continue
		opening[item] = row
		meta.setdefault(item, row)
	for line in invoice_lines or []:
		item = clean_text(line.get("item"))
		if item:
			meta.setdefault(item, line)
	names = sorted(
		set(opening) | set(received),
		key=lambda item: (clean_text((meta.get(item) or {}).get("item_name")) or item).lower(),
	)
	rows = []
	for item in names:
		prev = opening.get(item) or {}
		had_stock = item in opening and qty(prev.get("closing_qty")) != 0
		moved = qty(received.get(item, 0)) != 0
		if not had_stock and not moved:
			continue
		info = meta.get(item) or {}
		opening_qty = qty(prev.get("closing_qty")) if item in opening else 0.0
		primary = qty(received.get(item, 0))
		rate = money(prev.get("rate") or 0)
		closing = qty(opening_qty + primary)
		rows.append(
			{
				"item": item,
				"item_name": clean_text(info.get("item_name") or prev.get("item_name")),
				"uom": clean_text(info.get("stock_uom") or info.get("uom") or prev.get("uom")) or None,
				"opening_qty": opening_qty,
				"opening_edited": 0,
				"primary_qty": primary,
				"secondary_qty": 0.0,
				"closing_qty": closing,
				"closing_edited": 0,
				"rate": rate,
				"closing_value": money(closing * rate),
				"secondary_value": 0.0,
			}
		)
	return rows


def clean_complaint(row, credit_note=None) -> dict:
	distributor = clean_text(row.get("distributor"))
	if not distributor:
		raise DistributorError("Pick a distributor.")
	if not as_date(row.get("complaint_date")):
		raise DistributorError("Pick a date.")
	complaint_type = clean_text(row.get("complaint_type"))
	if complaint_type not in COMPLAINT_TYPES:
		raise DistributorError("Pick a complaint type.")
	status = clean_text(row.get("status")) or "Open"
	if status not in COMPLAINT_STATUSES:
		raise DistributorError("Pick a complaint status.")
	if not clean_text(row.get("description")):
		raise DistributorError("Describe the complaint.")
	if row.get("qty") not in (None, ""):
		quantity = qty(row.get("qty"))
		if quantity < 0:
			raise DistributorError("Quantity cannot be negative.")
	note = clean_text(row.get("credit_note"))
	if note:
		if not credit_note:
			raise DistributorError("The credit note could not be found.")
		if not as_flag(credit_note.get("is_return")):
			raise DistributorError("The linked invoice has to be a credit note.")
		other = clean_text(credit_note.get("customer"))
		if other and other != distributor:
			raise DistributorError("That credit note is for a different customer.")
	return {"complaint_type": complaint_type, "status": status}


def can_open_distributor_360(user, roles) -> bool:
	"""Who sees the Distributor 360 tile on the v16 apps screen.

	Administrator is included because that user is the desk owner. A guest, or a
	desk user without a sales role, does not get the tile.
	"""
	if not user or user == "Guest":
		return False
	if user == "Administrator":
		return True
	return bool(set(roles or []).intersection(TILE_ROLES))


def distributor_360_boot_app() -> dict:
	"""One apps-screen row. The desk grid reads this shape from boot.app_data."""
	return {
		"on_apps_screen": True,
		"sequence_id": DISTRIBUTOR_360_SEQUENCE,
		"app_name": DISTRIBUTOR_360_APP,
		"app_title": "Distributor 360",
		"app_route": DISTRIBUTOR_360_ROUTE,
		"desk_route": "",
		"app_logo_url": DISTRIBUTOR_360_LOGO,
		"dock": [],
	}


def place_distributor_360_app(app_data, user, roles) -> list:
	"""Return the apps-screen list with one Distributor 360 row, or without it.

	Frappe's boot copies only the first add_to_apps_screen entry of each installed
	app into app_data. Quick Actions is that first entry for this app, so a second
	hook entry never becomes a grid icon. This list is what the desktop draws.
	Calling it again does not add a second copy. A user who cannot open the page
	does not get the row.
	"""
	kept = []
	for row in app_data or []:
		name = row.get("app_name") if isinstance(row, dict) else None
		if name == DISTRIBUTOR_360_APP:
			continue
		kept.append(row)
	if can_open_distributor_360(user, roles):
		kept.append(distributor_360_boot_app())
	return kept


def is_manager(viewer) -> bool:
	viewer = viewer or {}
	if viewer.get("user") == "Administrator":
		return True
	return bool(set(viewer.get("roles") or []).intersection(EDIT_ROLES))


def can_see_profile(viewer, profile) -> bool:
	"""Sales User reads a profile they manage, sell, or cover as a Sales Person."""
	if is_manager(viewer):
		return True
	viewer = viewer or {}
	if "Sales User" not in set(viewer.get("roles") or []):
		return False
	user = viewer.get("user")
	if not user or not profile:
		return False
	if _field(profile, "account_manager") == user or _field(profile, "salesman") == user:
		return True
	person = _field(profile, "sales_person")
	return bool(person and person in set(viewer.get("sales_persons") or []))


def can_read_activity(viewer, doc, profile, identity_fields) -> bool:
	if is_manager(viewer):
		return True
	viewer = viewer or {}
	if "Sales User" not in set(viewer.get("roles") or []):
		return False
	user = viewer.get("user")
	for field in identity_fields:
		if user and _field(doc, field) == user:
			return True
	person = _field(doc, "sales_person")
	if person and person in set(viewer.get("sales_persons") or []):
		return True
	return bool(profile and can_see_profile(viewer, profile))


def can_file(viewer, profile, *, is_new, owner, distributor, previous_distributor=None) -> bool:
	"""Sales User files work for a distributor assigned to them.

	The owner of an existing record can still edit it after the profile moves, as long as
	the distributor on the record stays the same. A brand new record needs the assignment.
	"""
	if is_manager(viewer):
		return True
	viewer = viewer or {}
	if "Sales User" not in set(viewer.get("roles") or []):
		return False
	if not distributor:
		return True
	if profile and can_see_profile(viewer, profile):
		return True
	return bool(
		not is_new
		and owner
		and owner == viewer.get("user")
		and previous_distributor
		and previous_distributor == distributor
	)


def _in_company(row, company) -> bool:
	if not company:
		return True
	row_company = clean_text(row.get("company"))
	return not row_company or row_company == company


def _latest_sale(invoices):
	chosen = None
	for row in invoices or []:
		if as_flag(row.get("is_return")):
			continue
		posting = as_date(row.get("posting_date"))
		if not posting:
			continue
		if chosen is None or posting > chosen[0] or (posting == chosen[0] and clean_text(row.get("name")) > chosen[1]):
			chosen = (posting, clean_text(row.get("name")), row)
	return None if chosen is None else chosen[2]


def achievement_for_month(targets, today, company=None):
	"""Lowest current-month achievement. A whole-customer target wins over an item-group one."""
	start, _end = month_bounds(today)
	chosen = []
	for target in targets or []:
		if clean_text(target.get("period_type") or "Monthly") != "Monthly":
			continue
		if as_date(target.get("from_date")) != start:
			continue
		if company and clean_text(target.get("company")) and clean_text(target.get("company")) != clean_text(company):
			continue
		chosen.append(target)
	whole = [
		row for row in chosen if not clean_text(row.get("item_group")) and not clean_text(row.get("brand"))
	]
	pool = whole or chosen
	if not pool:
		return None
	return min(round(float(row.get("achievement_pct") or 0), 2) for row in pool)


def target_suggestion(chart, today, growth_pct) -> dict:
	"""Next month's target is the average primary of the last three calendar months, times growth.

	The three months include the month in progress. A quiet month counts as zero.
	"""
	growth = clean_growth(growth_pct)
	last = list(chart or [])[-3:]
	while len(last) < 3:
		last.insert(0, {"label": "", "year": None, "primary": 0})
	amounts = [money(row.get("primary")) for row in last]
	average = money(sum(amounts) / 3)
	start = add_months(date(as_date(today).year, as_date(today).month, 1), 1)
	end = month_bounds(start)[1]
	return {
		"months": [
			{"label": row.get("label") or "", "year": row.get("year"), "primary": money(row.get("primary"))}
			for row in last
		],
		"average": average,
		"growth_pct": growth,
		"amount": money(average * (1 + growth / 100)),
		"from_date": start,
		"to_date": end,
		"period_label": month_label(start),
	}


def _recent(rows, limit=RECENT_LIMIT) -> list:
	def key(row):
		return (as_date(row.get("date")) or date.min, clean_text(row.get("name")))

	return sorted(rows or [], key=key, reverse=True)[:limit]


def build_dashboard(bundle, today, growth_pct=GROWTH_DEFAULT) -> dict:
	"""KPIs, the 12-month chart, the buying pattern, and the lists for Distributor 360."""
	bundle = bundle or {}
	today = as_date(today)
	company = clean_text(bundle.get("company"))
	customer = clean_text(bundle.get("customer"))
	months = trailing_months(today, CHART_MONTHS)
	window_start = months[0]
	window_end = month_bounds(months[-1])[1]
	invoices = [row for row in bundle.get("invoices") or [] if _in_company(row, company)]
	lines = [row for row in bundle.get("lines") or [] if _in_company(row, company)]
	statements = [row for row in bundle.get("statements") or [] if _in_company(row, company)]
	visits = [row for row in bundle.get("visits") or [] if not company or _in_company(row, company)]
	complaints = [row for row in bundle.get("complaints") or [] if _in_company(row, company)]
	payments = [row for row in bundle.get("payments") or [] if _in_company(row, company)]

	primary = {}
	for row in invoices:
		posting = as_date(row.get("posting_date"))
		if not posting or posting < window_start or posting > window_end:
			continue
		key = (posting.year, posting.month)
		primary[key] = primary.get(key, 0) + signed_amount(row.get("amount"), row.get("is_return"))

	secondary = {}
	filed = set()
	for row in statements:
		start = as_date(row.get("from_date"))
		if not start:
			continue
		key = (start.year, start.month)
		filed.add(key)
		secondary[key] = secondary.get(key, 0) + float(row.get("total_secondary_value") or 0)

	chart = []
	for start in months:
		key = (start.year, start.month)
		chart.append(
			{
				"month": start,
				"label": MONTHS[start.month - 1],
				"year": start.year,
				"primary": money(primary.get(key, 0)),
				"secondary": money(secondary[key]) if key in filed else None,
			}
		)

	latest_statement = None
	for row in statements:
		start = as_date(row.get("from_date"))
		if not start:
			continue
		if latest_statement is None or start > latest_statement[0]:
			latest_statement = (start, row)

	last_sale = _latest_sale(invoices)
	profile = bundle.get("profile") or None
	last_visit = as_date(profile.get("last_visit_date")) if profile else None
	if last_visit is None:
		visit_dates = [as_date(row.get("visit_date")) for row in visits]
		visit_dates = [day for day in visit_dates if day]
		last_visit = max(visit_dates) if visit_dates else None

	if "outstanding" in bundle and bundle.get("outstanding") is not None:
		outstanding = money(bundle.get("outstanding"))
	else:
		outstanding = money(sum(float(row.get("outstanding") or 0) for row in invoices))
	if "overdue_amount" in bundle and bundle.get("overdue_amount") is not None:
		overdue_amount = money(bundle.get("overdue_amount"))
	else:
		overdue_amount = money(
			sum(
				float(row.get("outstanding") or 0)
				for row in invoices
				if float(row.get("outstanding") or 0) > 0
				and as_date(row.get("due_date"))
				and as_date(row.get("due_date")) < today
			)
		)
	if bundle.get("open_complaints") is not None:
		open_complaints = int(bundle.get("open_complaints") or 0)
	else:
		open_complaints = sum(1 for row in complaints if clean_text(row.get("status")) in OPEN_COMPLAINTS)

	line_months = {}
	products = {}
	for line in lines:
		posting = as_date(line.get("posting_date"))
		if not posting or posting < window_start or posting > window_end:
			continue
		item = clean_text(line.get("item"))
		if not item:
			continue
		amount = signed_amount(line.get("amount"), line.get("is_return"))
		quantity = signed_amount(
			line.get("stock_qty") if line.get("stock_qty") is not None else line.get("qty"),
			line.get("is_return"),
		)
		key = (posting.year, posting.month)
		line_months[key] = line_months.get(key, 0) + amount
		bucket = products.setdefault(item, {"item": item, "item_name": "", "qty": 0.0, "amount": 0.0, "months": {}})
		if clean_text(line.get("item_name")):
			bucket["item_name"] = clean_text(line.get("item_name"))
		bucket["qty"] += quantity
		bucket["amount"] += amount
		bucket["months"][key] = bucket["months"].get(key, 0) + amount

	ranked = sorted(
		(row for row in products.values() if row["amount"] > 0),
		key=lambda row: (-row["amount"], row["item"]),
	)
	line_total = sum(row["amount"] for row in ranked) or 0
	product_rows = []
	for row in ranked[:TOP_PRODUCTS]:
		product_rows.append(
			{
				"item": row["item"],
				"item_name": row["item_name"] or row["item"],
				"qty": qty(row["qty"]),
				"amount": money(row["amount"]),
				"share": round(row["amount"] / line_total * 100, 2) if line_total else 0.0,
			}
		)
	mix_items = []
	for row in ranked[:MIX_PRODUCTS]:
		shares = []
		for start in months:
			key = (start.year, start.month)
			base = line_months.get(key) or 0
			if not base:
				shares.append(None)
			else:
				shares.append(round(row["months"].get(key, 0) / base * 100, 2))
		mix_items.append({"item": row["item"], "item_name": row["item_name"] or row["item"], "shares": shares})

	orders = []
	for row in invoices:
		if as_flag(row.get("is_return")):
			continue
		posting = as_date(row.get("posting_date"))
		if not posting or posting < window_start or posting > window_end:
			continue
		orders.append(row)
	orders.sort(key=lambda row: (as_date(row.get("posting_date")), clean_text(row.get("name"))))
	order_count = len(orders)
	order_total = sum(signed_amount(row.get("amount"), 0) for row in orders)
	if order_count >= 2:
		gaps = [
			(as_date(orders[index + 1].get("posting_date")) - as_date(orders[index].get("posting_date"))).days
			for index in range(order_count - 1)
		]
		average_gap = round(sum(gaps) / len(gaps), 1)
	else:
		average_gap = None

	currency = clean_text(bundle.get("currency"))
	statement_row = latest_statement[1] if latest_statement else None
	return {
		"customer": customer,
		"customer_name": clean_text(bundle.get("customer_name")) or customer,
		"company": company,
		"currency": currency,
		"profile": _profile_view(profile),
		"last_billing": None
		if not last_sale
		else {
			"name": last_sale.get("name"),
			"posting_date": as_date(last_sale.get("posting_date")),
			"amount": money(signed_amount(last_sale.get("amount"), 0)),
		},
		"primary_mtd": chart[-1]["primary"] if chart else 0.0,
		"primary_3m": money(sum(row["primary"] for row in chart[-3:])),
		"primary_12m": money(sum(row["primary"] for row in chart)),
		"secondary_sales": None if not statement_row else money(statement_row.get("total_secondary_value")),
		"secondary_qty": None if not statement_row else qty(statement_row.get("total_secondary_qty")),
		"closing_qty": None if not statement_row else qty(statement_row.get("total_closing_qty")),
		"closing_value": None if not statement_row else money(statement_row.get("total_closing_value")),
		"statement_month": None if not latest_statement else latest_statement[0],
		"statement_name": None if not statement_row else statement_row.get("name"),
		"counters": None if not profile else clean_count(profile.get("counters"), "Counters served"),
		"last_visit": last_visit,
		"days_since_order": None
		if not last_sale
		else (today - as_date(last_sale.get("posting_date"))).days,
		"open_complaints": open_complaints,
		"outstanding": outstanding,
		"overdue_amount": overdue_amount,
		"chart": chart,
		"suggestion": target_suggestion(chart, today, growth_pct),
		"products": product_rows,
		"mix": {
			"months": [{"label": MONTHS[start.month - 1], "year": start.year} for start in months],
			"items": mix_items,
		},
		"buying": {
			"order_count": order_count,
			"average_order_value": money(order_total / order_count) if order_count else 0.0,
			"average_days_between": average_gap,
			"orders_per_month": round(order_count / CHART_MONTHS, 2),
		},
		"tabs": {
			"invoices": _recent([_invoice_tab(row) for row in invoices if not as_flag(row.get("is_return"))]),
			"credit_notes": _recent([_invoice_tab(row) for row in invoices if as_flag(row.get("is_return"))]),
			"payments": _recent([_payment_tab(row) for row in payments]),
			"visits": _recent([_visit_tab(row) for row in visits]),
			"statements": _recent([_statement_tab(row) for row in statements]),
			"complaints": _recent([_complaint_tab(row) for row in complaints]),
		},
	}


def _profile_view(profile):
	if not profile:
		return None
	return {
		"name": profile.get("name") or profile.get("customer"),
		"account_manager": clean_text(profile.get("account_manager")),
		"sales_person": clean_text(profile.get("sales_person")),
		"salesman": clean_text(profile.get("salesman")),
		"territory": clean_text(profile.get("territory")),
		"area": clean_text(profile.get("area")),
		"counters": clean_count(profile.get("counters"), "Counters served"),
		"visit_frequency": clean_text(profile.get("visit_frequency")),
		"last_visit_date": as_date(profile.get("last_visit_date")),
		"next_visit_due": as_date(profile.get("next_visit_due")),
		"is_active": 1 if as_flag(profile.get("is_active", 1)) or profile.get("is_active") in (None, "") else 0,
		"notes": clean_text(profile.get("notes")),
	}


def _invoice_tab(row) -> dict:
	return {
		"doctype": "Sales Invoice",
		"name": row.get("name"),
		"date": as_date(row.get("posting_date")),
		"amount": money(signed_amount(row.get("amount"), row.get("is_return"))),
		"text": "",
	}


def _payment_tab(row) -> dict:
	return {
		"doctype": "Payment Entry",
		"name": row.get("name"),
		"date": as_date(row.get("posting_date")),
		"amount": money(row.get("amount")),
		"text": "",
	}


def _visit_tab(row) -> dict:
	who = clean_text(row.get("salesman")) or clean_text(row.get("sales_person"))
	return {
		"doctype": "Distributor Visit",
		"name": row.get("name"),
		"date": as_date(row.get("visit_date")),
		"amount": money(row.get("order_amount")),
		"text": who,
	}


def _statement_tab(row) -> dict:
	return {
		"doctype": "Distributor Stock Statement",
		"name": row.get("name"),
		"date": as_date(row.get("from_date")),
		"amount": money(row.get("total_secondary_value")),
		"text": month_label(row.get("from_date")),
	}


def _complaint_tab(row) -> dict:
	return {
		"doctype": "Distributor Complaint",
		"name": row.get("name"),
		"date": as_date(row.get("complaint_date")),
		"amount": None,
		"text": " · ".join(
			part
			for part in (clean_text(row.get("complaint_type")), clean_text(row.get("status")), clean_text(row.get("item")))
			if part
		),
	}


def classify_distributor(profile, facts, today, no_order_days) -> list:
	"""Reasons this distributor belongs on the follow-up list. Empty means leave them off."""
	facts = facts or {}
	today = as_date(today)
	reasons = []
	active = as_flag(profile.get("is_active", 1)) or profile.get("is_active") in (None, "")
	if active:
		last_visit = as_date(profile.get("last_visit_date"))
		due = as_date(profile.get("next_visit_due"))
		if not last_visit:
			reasons.append({"key": "Visit", "label": "No visit yet"})
		elif due and due < today:
			reasons.append({"key": "Visit", "label": "Overdue visit"})
	last_order = as_date(facts.get("last_order_date"))
	if not last_order:
		reasons.append({"key": "Order", "label": "No order yet"})
	else:
		days = (today - last_order).days
		if days > no_order_days:
			reasons.append({"key": "Order", "label": f"No order in {days} days"})
	pct = facts.get("achievement_pct")
	if pct is not None and float(pct) < ACHIEVEMENT_FLOOR:
		reasons.append({"key": "Target", "label": "Target below 70%"})
	open_count = int(facts.get("open_complaints") or 0)
	if open_count == 1:
		reasons.append({"key": "Complaint", "label": "Open complaint"})
	elif open_count > 1:
		reasons.append({"key": "Complaint", "label": f"{open_count} open complaints"})
	overdue = float(facts.get("overdue_amount") or 0)
	if overdue > 0:
		reasons.append({"key": "Receivable", "label": "Overdue receivable"})
	return reasons


def clean_follow_up_filters(filters) -> dict:
	if isinstance(filters, str):
		filters = json.loads(filters or "{}")
	filters = filters or {}
	reason = clean_text(filters.get("reason")) or None
	if reason and reason not in {"Visit", "Order", "Target", "Complaint", "Receivable"}:
		raise DistributorError("Reason has to be Visit, Order, Target, Complaint, or Receivable.")
	return {
		"company": clean_text(filters.get("company")) or None,
		"account_manager": clean_text(filters.get("account_manager")) or None,
		"sales_person": clean_text(filters.get("sales_person")) or None,
		"no_order_days": clean_days(filters.get("no_order_days")),
		"include_inactive": as_flag(filters.get("include_inactive")),
		"reason": reason,
	}


def follow_up_rows(profiles, facts_by_customer, filters, viewer, today) -> dict:
	filters = clean_follow_up_filters(filters)
	today = as_date(today)
	rows = []
	for profile in profiles or []:
		if not can_see_profile(viewer, profile):
			continue
		if filters["company"] and clean_text(profile.get("company")) != filters["company"]:
			continue
		if filters["account_manager"] and clean_text(profile.get("account_manager")) != filters["account_manager"]:
			continue
		if filters["sales_person"] and clean_text(profile.get("sales_person")) != filters["sales_person"]:
			continue
		active = as_flag(profile.get("is_active", 1)) or profile.get("is_active") in (None, "")
		if not filters["include_inactive"] and not active:
			continue
		customer = clean_text(profile.get("customer"))
		facts = (facts_by_customer or {}).get(customer) or {}
		reasons = classify_distributor(profile, facts, today, filters["no_order_days"])
		if filters["reason"] and not any(reason["key"] == filters["reason"] for reason in reasons):
			continue
		if not reasons:
			continue
		last_order = as_date(facts.get("last_order_date"))
		rows.append(
			{
				"distributor": customer,
				"distributor_name": clean_text(profile.get("customer_name")) or customer,
				"company": clean_text(profile.get("company")),
				"account_manager": clean_text(profile.get("account_manager")),
				"sales_person": clean_text(profile.get("sales_person")),
				"salesman": clean_text(profile.get("salesman")),
				"territory": clean_text(profile.get("territory")),
				"area": clean_text(profile.get("area")),
				"last_visit": as_date(profile.get("last_visit_date")),
				"next_visit_due": as_date(profile.get("next_visit_due")),
				"days_since_order": None if not last_order else (today - last_order).days,
				"achievement_pct": None
				if facts.get("achievement_pct") is None
				else round(float(facts.get("achievement_pct") or 0), 2),
				"open_complaints": int(facts.get("open_complaints") or 0),
				"overdue_amount": money(facts.get("overdue_amount")),
				"reasons": " · ".join(reason["label"] for reason in reasons),
				"reason_keys": [reason["key"] for reason in reasons],
			}
		)
	rows.sort(key=lambda row: (row["distributor_name"].lower(), row["distributor"].lower()))
	return {
		"columns": follow_up_columns(),
		"rows": rows,
		"summary": follow_up_summary(rows),
		"message": "Nothing needs a follow-up." if not rows else "Distributors that need a call, an order, or a fix.",
		"no_order_days": filters["no_order_days"],
	}


def follow_up_columns() -> list:
	return [
		{"label": "Distributor", "fieldname": "distributor", "fieldtype": "Link", "options": "Customer", "width": 180},
		{"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 160},
		{
			"label": "Account Manager",
			"fieldname": "account_manager",
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		},
		{
			"label": "Sales Person",
			"fieldname": "sales_person",
			"fieldtype": "Link",
			"options": "Sales Person",
			"width": 140,
		},
		{"label": "Territory", "fieldname": "territory", "fieldtype": "Link", "options": "Territory", "width": 120},
		{"label": "Last Visit", "fieldname": "last_visit", "fieldtype": "Date", "width": 110},
		{"label": "Next Visit Due", "fieldname": "next_visit_due", "fieldtype": "Date", "width": 130},
		{"label": "Days Since Order", "fieldname": "days_since_order", "fieldtype": "Int", "width": 140},
		{"label": "Achievement %", "fieldname": "achievement_pct", "fieldtype": "Percent", "width": 130},
		{"label": "Open Complaints", "fieldname": "open_complaints", "fieldtype": "Int", "width": 140},
		{"label": "Overdue Amount", "fieldname": "overdue_amount", "fieldtype": "Currency", "width": 140},
		{"label": "Reasons", "fieldname": "reasons", "fieldtype": "Data", "width": 320},
	]


def follow_up_summary(rows) -> list:
	overdue_amount = money(sum(float(row.get("overdue_amount") or 0) for row in rows or []))
	return [
		{"value": len(rows or []), "label": "Distributors", "datatype": "Int"},
		{
			"value": sum(1 for row in rows or [] if "Visit" in (row.get("reason_keys") or [])),
			"label": "Visit chase",
			"datatype": "Int",
		},
		{
			"value": sum(1 for row in rows or [] if "Complaint" in (row.get("reason_keys") or [])),
			"label": "Open complaints",
			"datatype": "Int",
		},
		{"value": overdue_amount, "label": "Overdue", "datatype": "Currency"},
	]


def workspace_shortcut(link) -> dict:
	kind = link["link_type"]
	row = {
		"label": link["label"],
		"link_to": link["link_to"],
		"type": kind,
		"icon": link["icon"],
		"color": "",
		"url": "",
		"stats_filter": "",
		"format": "",
		"doc_view": "List" if kind == "DocType" else "",
	}
	if kind == "Report":
		row["report_ref_doctype"] = link.get("report_ref_doctype") or ""
	return row


def workspace_block(link) -> dict:
	slug = link["link_to"].lower().replace(" ", "-")
	return {"id": f"mb-{slug}", "type": "shortcut", "data": {"shortcut_name": link["label"], "col": 12}}


def workspace_link(link) -> dict:
	kind = link["link_type"]
	return {
		"type": "Link",
		"label": link["label"],
		"link_type": kind,
		"link_to": link["link_to"],
		"hidden": 0,
		"is_query_report": 1 if kind == "Report" else 0,
		"link_count": 0,
		"onboard": 0,
		"dependencies": "",
	}


def merge_distributor_workspace(shortcuts, content, links) -> dict:
	"""Append distributor shortcuts once. Existing Team Files and target links stay put."""
	shortcuts = list(shortcuts or [])
	content = list(content or [])
	links = list(links or [])
	labels = {clean_text(row.get("label")) for row in shortcuts}
	block_names = set()
	for block in content:
		if isinstance(block, dict):
			block_names.add(clean_text((block.get("data") or {}).get("shortcut_name")))
	link_labels = {clean_text(row.get("label")) for row in links}
	changed = False
	for link in DISTRIBUTOR_LINKS:
		label = link["label"]
		if label not in labels:
			shortcuts.append(workspace_shortcut(link))
			labels.add(label)
			changed = True
		if label not in block_names:
			content.append(workspace_block(link))
			block_names.add(label)
			changed = True
		if label not in link_labels:
			if DISTRIBUTOR_CARD not in link_labels:
				links.append(
					{
						"type": "Card Break",
						"label": DISTRIBUTOR_CARD,
						"hidden": 0,
						"is_query_report": 0,
						"link_count": 0,
						"onboard": 0,
					}
				)
				link_labels.add(DISTRIBUTOR_CARD)
			links.append(workspace_link(link))
			link_labels.add(label)
			changed = True
	return {"shortcuts": shortcuts, "content": content, "links": links, "changed": changed}


def sidebar_item(link) -> dict:
	return {
		"added": 0,
		"child": 0,
		"collapsible": 0,
		"is_default_module": 0,
		"hidden": 0,
		"icon": link["icon"],
		"indent": 0,
		"keep_closed": 0,
		"label": link["label"],
		"link_to": link["link_to"],
		"link_type": link["link_type"],
		"open_in_new_tab": 0,
		"show_arrow": 0,
		"type": "Link",
		"url": "",
	}


def missing_sidebar_links(existing) -> list:
	have = {(link_type, link_to) for link_type, link_to in existing or []}
	return [sidebar_item(link) for link in DISTRIBUTOR_LINKS if (link["link_type"], link["link_to"]) not in have]
