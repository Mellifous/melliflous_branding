# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Rules for a customer's primary (sell-in) target. No Frappe import."""

from __future__ import annotations

from datetime import date, datetime, timedelta

STATUSES = ("Achieved", "Not Achieved", "In Progress")
PERIOD_TYPES = ("Monthly", "Quarterly")
EDIT_ROLES = frozenset({"System Manager", "Sales Manager"})
READ_PTYPES = frozenset({"read", "report", "export", "print"})
CHART_LIMIT = 15
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

# Shortcuts added to Quick Actions, and to Selling / CRM when those modules exist.
TARGET_LINKS = (
	{
		"label": "Customer Targets",
		"link_to": "Customer Primary Target",
		"link_type": "DocType",
		"icon": "target",
		"type": "Link",
	},
	{
		"label": "Target vs Achievement",
		"link_to": "Customer Target vs Achievement",
		"link_type": "Report",
		"icon": "chart-column",
		"type": "Link",
	},
)
SIDEBAR_MODULES = ("Selling", "FCRM", "CRM")
WORKSPACE_NAMES = ("Selling", "CRM", "FCRM")


class TargetError(ValueError):
	"""A target the user typed cannot be saved."""


def clean_text(value) -> str:
	if value is None:
		return ""
	return str(value).strip()


def as_date(value):
	if value is None or value == "":
		return None
	if isinstance(value, datetime):
		return value.date()
	if isinstance(value, date):
		return value
	text = str(value).strip()
	if not text:
		return None
	return date.fromisoformat(text[:10])


def as_flag(value) -> bool:
	return value in (True, 1, "1", "Yes", "yes")


def fiscal_month(value) -> int:
	try:
		month = int(value)
	except (TypeError, ValueError):
		return 4
	if month < 1 or month > 12:
		return 4
	return month


def month_bounds(day) -> tuple[date, date]:
	day = as_date(day)
	if not day:
		raise TargetError("Pick a month.")
	start = date(day.year, day.month, 1)
	if day.month == 12:
		next_start = date(day.year + 1, 1, 1)
	else:
		next_start = date(day.year, day.month + 1, 1)
	return start, next_start - timedelta(days=1)


def quarter_bounds(day, fiscal_start_month=4) -> tuple[date, date]:
	"""Quarter of the company's fiscal year. April is the Indian year used when none is set."""
	day = as_date(day)
	if not day:
		raise TargetError("Pick a day in the quarter.")
	start_month = fiscal_month(fiscal_start_month)
	shift = (day.month - start_month) % 12
	quarter_index = shift // 3
	start_month_index = (start_month - 1 + quarter_index * 3) % 12
	month = start_month_index + 1
	year = day.year - 1 if month > day.month else day.year
	start = date(year, month, 1)
	end_month = month + 2
	end_year = year
	if end_month > 12:
		end_month -= 12
		end_year += 1
	if end_month == 12:
		end = date(end_year, 12, 31)
	else:
		end = date(end_year, end_month + 1, 1) - timedelta(days=1)
	return start, end


def saved_period(period_type, target_month, target_quarter, from_date, fiscal_start_month=4) -> dict:
	period_type = period_type or "Monthly"
	if period_type not in PERIOD_TYPES:
		raise TargetError("Period type must be Monthly or Quarterly.")
	if period_type == "Quarterly":
		day = target_quarter or from_date
		start, end = quarter_bounds(day, fiscal_start_month)
		return {
			"period_type": "Quarterly",
			"target_month": None,
			"target_quarter": as_date(day),
			"from_date": start,
			"to_date": end,
		}
	day = target_month or from_date
	start, end = month_bounds(day)
	return {
		"period_type": "Monthly",
		"target_month": as_date(day),
		"target_quarter": None,
		"from_date": start,
		"to_date": end,
	}


