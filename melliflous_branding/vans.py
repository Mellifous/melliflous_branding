# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Van fleet rules. No Frappe import.

A cancelled or delinked ledger is not this module. Stock, cash, beats, and the
dashboard are decided from rows the caller already loaded.
"""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import date, datetime, timedelta
from xml.etree import ElementTree

SEED_OWNER_EMAIL = "akash@skgourmetspices.com"
SK_DIVISION = "SK Gourmet Spices"
VAN_TYPES = ("Distributor Van", "Company Van")
VAN_STATUSES = ("Live", "Idle", "Pipeline")
COVERAGE = ("Dedicated", "Joint", "Substitute")
ABSENCE_REASONS = ("Holiday", "SR Absent")
ENTRY_MODES = ("Amount only", "Manual SKU", "FieldAssist upload")
FORBIDDEN_CODES = frozenset(f"V{number:02d}" for number in range(4, 10))

SEED_VANS = (
	{"code": "V01", "area": "Motihari", "daily_target": 6500},
	{"code": "V02", "area": "Ara", "daily_target": 4500},
	{"code": "V03", "area": "Lucknow", "daily_target": 0},
	{"code": "V10", "area": "Madhepura", "daily_target": 8000},
	{"code": "V11", "area": "Saharsa", "daily_target": 10000},
	{"code": "V12", "area": "Semrahi/Supaul", "daily_target": 0},
	{"code": "V13", "area": "Supaul", "daily_target": 8000},
)


class VanError(ValueError):
	"""The van report or the upload cannot be used."""


def clean(value) -> str:
	return " ".join(str(value or "").split())


def money(value) -> float:
	try:
		return round(float(value or 0), 2)
	except (TypeError, ValueError):
		return 0.0


def whole(value) -> int:
	try:
		return int(float(value or 0))
	except (TypeError, ValueError):
		return 0


def as_date(value):
	if value is None or value == "":
		return None
	if isinstance(value, datetime):
		return value.date()
	if isinstance(value, date):
		return value
	text = str(value).strip()[:10]
	try:
		return datetime.strptime(text, "%Y-%m-%d").date()
	except ValueError:
		return None


def person_blob(user, email="") -> str:
	return f"{clean(user)} {clean(email)}".lower()


def van_access(user, email, roles) -> str:
	"""delete, edit, read, or none.

	Administrator and akash may delete. Priti may create and edit. Sasank may
	read. A sales role still opens the page for everyone else on the desk.
	"""
	blob = person_blob(user, email)
	role_names = {clean(role) for role in roles or []}
	if clean(user) == "Administrator" or SEED_OWNER_EMAIL in blob:
		return "delete"
	if "priti" in blob:
		return "edit"
	if "sasank" in blob:
		return "read"
	if "Van Manager" in role_names:
		return "delete"
	if "System Manager" in role_names or "Sales Manager" in role_names or "Van Editor" in role_names:
		return "edit"
	if "Sales User" in role_names or "Van Reader" in role_names:
		return "read"
	return "none"


def may_delete(user, email, roles) -> bool:
	return van_access(user, email, roles) == "delete"


def may_edit(user, email, roles) -> bool:
	return van_access(user, email, roles) in {"delete", "edit"}


def sees_division(user, email, roles, division, company) -> bool:
	"""Sasank stays on SK Gourmet. Everyone else who can read is not filtered here."""
	if van_access(user, email, roles) == "none":
		return False
	if "sasank" not in person_blob(user, email):
		return True
	text = f"{clean(division)} {clean(company)}".lower()
	return "sk gourmet" in text


def can_open_vans_360(user, email, roles) -> bool:
	return van_access(user, email, roles) != "none"


def vans_360_boot_app() -> dict:
	return {
		"on_apps_screen": True,
		"sequence_id": 14,
		"app_name": "vans_360",
		"app_title": "Vans 360",
		"app_route": "/desk/vans-360",
		"desk_route": "",
		"app_logo_url": "/assets/melliflous_branding/images/melliflous_icon_512.png",
		"dock": [],
	}


def place_vans_360_app(app_data, user, email, roles) -> list:
	"""One Vans 360 tile beside whatever is already on the apps screen."""
	kept = []
	for row in app_data or []:
		if isinstance(row, dict) and row.get("app_name") == "vans_360":
			continue
		kept.append(row)
	if can_open_vans_360(user, email, roles):
		kept.append(vans_360_boot_app())
	return kept


def seed_vans() -> list:
	"""The seven vans AJ named. V04 to V09 are never included."""
	rows = []
	for row in SEED_VANS:
		code = clean(row["code"]).upper()
		if code in FORBIDDEN_CODES:
			raise VanError(f"{code} must not be created.")
		rows.append(
			{
				"code": code,
				"area": clean(row["area"]),
				"van_type": "Distributor Van",
				"daily_target": money(row["daily_target"]),
				"status": "Live" if money(row["daily_target"]) else "Pipeline",
				"division": SK_DIVISION,
			}
		)
	codes = {row["code"] for row in rows}
	if codes & FORBIDDEN_CODES:
		raise VanError("V04 to V09 must not be created.")
	return rows


def report_figures(sales, cash, online, credit, discount) -> dict:
	"""Collected cash plus online. Mismatch is what is left unexplained."""
	sales_n = money(sales)
	cash_n = money(cash)
	online_n = money(online)
	credit_n = money(credit)
	discount_n = money(discount)
	return {
		"total_collected": money(cash_n + online_n),
		"mismatch": money(sales_n - discount_n - cash_n - online_n - credit_n),
	}


def report_name(code, day, existing) -> str:
	"""One row per van and date, or a second row when that beat is genuine."""
	base = f"{clean(code).upper()}-{as_date(day).isoformat() if as_date(day) else clean(day)}"
	count = whole(existing)
	if count <= 0:
		return base
	if count == 1:
		return base + "-2"
	raise VanError("This van already has two reports on this date.")


def validate_report(row, existing_on_day) -> None:
	"""Raise VanError when the daily report is not ready to save."""
	if not clean(row.get("van")):
		raise VanError("Choose a van.")
	if not as_date(row.get("date")):
		raise VanError("Choose a date.")
	worked = clean(row.get("worked")) or "Yes"
	if worked == "No" and clean(row.get("reason")) not in ABSENCE_REASONS:
		raise VanError("Choose Holiday or SR Absent when the van did not work.")
	if clean(row.get("coverage")) == "Joint" and not clean(row.get("second_sr")):
		raise VanError("A joint beat needs the second SR.")
	second = str(row.get("second_beat") or "").strip() in {"1", "True", "true", "Yes"}
	if whole(existing_on_day) >= 1 and not second:
		raise VanError("Tick second beat to file another report for this van on this date.")
	if whole(existing_on_day) >= 2:
		raise VanError("This van already has two reports on this date.")
	mode = clean(row.get("entry_mode")) or "Amount only"
	if mode not in ENTRY_MODES:
		raise VanError("Choose Amount only, Manual SKU, or FieldAssist upload.")


def stock_action(van_type, entry_mode, items, stock_updated) -> str:
	"""What submit should do with stock. pending means amount-only, still to catch up."""
	if str(stock_updated or "").strip() in {"1", "True", "true"}:
		return "done"
	lines = [row for row in items or [] if clean(row.get("item")) and money(row.get("qty")) > 0]
	if clean(entry_mode) == "Amount only" or not lines:
		return "pending"
	if clean(van_type) == "Company Van":
		return "material_issue"
	if clean(van_type) == "Distributor Van":
		return "secondary"
	return "pending"


def line_amount(qty, rate) -> float:
	return money(money(qty) * money(rate))


def material_issue_payload(company, warehouse, items, posting_date, van) -> dict:
	lines = []
	for row in items or []:
		item = clean(row.get("item"))
		qty = money(row.get("qty"))
		if not item or qty <= 0:
			continue
		lines.append(
			{
				"item_code": item,
				"qty": qty,
				"s_warehouse": clean(warehouse),
				"basic_rate": money(row.get("rate")),
				"transfer_qty": qty,
				"uom": clean(row.get("uom")),
			}
		)
	if not lines:
		raise VanError("Add an item quantity before updating stock.")
	if not clean(warehouse):
		raise VanError("Set the van warehouse before issuing stock.")
	return {
		"doctype": "Stock Entry",
		"stock_entry_type": "Material Issue",
		"purpose": "Material Issue",
		"company": clean(company),
		"posting_date": posting_date,
		"from_warehouse": clean(warehouse),
		"remarks": f"Van {clean(van)} daily sales",
		"items": lines,
	}


def transfer_payload(company, from_warehouse, to_warehouse, items, posting_date, purpose) -> dict:
	"""Depot to van, or van back to depot. purpose is Material Transfer."""
	lines = []
	for row in items or []:
		item = clean(row.get("item"))
		qty = money(row.get("qty"))
		if not item or qty <= 0:
			continue
		lines.append(
			{
				"item_code": item,
				"qty": qty,
				"s_warehouse": clean(from_warehouse),
				"t_warehouse": clean(to_warehouse),
				"basic_rate": money(row.get("rate")),
				"transfer_qty": qty,
			}
		)
	if not lines or not clean(from_warehouse) or not clean(to_warehouse):
		raise VanError("Choose both warehouses and at least one item.")
	return {
		"doctype": "Stock Entry",
		"stock_entry_type": "Material Transfer",
		"purpose": "Material Transfer",
		"company": clean(company),
		"posting_date": posting_date,
		"from_warehouse": clean(from_warehouse),
		"to_warehouse": clean(to_warehouse),
		"remarks": clean(purpose) or "Van stock transfer",
		"items": lines,
	}


def add_secondary_qty(lines, sales_by_item) -> list:
	"""Increase secondary sales and recompute closing. No general ledger."""
	from melliflous_branding.distributors import apply_statement_line

	updated = []
	seen = set()
	for row in lines or []:
		item = clean(row.get("item"))
		if not item:
			continue
		seen.add(item)
		copy = dict(row)
		copy["secondary_qty"] = money(row.get("secondary_qty")) + money((sales_by_item or {}).get(item))
		updated.append(apply_statement_line(copy, None, copy.get("primary_qty")))
	for item, qty in (sales_by_item or {}).items():
		if clean(item) in seen or money(qty) <= 0:
			continue
		updated.append(
			apply_statement_line(
				{"item": clean(item), "secondary_qty": money(qty), "opening_qty": 0, "rate": 0},
				None,
				0,
			)
		)
	return updated


def parse_fa_csv(text) -> list:
	sample = text or ""
	if sample.startswith("\ufeff"):
		sample = sample[1:]
	reader = csv.DictReader(io.StringIO(sample))
	return _fa_from_dicts(list(reader))


def parse_fa_xlsx(blob: bytes) -> list:
	"""First sheet of an xlsx workbook. The standard library reads the zip."""
	try:
		book = zipfile.ZipFile(io.BytesIO(blob))
	except zipfile.BadZipFile as exc:
		raise VanError("That file is not an Excel workbook.") from exc
	shared = []
	if "xl/sharedStrings.xml" in book.namelist():
		root = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
		namespace = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
		for node in root.findall("m:si", namespace):
			shared.append("".join(part.text or "" for part in node.iter() if part.text))
	sheet_name = "xl/worksheets/sheet1.xml"
	if sheet_name not in book.namelist():
		raise VanError("The workbook has no first sheet.")
	root = ElementTree.fromstring(book.read(sheet_name))
	namespace = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
	grid = []
	for row in root.findall("m:sheetData/m:row", namespace):
		values = []
		for cell in row.findall("m:c", namespace):
			kind = cell.attrib.get("t")
			value = cell.find("m:v", namespace)
			text = "" if value is None or value.text is None else value.text
			if kind == "s" and text.isdigit():
				text = shared[int(text)] if int(text) < len(shared) else ""
			values.append(text)
		grid.append(values)
	if not grid:
		return []
	headers = [clean(cell) for cell in grid[0]]
	dicts = []
	for values in grid[1:]:
		dicts.append({headers[index]: values[index] if index < len(values) else "" for index in range(len(headers))})
	return _fa_from_dicts(dicts)


def _fa_from_dicts(rows) -> list:
	parsed = []
	for row in rows or []:
		if not isinstance(row, dict):
			continue
		folded = {clean(key).lower(): value for key, value in row.items()}
		sku = ""
		for key in ("fa sku", "sku", "item", "product", "item name", "sku name"):
			if clean(folded.get(key)):
				sku = clean(folded.get(key))
				break
		if not sku:
			continue
		qty = 0.0
		rate = 0.0
		amount = 0.0
		for key, target in (("qty", "qty"), ("quantity", "qty"), ("rate", "rate"), ("amount", "amount"), ("value", "amount")):
			if key not in folded:
				continue
			number = money(folded.get(key))
			if target == "qty":
				qty = number
			elif target == "rate":
				rate = number
			else:
				amount = number
		if rate <= 0 and qty:
			rate = money(amount / qty) if qty else 0.0
		if amount <= 0:
			amount = line_amount(qty, rate)
		parsed.append({"fa_sku": sku, "qty": qty, "rate": rate, "amount": amount})
	return parsed


def map_fa_lines(parsed, item_map) -> dict:
	"""item_map is fa sku -> item code. Unknown SKUs are returned, not guessed."""
	known = {clean(key).lower(): clean(value) for key, value in (item_map or {}).items() if clean(key) and clean(value)}
	lines = []
	missing = []
	for row in parsed or []:
		sku = clean(row.get("fa_sku"))
		item = known.get(sku.lower())
		if not item:
			if sku and sku not in missing:
				missing.append(sku)
			continue
		qty = money(row.get("qty"))
		rate = money(row.get("rate"))
		lines.append({"fa_sku": sku, "item": item, "qty": qty, "rate": rate, "amount": line_amount(qty, rate)})
	return {"lines": lines, "missing": missing}


def period_bounds(preset, today, start=None, end=None):
	day = as_date(today) or date.today()
	name = clean(preset).lower()
	if name == "today":
		return day, day
	if name == "week":
		return day - timedelta(days=day.weekday()), day
	if name == "mtd":
		return day.replace(day=1), day
	custom_start = as_date(start) or day.replace(day=1)
	custom_end = as_date(end) or day
	if custom_end < custom_start:
		custom_end = custom_start
	return custom_start, custom_end


def _in_period(value, start, end) -> bool:
	day = as_date(value)
	return bool(day and start <= day <= end)


def fleet_overview(vans, reports, today, start, end) -> dict:
	"""One pass over the reports already loaded for the period."""
	start_d, end_d = as_date(start), as_date(end)
	today_d = as_date(today) or end_d
	live = [row for row in vans or [] if clean(row.get("status")) == "Live"]
	sales = 0.0
	target = 0.0
	visited = 0
	productive = 0
	mismatch_count = 0
	new_outlets = 0
	logged_today = set()
	worked_days = set()
	last_keyed = ""
	for row in reports or []:
		if not _in_period(row.get("date"), start_d, end_d):
			continue
		sales += money(row.get("sales"))
		target += money(row.get("target"))
		visited += whole(row.get("counters_visited"))
		productive += whole(row.get("productive_counters"))
		if money(row.get("mismatch")):
			mismatch_count += 1
		new_outlets += whole(row.get("new_outlets"))
		if clean(row.get("worked")) != "No":
			worked_day = as_date(row.get("date"))
			if worked_day:
				worked_days.add((clean(row.get("van")), worked_day.isoformat()))
				if worked_day == today_d:
					logged_today.add(clean(row.get("van")))
		keyed = clean(row.get("modified"))
		if keyed > last_keyed:
			last_keyed = keyed
	days = (end_d - start_d).days + 1 if start_d and end_d else 0
	missed = max(len(live) * days - len(worked_days), 0)
	month_days = (today_d.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
	days_left = max((month_days - today_d).days, 0) if today_d else 0
	month_target = sum(money(row.get("daily_target")) * month_days.day for row in live)
	run_rate = money((month_target - sales) / days_left) if days_left else None
	percent = money(sales / target * 100) if target else 0.0
	strike = money(productive / visited * 100) if visited else 0.0
	return {
		"sales": money(sales),
		"target": money(target),
		"percent": percent,
		"run_rate": run_rate,
		"days_left": days_left,
		"vans_logged_today": len(logged_today),
		"strike": strike,
		"missed_van_days": missed,
		"mismatches": mismatch_count,
		"new_outlets": new_outlets,
		"last_keyed": last_keyed,
	}


def sr_leaderboard(reports, start, end) -> list:
	start_d, end_d = as_date(start), as_date(end)
	bucket = {}
	for row in reports or []:
		if not _in_period(row.get("date"), start_d, end_d) or clean(row.get("worked")) == "No":
			continue
		name = clean(row.get("worked_by")) or "Unassigned"
		slot = bucket.setdefault(name, {"worked_by": name, "sales": 0.0, "days": 0, "target": 0.0})
		slot["sales"] = money(slot["sales"] + money(row.get("sales")))
		slot["target"] = money(slot["target"] + money(row.get("target")))
		slot["days"] += 1
	rows = list(bucket.values())
	rows.sort(key=lambda row: (-row["sales"], row["worked_by"]))
	return rows


def collections_summary(reports, start, end) -> dict:
	start_d, end_d = as_date(start), as_date(end)
	cash = online = credit = discount = 0.0
	for row in reports or []:
		if not _in_period(row.get("date"), start_d, end_d):
			continue
		cash += money(row.get("cash"))
		online += money(row.get("online"))
		credit += money(row.get("credit"))
		discount += money(row.get("discount"))
	return {
		"cash": money(cash),
		"online": money(online),
		"credit": money(credit),
		"discount": money(discount),
		"total_collected": money(cash + online),
	}


def cash_balances(reports, transfers) -> list:
	balances = {}
	for row in reports or []:
		holder = clean(row.get("cash_held_by"))
		if not holder:
			continue
		balances[holder] = money(balances.get(holder, 0) + money(row.get("cash")))
	for row in transfers or []:
		source = clean(row.get("from_holder"))
		target = clean(row.get("to_holder")) or clean(row.get("to_bank"))
		amount = money(row.get("amount"))
		if source:
			balances[source] = money(balances.get(source, 0) - amount)
		if target:
			balances[target] = money(balances.get(target, 0) + amount)
	rows = [{"holder": holder, "balance": balance} for holder, balance in balances.items()]
	rows.sort(key=lambda row: row["holder"])
	return rows


def beat_status(beats, reports, today) -> list:
	today_d = as_date(today) or date.today()
	last = {}
	for row in reports or []:
		beat = clean(row.get("beat"))
		day = as_date(row.get("date"))
		if not beat or not day or clean(row.get("worked")) == "No":
			continue
		if beat not in last or day > last[beat]:
			last[beat] = day
	rows = []
	for beat in beats or []:
		if str(beat.get("active") or "1").strip() in {"0", "False", "false"}:
			continue
		name = clean(beat.get("beat_name") or beat.get("name"))
		seen = last.get(name)
		every = whole(beat.get("every_n_days")) or 1
		overdue = bool(seen and (today_d - seen).days > every) or (seen is None)
		rows.append(
			{
				"beat": name,
				"van": clean(beat.get("van")),
				"planned_counters": whole(beat.get("planned_counters")),
				"last_worked": seen.isoformat() if seen else "",
				"overdue": 1 if overdue else 0,
			}
		)
	return rows


def exceptions(vans, reports, start, end) -> list:
	start_d, end_d = as_date(start), as_date(end)
	found = []
	by_van = {}
	for row in reports or []:
		if not _in_period(row.get("date"), start_d, end_d):
			continue
		by_van.setdefault(clean(row.get("van")), []).append(row)
		if clean(row.get("worked")) == "No" and clean(row.get("reason")) == "SR Absent":
			found.append({"van": clean(row.get("van")), "kind": "absent", "date": str(row.get("date"))})
		if clean(row.get("worked")) != "No" and money(row.get("sales")) == 0:
			found.append({"van": clean(row.get("van")), "kind": "0%", "date": str(row.get("date"))})
		target = money(row.get("target"))
		if target and money(row.get("sales")) < target * 0.7:
			found.append({"van": clean(row.get("van")), "kind": "<70% target", "date": str(row.get("date"))})
		if money(row.get("mismatch")):
			found.append({"van": clean(row.get("van")), "kind": "mismatch", "date": str(row.get("date"))})
	for van in vans or []:
		if clean(van.get("status")) == "Idle":
			found.append({"van": clean(van.get("code") or van.get("name")), "kind": "idle", "date": ""})
	for van, rows in by_van.items():
		absent = sum(1 for row in rows if clean(row.get("worked")) == "No" and clean(row.get("reason")) == "SR Absent")
		if absent >= 3:
			found.append({"van": van, "kind": "frequent absence", "date": ""})
		visited = sum(whole(row.get("counters_visited")) for row in rows)
		productive = sum(whole(row.get("productive_counters")) for row in rows)
		if visited and productive / visited < 0.5:
			found.append({"van": van, "kind": "low strike", "date": ""})
	return found


def reported_vs_invoiced(reports, invoices, start, end) -> list:
	"""Unbilled van-days are worked days with no submitted invoice for that van."""
	start_d, end_d = as_date(start), as_date(end)
	reported = {}
	for row in reports or []:
		if not _in_period(row.get("date"), start_d, end_d) or clean(row.get("worked")) == "No":
			continue
		key = (clean(row.get("van")), as_date(row.get("date")).isoformat())
		slot = reported.setdefault(key, {"van": key[0], "date": key[1], "reported": 0.0, "invoiced": 0.0})
		slot["reported"] = money(slot["reported"] + money(row.get("sales")))
	billed = set()
	for row in invoices or []:
		if not _in_period(row.get("posting_date"), start_d, end_d):
			continue
		if whole(row.get("docstatus")) != 1:
			continue
		key = (clean(row.get("van")), as_date(row.get("posting_date")).isoformat())
		billed.add(key)
		slot = reported.setdefault(key, {"van": key[0], "date": key[1], "reported": 0.0, "invoiced": 0.0})
		slot["invoiced"] = money(slot["invoiced"] + money(row.get("grand_total")))
	rows = []
	for key, slot in reported.items():
		slot["unbilled"] = 0 if key in billed else 1
		rows.append(slot)
	rows.sort(key=lambda row: (row["date"], row["van"]))
	return rows


def report_table(kind, reports, vans, beats, transfers, today) -> tuple:
	"""Columns and rows for one download. kind selects the sheet."""
	name = clean(kind).lower()
	if name in {"van summary", "summary"}:
		columns = ["Van", "Area", "Sales", "Target", "Days"]
		bucket = {}
		for row in reports or []:
			van = clean(row.get("van"))
			slot = bucket.setdefault(van, {"sales": 0.0, "target": 0.0, "days": 0})
			slot["sales"] = money(slot["sales"] + money(row.get("sales")))
			slot["target"] = money(slot["target"] + money(row.get("target")))
			slot["days"] += 1
		areas = {clean(row.get("code") or row.get("name")): clean(row.get("area")) for row in vans or []}
		data = [[van, areas.get(van, ""), slot["sales"], slot["target"], slot["days"]] for van, slot in sorted(bucket.items())]
		return columns, data
	if name in {"sr", "sr leaderboard"}:
		columns = ["Worked by", "Sales", "Target", "Days"]
		data = [[row["worked_by"], row["sales"], row["target"], row["days"]] for row in sr_leaderboard(reports, "2000-01-01", "2999-01-01")]
		return columns, data
	if name == "beat":
		columns = ["Beat", "Van", "Planned", "Last worked", "Overdue"]
		data = [
			[row["beat"], row["van"], row["planned_counters"], row["last_worked"], row["overdue"]]
			for row in beat_status(beats, reports, today)
		]
		return columns, data
	if name in {"collections", "collections/credit"}:
		columns = ["Date", "Van", "Cash", "Online", "Credit", "Discount"]
		data = [
			[row.get("date"), row.get("van"), money(row.get("cash")), money(row.get("online")), money(row.get("credit")), money(row.get("discount"))]
			for row in reports or []
		]
		return columns, data
	if name in {"cash", "cash transfers"}:
		columns = ["Date", "From", "To", "Amount", "Reference"]
		data = [
			[row.get("posting_date"), row.get("from_holder"), row.get("to_holder") or row.get("to_bank"), money(row.get("amount")), row.get("reference")]
			for row in transfers or []
		]
		return columns, data
	if name in {"new outlets", "outlets"}:
		columns = ["Date", "Van", "New outlets"]
		data = [[row.get("date"), row.get("van"), whole(row.get("new_outlets"))] for row in reports or [] if whole(row.get("new_outlets"))]
		return columns, data
	columns = ["Date", "Van", "Item", "Qty", "Rate", "Amount"]
	data = []
	for row in reports or []:
		lines = row.get("items") or []
		if not lines:
			data.append([row.get("date"), row.get("van"), "", "", "", money(row.get("sales"))])
			continue
		for line in lines:
			data.append([row.get("date"), row.get("van"), line.get("item"), money(line.get("qty")), money(line.get("rate")), money(line.get("amount"))])
	return columns, data


def rows_to_csv(columns, data) -> str:
	buffer = io.StringIO()
	writer = csv.writer(buffer)
	writer.writerow(columns)
	for row in data:
		writer.writerow(row)
	return buffer.getvalue()


def plain_row(row) -> dict:
	"""Copy a row without calling a missing method.

	Frappe's `_dict` answers any missing attribute with None, so hasattr(row, "as_dict")
	is true and row.as_dict() raises TypeError. A real Document as_dict is callable.
	"""
	if isinstance(row, dict):
		return dict(row)
	as_dict = getattr(row, "as_dict", None)
	if callable(as_dict):
		return as_dict()
	return {}


def empty_dashboard() -> dict:
	return {
		"overview": {
			"sales": 0.0,
			"target": 0.0,
			"percent": 0.0,
			"run_rate": None,
			"days_left": 0,
			"vans_logged_today": 0,
			"strike": 0.0,
			"missed_van_days": 0,
			"mismatches": 0,
			"new_outlets": 0,
			"last_keyed": "",
		},
		"vans": [],
		"leaderboard": [],
		"collections": {"cash": 0.0, "online": 0.0, "credit": 0.0, "discount": 0.0, "total_collected": 0.0},
		"beats": [],
		"exceptions": [],
		"reported_vs_invoiced": [],
		"cash": {"balances": [], "transfers": []},
		"stock": [],
	}


def assemble_dashboard(vans, reports, invoices, beats, transfers, today, start, end) -> dict:
	"""Dashboard for any period, including a fleet with no daily reports yet."""
	vans = [plain_row(row) for row in vans or []]
	reports = [plain_row(row) for row in reports or []]
	invoices = [plain_row(row) for row in invoices or []]
	beats = [plain_row(row) for row in beats or []]
	transfers = [plain_row(row) for row in transfers or []]
	payload = empty_dashboard()
	payload["overview"] = fleet_overview(vans, reports, today, start, end)
	payload["vans"] = vans
	payload["leaderboard"] = sr_leaderboard(reports, start, end)
	payload["collections"] = collections_summary(reports, start, end)
	payload["beats"] = beat_status(beats, reports, today)
	payload["exceptions"] = exceptions(vans, reports, start, end)
	payload["reported_vs_invoiced"] = reported_vs_invoiced(reports, invoices, start, end)
	payload["cash"] = {"balances": cash_balances(reports, transfers), "transfers": transfers[:20]}
	return payload


def rows_to_html(title, columns, data) -> str:
	head = "".join(f"<th>{clean(column)}</th>" for column in columns)
	body = []
	for row in data:
		cells = "".join(f"<td>{clean(cell)}</td>" for cell in row)
		body.append(f"<tr>{cells}</tr>")
	return (
		f"<!DOCTYPE html><html><head><title>{clean(title)}</title></head><body>"
		f"<h1>{clean(title)}</h1><table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"
		"<p>Print this page to save a PDF.</p></body></html>"
	)
