# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Load vans once per request and apply the rules in vans.py."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from melliflous_branding.divisions import MIMT_COMPANY
from melliflous_branding.vans import (
	SEED_OWNER_EMAIL,
	SK_DIVISION,
	VanError,
	add_secondary_qty,
	beat_status,
	can_open_vans_360,
	cash_balances,
	collections_summary,
	exceptions,
	fleet_overview,
	line_amount,
	map_fa_lines,
	material_issue_payload,
	may_delete,
	may_edit,
	parse_fa_csv,
	parse_fa_xlsx,
	period_bounds,
	place_vans_360_app,
	report_figures,
	report_name,
	report_table,
	reported_vs_invoiced,
	rows_to_csv,
	rows_to_html,
	seed_vans,
	sees_division,
	sr_leaderboard,
	stock_action,
	transfer_payload,
	validate_report,
	van_access,
)

VAN_FIELDS = {
	"Sales Invoice": [
		{
			"fieldname": "custom_van",
			"label": "Van",
			"fieldtype": "Link",
			"options": "Van",
			"insert_after": "customer",
			"search_index": 1,
		}
	],
	"Payment Entry": [
		{
			"fieldname": "custom_van",
			"label": "Van",
			"fieldtype": "Link",
			"options": "Van",
			"insert_after": "party",
			"search_index": 1,
		}
	],
}

ROLES = (
	{"role_name": "Van Manager", "desk_access": 1},
	{"role_name": "Van Editor", "desk_access": 1},
	{"role_name": "Van Reader", "desk_access": 1},
)


def ensure_vans() -> None:
	"""Roles, the Van field, and the seven seeded vans. Safe to run again."""
	if not frappe.db.exists("DocType", "Role"):
		return
	for row in ROLES:
		if not frappe.db.exists("Role", row["role_name"]):
			frappe.get_doc({"doctype": "Role", **row}).insert(ignore_permissions=True)
	_ensure_van_fields()
	_seed_van_rows()
	_grant_named_users()