def periods_overlap(left_from, left_to, right_from, right_to) -> bool:
	left_from = as_date(left_from)
	left_to = as_date(left_to)
	right_from = as_date(right_from)
	right_to = as_date(right_to)
	if not left_from or not left_to or not right_from or not right_to:
		return False
	return left_from <= right_to and right_from <= left_to


def same_filter(left_group, left_brand, right_group, right_brand) -> bool:
	return (left_group or "") == (right_group or "") and (left_brand or "") == (right_brand or "")


def find_overlap(rows, start, end, item_group, brand, current_name=None) -> list:
	hits = []
	for row in rows:
		name = row.get("name")
		if current_name and name == current_name:
			continue
		if not same_filter(item_group, brand, row.get("item_group"), row.get("brand")):
			continue
		if periods_overlap(start, end, row.get("from_date"), row.get("to_date")):
			hits.append(row)
	return hits


def require_target_amount(amount) -> float:
	if amount is None or amount == "":
		raise TargetError("Enter a target amount.")
	number = float(amount)
	if number <= 0:
		raise TargetError("Target amount has to be more than zero.")
	return round(number, 2)


def clean_qty(qty, uom) -> tuple:
	if qty is None or qty == "":
		return None, clean_text(uom) or None
	number = float(qty)
	if number < 0:
		raise TargetError("Target quantity cannot be negative.")
	if number == 0:
		return None, clean_text(uom) or None
	unit = clean_text(uom)
	if not unit:
		raise TargetError("Pick a UOM for the quantity target.")
	return round(number, 3), unit


def assigned_owner(sales_user, session_user) -> str:
	return clean_text(sales_user) or clean_text(session_user)


def signed_amount(amount, is_return) -> float:
	"""Credit notes subtract. ERPNext stores their amount negative or, rarely, positive."""
	number = abs(float(amount or 0))
	if as_flag(is_return):
		return -number
	return number


def line_qty(line, uom) -> float:
	unit = clean_text(uom)
	if not unit:
		return float(line.get("qty") or 0)
	if unit == clean_text(line.get("stock_uom")) and line.get("stock_qty") is not None:
		return float(line.get("stock_qty") or 0)
	if unit == clean_text(line.get("uom")):
		return float(line.get("qty") or 0)
	return 0.0


def groups_for(item_group, descendants):
	group = clean_text(item_group)
	if not group:
		return None
	known = (descendants or {}).get(group)
	return known or {group}


def line_matches(line, target, descendants) -> bool:
	groups = groups_for(target.get("item_group"), descendants)
	if groups is not None and clean_text(line.get("item_group")) not in groups:
		return False
	brand = clean_text(target.get("brand"))
	if brand and clean_text(line.get("brand")) != brand:
		return False
	return True


def achievement_figures(target, achieved, from_date, to_date, today) -> dict:
	target_amount = round(float(target or 0), 2)
	achieved_amount = round(float(achieved or 0), 2)
	pct = round(achieved_amount / target_amount * 100, 2) if target_amount else 0.0
	end = as_date(to_date)
	day = as_date(today)
	if target_amount and (pct >= 100 or achieved_amount >= target_amount):
		status = "Achieved"
	elif end and day and day > end:
		status = "Not Achieved"
	else:
		status = "In Progress"
	return {
		"achieved_amount": achieved_amount,
		"gap": round(target_amount - achieved_amount, 2),
		"achievement_pct": pct,
		"status": status,
	}


def indicator_colour(pct) -> str:
	shown = round(float(pct or 0), 2)
	if shown >= 100:
		return "green"
	if shown >= 70:
		return "orange"
	return "red"