def _ensure_van_fields() -> None:
	if not frappe.db.exists("DocType", "Custom Field"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	specs = {}
	for doctype, fields in VAN_FIELDS.items():
		if frappe.db.exists("DocType", doctype):
			specs[doctype] = fields
	if specs:
		create_custom_fields(specs, update=True)


def _seed_van_rows() -> None:
	if not frappe.db.table_exists("Van"):
		return
	company = MIMT_COMPANY if frappe.db.exists("Company", MIMT_COMPANY) else None
	division = SK_DIVISION if frappe.db.exists("Division", SK_DIVISION) else None
	for row in seed_vans():
		if frappe.db.exists("Van", row["code"]):
			continue
		doc = frappe.get_doc({"doctype": "Van", **row})
		if company:
			doc.company = company
		if division:
			doc.division = division
		doc.insert(ignore_permissions=True)


def _grant_named_users() -> None:
	if not frappe.db.table_exists("User"):
		return
	for row in frappe.get_all("User", fields=["name", "email"]):
		blob = f"{row.name} {row.email or ''}".lower()
		if row.name == "Administrator" or SEED_OWNER_EMAIL in blob:
			_add_role(row.name, "Van Manager")
		elif "priti" in blob:
			_add_role(row.name, "Van Editor")
		elif "sasank" in blob:
			_add_role(row.name, "Van Reader")


def _add_role(user, role) -> None:
	if not frappe.db.exists("User", user) or not frappe.db.exists("Role", role):
		return
	if frappe.db.exists("Has Role", {"parent": user, "role": role, "parenttype": "User"}):
		return
	frappe.get_doc("User", user).add_roles(role)


def prepare_report(doc) -> None:
	van = frappe.db.get_value("Van", doc.van, ["code", "company", "division", "daily_target", "dedicated_sr", "sales_officer"], as_dict=True) if doc.van else None
	if van:
		doc.company = van.company
		doc.division = van.division
		if not doc.target:
			doc.target = van.daily_target
		if not doc.worked_by and van.dedicated_sr:
			doc.worked_by = van.dedicated_sr
		if not doc.sales_officer and van.sales_officer:
			doc.sales_officer = van.sales_officer
		code = van.code
	else:
		code = doc.van
	figures = report_figures(doc.sales, doc.cash, doc.online, doc.credit, doc.discount)
	doc.total_collected = figures["total_collected"]
	doc.mismatch = figures["mismatch"]
	for row in doc.get("items") or []:
		row.amount = line_amount(row.qty, row.rate)
	existing = 0
	if doc.van and doc.date and frappe.db.table_exists("Van Daily Report"):
		existing = frappe.db.count(
			"Van Daily Report",
			{"van": doc.van, "date": doc.date, "name": ["!=", doc.name or ""], "docstatus": ["!=", 2]},
		)
	try:
		validate_report(
			{
				"van": doc.van,
				"date": doc.date,
				"worked": doc.worked,
				"reason": doc.reason,
				"coverage": doc.coverage,
				"second_sr": doc.second_sr,
				"second_beat": doc.second_beat,
				"entry_mode": doc.entry_mode,
			},
			existing,
		)
	except VanError as exc:
		frappe.throw(_(str(exc)))
	if doc.is_new() and not doc.name:
		doc.name = report_name(code, doc.date, existing)


def post_report_stock(doc) -> None:
	"""Submit path. Amount-only reports stay pending until SKU lines are added."""
	van = frappe.db.get_value(
		"Van",
		doc.van,
		["van_type", "warehouse", "distributor", "company", "code"],
		as_dict=True,
	) or {}
	items = [{"item": row.item, "qty": row.qty, "rate": row.rate, "uom": getattr(row, "uom", None)} for row in doc.get("items") or []]
	action = stock_action(van.get("van_type"), doc.entry_mode, items, doc.stock_updated)
	if action == "done":
		return
	if action == "pending":
		frappe.db.set_value("Van Daily Report", doc.name, {"stock_pending": 1, "stock_updated": 0}, update_modified=False)
		return
	if action == "material_issue":
		payload = material_issue_payload(van.get("company") or doc.company, van.get("warehouse"), items, doc.date, van.get("code"))
		entry = frappe.get_doc(payload)
		entry.insert(ignore_permissions=True)
		entry.submit()
		frappe.db.set_value(
			"Van Daily Report",
			doc.name,
			{"stock_entry": entry.name, "stock_updated": 1, "stock_pending": 0},
			update_modified=False,
		)
		return
	_apply_secondary(van.get("distributor"), van.get("company") or doc.company, doc.date, items)
	frappe.db.set_value("Van Daily Report", doc.name, {"stock_updated": 1, "stock_pending": 0}, update_modified=False)


def _apply_secondary(distributor, company, day, items) -> None:
	if not distributor or not frappe.db.table_exists("Distributor Stock Statement"):
		return
	month = getdate(day).replace(day=1) if day else None
	name = frappe.db.get_value(
		"Distributor Stock Statement",
		{"distributor": distributor, "company": company, "docstatus": ["!=", 2]},
		"name",
		order_by="from_date desc",
	)
	if not name:
		return
	statement = frappe.get_doc("Distributor Stock Statement", name)
	if month and statement.get("from_date") and getdate(statement.from_date).replace(day=1) != month:
		return
	sales = {}
	for row in items:
		if row.get("item"):
			sales[row["item"]] = sales.get(row["item"], 0) + float(row.get("qty") or 0)
	current = [row.as_dict() for row in statement.get("items") or []]
	updated = add_secondary_qty(current, sales)
	statement.set("items", [])
	for row in updated:
		statement.append("items", row)
	statement.flags.ignore_permissions = True
	statement.save(ignore_permissions=True)


def has_van_permission(doc, ptype, user) -> bool:
	email = frappe.db.get_value("User", user, "email") if user else ""
	roles = frappe.get_roles(user) if user else []
	if ptype == "delete" and not may_delete(user, email, roles):
		return False
	if ptype in {"write", "create", "submit"} and not may_edit(user, email, roles):
		return False
	if not doc:
		return van_access(user, email, roles) != "none"
	division = doc.get("division") if isinstance(doc, dict) else getattr(doc, "division", "")
	company = doc.get("company") if isinstance(doc, dict) else getattr(doc, "company", "")
	return sees_division(user, email, roles, division, company)


def van_permission_query(user) -> str:
	return _division_query(user, "Van")


def report_permission_query(user) -> str:
	return _division_query(user, "Van Daily Report")


def beat_permission_query(user) -> str:
	return _division_query(user, "Van Beat")


def cash_permission_query(user) -> str:
	return _division_query(user, "Cash Transfer")


def _division_query(user, doctype) -> str:
	email = frappe.db.get_value("User", user, "email") if user else ""
	roles = frappe.get_roles(user) if user else []
	if van_access(user, email, roles) == "none":
		return "1=0"
	if "sasank" in f"{user} {email or ''}".lower():
		return f"`tab{doctype}`.division = 'SK Gourmet Spices'"
	return ""


def place_vans_boot(app_data, user) -> list:
	email = ""
	roles = []
	if user:
		email = frappe.db.get_value("User", user, "email") or ""
		try:
			roles = frappe.get_roles(user)
		except Exception:
			roles = []
	return place_vans_360_app(app_data, user, email, roles)


@frappe.whitelist()
def vans_dashboard(company=None, division=None, preset="MTD", start=None, end=None, van=None):
	"""One payload for the page. Reports in the period are loaded once."""
	_require_reader()
	start_d, end_d = period_bounds(preset, today(), start, end)
	vans = _vans(company, division, van)
	codes = [row.code for row in vans]
	reports = _reports(codes, start_d, end_d) if codes else []
	invoices = _invoices(codes, start_d, end_d) if codes else []
	beats = _beats(codes) if codes else []
	transfers = _transfers(company, division)
	return {
		"overview": fleet_overview(vans, reports, today(), start_d, end_d),
		"vans": [row.as_dict() if hasattr(row, "as_dict") else row for row in vans],
		"leaderboard": sr_leaderboard(reports, start_d, end_d),
		"collections": collections_summary(reports, start_d, end_d),
		"beats": beat_status(beats, reports, today()),
		"exceptions": exceptions(vans, reports, start_d, end_d),
		"reported_vs_invoiced": reported_vs_invoiced(reports, invoices, start_d, end_d),
		"cash": {"balances": cash_balances(reports, transfers), "transfers": transfers[:20]},
		"stock": _stock(vans),
	}


def _require_reader() -> None:
	user = frappe.session.user
	email = frappe.db.get_value("User", user, "email") if user else ""
	if van_access(user, email, frappe.get_roles(user)) == "none":
		frappe.throw(_("You cannot open Vans 360."), frappe.PermissionError)


def _vans(company, division, van):
	filters = {}
	if company:
		filters["company"] = company
	if division:
		filters["division"] = division
	if van:
		filters["name"] = van
	if not frappe.db.table_exists("Van"):
		return []
	return frappe.get_all(
		"Van",
		filters=filters,
		fields=["name", "code", "area", "van_type", "status", "daily_target", "company", "division", "warehouse", "distributor"],
		limit=200,
	)


def _reports(vans, start, end):
	if not vans or not frappe.db.table_exists("Van Daily Report"):
		return []
	return frappe.get_all(
		"Van Daily Report",
		filters={"van": ["in", vans], "date": ["between", [start, end]], "docstatus": ["!=", 2]},
		fields=[
			"name", "date", "van", "worked", "reason", "worked_by", "sales", "target", "cash", "online",
			"credit", "discount", "mismatch", "counters_visited", "productive_counters", "new_outlets",
			"cash_held_by", "beat", "modified", "entry_mode", "stock_updated",
		],
		limit=5000,
	)


def _invoices(vans, start, end):
	if not vans or not frappe.db.has_column("Sales Invoice", "custom_van"):
		return []
	return frappe.get_all(
		"Sales Invoice",
		filters={"custom_van": ["in", vans], "posting_date": ["between", [start, end]], "docstatus": 1},
		fields=["name", "custom_van as van", "posting_date", "grand_total", "docstatus"],
		limit=5000,
	)


def _beats(vans):
	if not frappe.db.table_exists("Van Beat"):
		return []
	return frappe.get_all(
		"Van Beat",
		filters={"van": ["in", vans]},
		fields=["name", "beat_name", "van", "planned_counters", "every_n_days", "active"],
		limit=500,
	)


def _transfers(company, division):
	if not frappe.db.table_exists("Cash Transfer"):
		return []
	filters = {}
	if company:
		filters["company"] = company
	if division:
		filters["division"] = division
	return frappe.get_all(
		"Cash Transfer",
		filters=filters,
		fields=["name", "posting_date", "from_holder", "to_holder", "to_bank", "amount", "reference"],
		order_by="posting_date desc",
		limit=50,
	)


def _stock(vans):
	rows = []
	company_vans = [row for row in vans if row.get("van_type") == "Company Van" and row.get("warehouse")]
	if not company_vans or not frappe.db.table_exists("Bin"):
		return rows
	warehouses = [row.warehouse for row in company_vans]
	bins = frappe.get_all(
		"Bin",
		filters={"warehouse": ["in", warehouses]},
		fields=["warehouse", "item_code", "actual_qty"],
		limit=2000,
	)
	by_warehouse = {}
	for row in bins:
		by_warehouse.setdefault(row.warehouse, []).append({"item": row.item_code, "qty": row.actual_qty})
	for van in company_vans:
		rows.append({"van": van.code, "warehouse": van.warehouse, "items": by_warehouse.get(van.warehouse, [])[:30]})
	return rows


@frappe.whitelist()
def upload_fieldassist(report, filename=None, filedata=None):
	"""Parse a CSV or xlsx and return mapped lines plus SKUs that still need a map."""
	_require_reader()
	if not filedata:
		frappe.throw(_("Choose a file."))
	import base64

	raw = filedata
	if isinstance(raw, str) and "," in raw[:80]:
		raw = raw.split(",", 1)[-1]
	try:
		blob = base64.b64decode(raw)
	except Exception:
		blob = raw.encode() if isinstance(raw, str) else raw
	name = (filename or "").lower()
	try:
		if name.endswith(".xlsx"):
			parsed = parse_fa_xlsx(blob)
		else:
			parsed = parse_fa_csv(blob.decode("utf-8", errors="replace") if isinstance(blob, bytes) else blob)
	except VanError as exc:
		frappe.throw(_(str(exc)))
	item_map = {}
	if frappe.db.table_exists("FieldAssist Item Map"):
		for row in frappe.get_all("FieldAssist Item Map", fields=["fa_sku", "item"], limit=5000):
			item_map[row.fa_sku] = row.item
	mapped = map_fa_lines(parsed, item_map)
	mapped["report"] = report
	return mapped


@frappe.whitelist()
def catch_up_stock(report):
	"""Add stock for a report that was filed as an amount and later given SKU lines."""
	_require_reader()
	doc = frappe.get_doc("Van Daily Report", report)
	if cint(doc.docstatus) != 1:
		frappe.throw(_("Submit the report before updating stock."))
	post_report_stock(doc)
	return {"stock_updated": frappe.db.get_value("Van Daily Report", report, "stock_updated")}


@frappe.whitelist()
def move_van_stock(van, direction, items, posting_date=None, depot=None):
	"""direction load moves depot to the van. unload moves the van back to the depot."""
	_require_reader()
	record = frappe.get_doc("Van", van)
	if record.van_type != "Company Van":
		frappe.throw(_("Only a company van keeps stock in a warehouse."))
	if isinstance(items, str):
		items = frappe.parse_json(items)
	source, target = (depot, record.warehouse) if direction == "load" else (record.warehouse, depot)
	try:
		payload = transfer_payload(record.company, source, target, items, posting_date or today(), f"Van {record.code} {direction}")
	except VanError as exc:
		frappe.throw(_(str(exc)))
	entry = frappe.get_doc(payload)
	entry.insert(ignore_permissions=True)
	entry.submit()
	return {"stock_entry": entry.name}


@frappe.whitelist()
def van_report_download(kind="Detailed sales", company=None, division=None, preset="MTD", start=None, end=None, file_format="csv"):
	_require_reader()
	start_d, end_d = period_bounds(preset, today(), start, end)
	vans = _vans(company, division, None)
	codes = [row.code for row in vans]
	reports = _reports(codes, start_d, end_d)
	for row in reports:
		row["items"] = frappe.get_all(
			"Van Daily Report Item",
			filters={"parent": row.name},
			fields=["item", "qty", "rate", "amount"],
		)
	beats = _beats(codes)
	transfers = _transfers(company, division)
	columns, data = report_table(kind, reports, vans, beats, transfers, today())
	if (file_format or "").lower() == "html":
		return {"filename": "vans.html", "body": rows_to_html(kind, columns, data)}
	return {"filename": "vans.csv", "body": rows_to_csv(columns, data)}


def report_execute(filters=None):
	filters = filters or {}
	user = frappe.session.user
	email = frappe.db.get_value("User", user, "email") if user else ""
	if not sees_division(user, email, frappe.get_roles(user), filters.get("division"), filters.get("company")):
		return [], []
	result = van_report_download(
		filters.get("kind") or "Detailed sales",
		filters.get("company"),
		filters.get("division"),
		filters.get("preset") or "MTD",
		filters.get("start"),
		filters.get("end"),
		"csv",
	)
	# The script report wants columns as dicts. Rebuild from the CSV header.
	import csv
	import io

	reader = csv.reader(io.StringIO(result["body"]))
	rows = list(reader)
	if not rows:
		return [], []
	columns = [{"label": name, "fieldname": name.lower().replace(" ", "_"), "fieldtype": "Data", "width": 120} for name in rows[0]]
	data = []
	for line in rows[1:]:
		data.append({column["fieldname"]: line[index] if index < len(line) else "" for index, column in enumerate(columns)})
	return columns, data