def achievement_for_targets(targets, lines, descendants, today) -> dict:
	grouped = {}
	for line in lines or []:
		key = (line.get("customer"), line.get("company"))
		grouped.setdefault(key, []).append(line)
	out = {}
	for index, target in enumerate(targets or []):
		amount = 0.0
		qty = 0.0
		start = as_date(target.get("from_date"))
		end = as_date(target.get("to_date"))
		bucket = grouped.get((target.get("customer"), target.get("company")), ())
		for line in bucket:
			posting = as_date(line.get("posting_date"))
			if start and end and posting and (posting < start or posting > end):
				continue
			if not line_matches(line, target, descendants):
				continue
			amount += signed_amount(line.get("amount"), line.get("is_return"))
			qty += signed_amount(line_qty(line, target.get("uom")), line.get("is_return"))
		figures = achievement_figures(target.get("target_amount"), amount, start, end, today)
		figures["achieved_qty"] = round(qty, 3)
		out[target.get("name") or f"row-{index}"] = figures
	return out


def can_edit_targets(roles, user=None) -> bool:
	if user == "Administrator":
		return True
	return bool(set(roles or []).intersection(EDIT_ROLES))


def _field(doc, name):
	if isinstance(doc, dict):
		return doc.get(name)
	return getattr(doc, name, None)


def can_see_target(viewer, target) -> bool:
	viewer = viewer or {}
	user = viewer.get("user")
	roles = set(viewer.get("roles") or [])
	if user == "Administrator" or roles.intersection(EDIT_ROLES):
		return True
	if "Sales User" not in roles:
		return False
	if user and (_field(target, "owner") == user or _field(target, "sales_user") == user):
		return True
	sales_person = _field(target, "sales_person")
	return bool(sales_person and sales_person in set(viewer.get("sales_persons") or []))


def _blank_amount(value) -> bool:
	"""An empty grid cell often arrives as 0. That is not a target."""
	if value is None or value == "":
		return True
	try:
		return float(value) == 0
	except (TypeError, ValueError):
		return False


def clean_bulk_rows(rows) -> list:
	if isinstance(rows, str):
		import json

		rows = json.loads(rows) if rows else []
	seen = set()
	cleaned = []
	for row in rows or []:
		if not isinstance(row, dict):
			continue
		customer = clean_text(row.get("customer"))
		raw_amount = row.get("target_amount")
		if not customer and _blank_amount(raw_amount):
			continue
		if not customer:
			raise TargetError("Each target needs a customer.")
		if _blank_amount(raw_amount):
			continue
		amount = require_target_amount(raw_amount)
		qty, unit = clean_qty(row.get("target_qty"), row.get("uom"))
		if customer in seen:
			raise TargetError(f"{customer} is on this list twice.")
		seen.add(customer)
		cleaned.append(
			{
				"customer": customer,
				"target_amount": amount,
				"target_qty": qty,
				"uom": unit,
				"sales_person": clean_text(row.get("sales_person")) or None,
			}
		)
	return cleaned


def plan_bulk(rows, existing_by_customer) -> list:
	existing_by_customer = existing_by_customer or {}
	actions = []
	for row in rows:
		name = existing_by_customer.get(row["customer"]) or ""
		actions.append({**row, "existing": name, "action": "update" if name else "create"})
	return actions


def period_label(start, end, period_type) -> str:
	start = as_date(start)
	end = as_date(end)
	if not start or not end:
		return ""
	if period_type == "Monthly":
		return f"{MONTHS[start.month - 1]} {start.year}"
	return f"{MONTHS[start.month - 1]} {start.year} – {MONTHS[end.month - 1]} {end.year}"


def clean_filters(filters) -> dict:
	filters = filters or {}
	out = {}
	for key in ("company", "period_type", "from_date", "to_date", "customer", "sales_person", "status"):
		value = filters.get(key)
		if value not in (None, ""):
			out[key] = value
	if out.get("period_type") not in PERIOD_TYPES:
		out.pop("period_type", None)
	if out.get("status") not in STATUSES:
		out.pop("status", None)
	return out


def target_matches_filters(target, filters) -> bool:
	filters = filters or {}
	if filters.get("company") and target.get("company") != filters["company"]:
		return False
	if filters.get("customer") and target.get("customer") != filters["customer"]:
		return False
	if filters.get("sales_person") and target.get("sales_person") != filters["sales_person"]:
		return False
	if filters.get("period_type") and target.get("period_type") != filters["period_type"]:
		return False
	if filters.get("from_date") or filters.get("to_date"):
		start = filters.get("from_date") or date.min.isoformat()
		end = filters.get("to_date") or date.max.isoformat()
		if not periods_overlap(target.get("from_date"), target.get("to_date"), start, end):
			return False
	return True


def report_columns(currency=None, show_filters=False) -> list:
	money = {"fieldtype": "Currency", "options": currency or "", "width": 120}
	columns = [
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
		{"label": "Territory", "fieldname": "territory", "fieldtype": "Link", "options": "Territory", "width": 140},
		{"label": "Sales Person", "fieldname": "sales_person", "fieldtype": "Data", "width": 150},
		{"label": "Period", "fieldname": "period", "fieldtype": "Data", "width": 140},
	]
	if show_filters:
		columns.extend(
			[
				{
					"label": "Item Group",
					"fieldname": "item_group",
					"fieldtype": "Link",
					"options": "Item Group",
					"width": 140,
				},
				{"label": "Brand", "fieldname": "brand", "fieldtype": "Link", "options": "Brand", "width": 120},
			]
		)
	columns.extend(
		[
			{"label": "Target", "fieldname": "target_amount", **money},
			{"label": "Achieved", "fieldname": "achieved_amount", **money},
			{"label": "Gap", "fieldname": "gap", **money},
			{"label": "Achievement %", "fieldname": "achievement_pct", "fieldtype": "Percent", "width": 130},
			{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
		]
	)
	return columns


def report_row(target, figures) -> dict:
	sales = clean_text(target.get("sales_person")) or clean_text(target.get("sales_user"))
	return {
		"customer": target.get("customer"),
		"customer_name": clean_text(target.get("customer_name")) or target.get("customer") or "",
		"territory": clean_text(target.get("territory")),
		"sales_person": sales,
		"period": period_label(target.get("from_date"), target.get("to_date"), target.get("period_type")),
		"item_group": clean_text(target.get("item_group")),
		"brand": clean_text(target.get("brand")),
		"target_amount": round(float(target.get("target_amount") or 0), 2),
		"achieved_amount": figures["achieved_amount"],
		"gap": figures["gap"],
		"achievement_pct": figures["achievement_pct"],
		"status": figures["status"],
		"colour": indicator_colour(figures["achievement_pct"]),
		"is_total": 0,
	}


def total_row(rows) -> dict:
	target = round(sum(float(row.get("target_amount") or 0) for row in rows), 2)
	achieved = round(sum(float(row.get("achieved_amount") or 0) for row in rows), 2)
	figures = achievement_figures(target, achieved, None, None, None)
	return {
		"customer": "Total",
		"customer_name": "Total",
		"territory": "",
		"sales_person": "",
		"period": "",
		"item_group": "",
		"brand": "",
		"target_amount": target,
		"achieved_amount": achieved,
		"gap": figures["gap"],
		"achievement_pct": figures["achievement_pct"],
		"status": "",
		"colour": indicator_colour(figures["achievement_pct"]),
		"is_total": 1,
	}


def chart_for(rows):
	body = [row for row in rows if not row.get("is_total")]
	if not body:
		return None
	ranked = sorted(body, key=lambda row: float(row.get("target_amount") or 0), reverse=True)[:CHART_LIMIT]
	return {
		"data": {
			"labels": [row.get("customer_name") or row.get("customer") for row in ranked],
			"datasets": [
				{"name": "Target", "values": [row["target_amount"] for row in ranked]},
				{"name": "Achieved", "values": [row["achieved_amount"] for row in ranked]},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 0},
		"colors": ["#b8b8b8", "#4c84ff"],
	}


def summary_for(total, currency):
	indicator = {"green": "Green", "orange": "Orange", "red": "Red"}[total["colour"]]
	money = currency or ""
	return [
		{"value": total["target_amount"], "label": "Target", "datatype": "Currency", "currency": money},
		{"value": total["achieved_amount"], "label": "Achieved", "datatype": "Currency", "currency": money},
		{"value": total["gap"], "label": "Gap", "datatype": "Currency", "currency": money},
		{
			"value": total["achievement_pct"],
			"label": "Achievement %",
			"datatype": "Percent",
			"indicator": indicator,
		},
	]


def build_report(targets, lines, descendants, filters, viewer, today, currency=None) -> dict:
	filters = clean_filters(filters)
	chosen = [
		target
		for target in targets or []
		if can_see_target(viewer, target) and target_matches_filters(target, filters)
	]
	figures = achievement_for_targets(chosen, lines, descendants, today)
	rows = []
	for target in chosen:
		fig = figures[target.get("name")]
		if filters.get("status") and fig["status"] != filters["status"]:
			continue
		rows.append(report_row(target, fig))
	rows.sort(key=lambda row: ((row.get("customer_name") or "").lower(), row.get("period") or ""))
	show_filters = any(row.get("item_group") or row.get("brand") for row in rows)
	chart = chart_for(rows)
	message = ""
	if len(rows) > CHART_LIMIT:
		message = f"Chart shows the {CHART_LIMIT} largest targets."
	data = rows
	summary = None
	if rows:
		total = total_row(rows)
		data = rows + [total]
		summary = summary_for(total, currency)
	return {
		"columns": report_columns(currency, show_filters),
		"rows": data,
		"chart": chart,
		"summary": summary,
		"message": message,
	}


def workspace_shortcut(link) -> dict:
	is_report = link["link_type"] == "Report"
	return {
		"label": link["label"],
		"link_to": link["link_to"],
		"type": "Report" if is_report else "DocType",
		"icon": link["icon"],
		"color": "",
		"url": "",
		"stats_filter": "",
		"format": "",
		"doc_view": "" if is_report else "List",
		"report_ref_doctype": "Customer Primary Target" if is_report else "",
	}


def workspace_block(link, col) -> dict:
	slug = link["link_to"].lower().replace(" ", "-")
	return {"id": f"mb-{slug}", "type": "shortcut", "data": {"shortcut_name": link["label"], "col": col}}


def workspace_link(link) -> dict:
	is_report = link["link_type"] == "Report"
	return {
		"type": "Link",
		"label": link["label"],
		"link_type": "Report" if is_report else "DocType",
		"link_to": link["link_to"],
		"hidden": 0,
		"is_query_report": 1 if is_report else 0,
		"link_count": 0,
		"onboard": 0,
		"dependencies": "",
	}


def merge_workspace(shortcuts, content, links, col=3) -> dict:
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
	for link in TARGET_LINKS:
		label = link["label"]
		if label not in labels:
			shortcuts.append(workspace_shortcut(link))
			labels.add(label)
			changed = True
		if label not in block_names:
			content.append(workspace_block(link, col))
			block_names.add(label)
			changed = True
		if label not in link_labels:
			if "Targets" not in link_labels:
				links.append(
					{
						"type": "Card Break",
						"label": "Targets",
						"hidden": 0,
						"is_query_report": 0,
						"link_count": 0,
						"onboard": 0,
					}
				)
				link_labels.add("Targets")
			links.append(workspace_link(link))
			link_labels.add(label)
			changed = True
	return {"shortcuts": shortcuts, "content": content, "links": links, "changed": changed}


def missing_sidebar_links(existing) -> list:
	have = {(link_type, link_to) for link_type, link_to in existing or []}
	missing = []
	for link in TARGET_LINKS:
		if (link["link_type"], link["link_to"]) in have:
			continue
		missing.append({**link, "added": 1, "hidden": 0, "child": 0})
	return missing
