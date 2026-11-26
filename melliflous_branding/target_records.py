# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Save, score, and report Customer Primary Target. The rules live in targets.py."""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import getdate

from melliflous_branding.targets import (
	EDIT_ROLES,
	READ_PTYPES,
	SIDEBAR_MODULES,
	TARGET_LINKS,
	WORKSPACE_NAMES,
	TargetError,
	achievement_for_targets,
	as_date,
	as_flag,
	build_report,
	can_edit_targets,
	can_see_target,
	clean_bulk_rows,
	clean_filters,
	clean_text,
	missing_sidebar_links,
	month_bounds,
	plan_bulk,
	saved_period,
	workspace_block,
	workspace_link,
	workspace_shortcut,
)

TARGET_FIELDS = [
	"name",
	"customer",
	"company",
	"from_date",
	"to_date",
	"period_type",
	"target_amount",
	"target_qty",
	"uom",
	"item_group",
	"brand",
	"sales_person",
	"sales_user",
	"owner",
	"currency",
	"achieved_amount",
	"achieved_qty",
	"gap",
	"achievement_pct",
	"status",
]

FIGURE_FIELDS = ("achieved_amount", "achieved_qty", "gap", "achievement_pct", "status")


def _quietly(title, fn):
	try:
		return fn()
	except Exception:
		frappe.log_error(title=title)
		return None


def require_editor():
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	if not can_edit_targets(frappe.get_roles(user), user):
		frappe.throw(_("Only a Sales Manager can set targets."), frappe.PermissionError)


def fiscal_start_month() -> int:
	if not frappe.db.table_exists("Fiscal Year"):
		return 4
	today = frappe.utils.today()
	rows = frappe.db.sql(
		"""
		select year_start_date
		from `tabFiscal Year`
		where year_start_date <= %s and year_end_date >= %s
		order by year_start_date desc
		limit 1
		""",
		(today, today),
	)
	if not rows or not rows[0][0]:
		return 4
	return as_date(rows[0][0]).month


def company_currency(company):
	if not company or not frappe.db.table_exists("Company"):
		return None
	return frappe.db.get_value("Company", company, "default_currency")


def sales_persons_for_user(user) -> list:
	if not user or not frappe.db.table_exists("Sales Person") or not frappe.db.table_exists("Employee"):
		return []
	sales_columns = set(frappe.db.get_table_columns("Sales Person") or [])
	employee_columns = set(frappe.db.get_table_columns("Employee") or [])
	if "employee" not in sales_columns or "user_id" not in employee_columns:
		return []
	return frappe.db.sql(
		"""
		select sp.name
		from `tabSales Person` sp
		inner join `tabEmployee` emp on emp.name = sp.employee
		where emp.user_id = %s
		""",
		user,
		pluck=True,
	)


@frappe.whitelist()
def user_for_sales_person(sales_person):
	if not frappe.has_permission("Customer Primary Target", "read"):
		frappe.throw(_("You are not allowed to do this."), frappe.PermissionError)
	if not sales_person or not frappe.db.table_exists("Sales Person") or not frappe.db.table_exists("Employee"):
		return None
	sales_columns = set(frappe.db.get_table_columns("Sales Person") or [])
	employee_columns = set(frappe.db.get_table_columns("Employee") or [])
	if "employee" not in sales_columns or "user_id" not in employee_columns:
		return None
	employee = frappe.db.get_value("Sales Person", sales_person, "employee")
	if not employee:
		return None
	return frappe.db.get_value("Employee", employee, "user_id") or None


def get_permission_query_conditions(user=None):
	"""Sales User reads targets they own or that belong to their Sales Person."""
	user = user or frappe.session.user
	if not user or user == "Administrator":
		return ""
	roles = set(frappe.get_roles(user))
	if roles.intersection(EDIT_ROLES) or "Sales User" not in roles:
		return ""
	escaped = frappe.db.escape(user)
	parts = [
		f"`tabCustomer Primary Target`.`owner` = {escaped}",
		f"`tabCustomer Primary Target`.`sales_user` = {escaped}",
	]
	persons = sales_persons_for_user(user)
	if persons:
		quoted = ", ".join(frappe.db.escape(person) for person in persons)
		parts.append(f"`tabCustomer Primary Target`.`sales_person` in ({quoted})")
	return "(" + " or ".join(parts) + ")"


def has_target_permission(doc, ptype="read", user=None):
	if not doc or isinstance(doc, str):
		return True
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or roles.intersection(EDIT_ROLES):
		return True
	if "Sales User" not in roles:
		return True
	if ptype not in READ_PTYPES:
		return False
	viewer = {"user": user, "roles": roles, "sales_persons": sales_persons_for_user(user)}
	return can_see_target(viewer, doc)


def _chunks(values, size):
	values = list(values)
	for index in range(0, len(values), size):
		yield values[index : index + size]


def _line_sql():
	if not frappe.db.table_exists("Sales Invoice") or not frappe.db.table_exists("Sales Invoice Item"):
		return None
	item = set(frappe.db.get_table_columns("Sales Invoice Item") or [])
	invoice = set(frappe.db.get_table_columns("Sales Invoice") or [])
	if "base_net_amount" in item:
		amount = "sii.`base_net_amount`"
	elif "net_amount" in item:
		amount = "sii.`net_amount`"
	else:
		return None
	if "posting_date" not in invoice or "customer" not in invoice or "company" not in invoice:
		return None

	def item_expr(name):
		if name in item:
			return f"sii.`{name}`"
		return "null"

	is_return = "si.`is_return`" if "is_return" in invoice else "0"
	return f"""
		select si.customer as customer, si.company as company, si.posting_date as posting_date,
			{is_return} as is_return, {amount} as amount,
			{item_expr("qty")} as qty, {item_expr("stock_qty")} as stock_qty,
			{item_expr("uom")} as uom, {item_expr("stock_uom")} as stock_uom,
			{item_expr("item_group")} as item_group, {item_expr("brand")} as brand
		from `tabSales Invoice` si
		inner join `tabSales Invoice Item` sii on sii.parent = si.name
		where si.docstatus = 1
			and si.posting_date between %s and %s
			and si.company in %s
			and si.customer in %s
	"""


def fetch_lines(targets) -> list:
	query = _line_sql()
	if not query or not targets:
		return []
	customers = sorted({clean_text(_value(row, "customer")) for row in targets if clean_text(_value(row, "customer"))})
	companies = sorted({clean_text(_value(row, "company")) for row in targets if clean_text(_value(row, "company"))})
	dates = []
	for row in targets:
		for field in ("from_date", "to_date"):
			day = as_date(_value(row, field))
			if day:
				dates.append(day)
	if not customers or not companies or not dates:
		return []
	start, end = min(dates), max(dates)
	lines = []
	for chunk in _chunks(customers, 300):
		lines.extend(frappe.db.sql(query, (start, end, companies, chunk), as_dict=True))
	for line in lines:
		line["is_return"] = as_flag(line.get("is_return"))
	return lines


def _value(row, field):
	if isinstance(row, dict):
		return row.get(field)
	return getattr(row, field, None)


def descendant_map(item_groups) -> dict:
	groups = [group for group in dict.fromkeys(item_groups or []) if group]
	if not groups or not frappe.db.table_exists("Item Group"):
		return {group: {group} for group in groups}
	columns = set(frappe.db.get_table_columns("Item Group") or [])
	has_tree = "lft" in columns and "rgt" in columns
	result = {}
	for group in groups:
		if not has_tree:
			result[group] = {group}
			continue
		bounds = frappe.db.get_value("Item Group", group, ["lft", "rgt"], as_dict=True)
		if not bounds:
			result[group] = {group}
			continue
		names = frappe.db.sql(
			"select name from `tabItem Group` where lft >= %s and rgt <= %s",
			(bounds.lft, bounds.rgt),
			pluck=True,
		)
		result[group] = set(names) or {group}
	return result


def target_dict(doc) -> dict:
	return {
		"name": doc.name or "new",
		"customer": doc.customer,
		"company": doc.company,
		"from_date": doc.from_date,
		"to_date": doc.to_date,
		"target_amount": doc.target_amount,
		"target_qty": doc.target_qty,
		"uom": doc.uom,
		"item_group": doc.item_group,
		"brand": doc.brand,
	}


def figures_changed(current, figures) -> bool:
	for key, places in (("achieved_amount", 2), ("gap", 2), ("achievement_pct", 2), ("achieved_qty", 3)):
		if round(float(current.get(key) or 0), places) != round(float(figures.get(key) or 0), places):
			return True
	return (current.get("status") or "") != figures["status"]


def apply_figures(doc, persist):
	if not doc.customer or not doc.company or not doc.from_date or not doc.to_date:
		return
	target = target_dict(doc)
	lines = fetch_lines([target])
	descendants = descendant_map([doc.item_group] if doc.item_group else [])
	figures = achievement_for_targets([target], lines, descendants, frappe.utils.today())[target["name"]]
	changed = figures_changed(doc, figures)
	for key in FIGURE_FIELDS:
		doc.set(key, figures[key])
	if persist and changed and doc.name and not doc.is_new():
		frappe.db.set_value("Customer Primary Target", doc.name, figures, update_modified=False)


def overlapping_targets(doc, current_name):
	from melliflous_branding.targets import find_overlap

	rows = frappe.db.sql(
		"""
		select name, from_date, to_date, item_group, brand
		from `tabCustomer Primary Target`
		where customer = %s and company = %s
			and from_date <= %s and to_date >= %s
		""",
		(doc.customer, doc.company, doc.to_date, doc.from_date),
		as_dict=True,
	)
	return find_overlap(rows, doc.from_date, doc.to_date, doc.item_group, doc.brand, current_name)


def prepare_target(doc):
	from melliflous_branding.targets import assigned_owner, clean_qty, require_target_amount

	if not doc.company:
		doc.company = frappe.defaults.get_user_default("company")
	if not doc.naming_series:
		doc.naming_series = "CPT-.YYYY.-"
	try:
		period = saved_period(
			doc.period_type,
			doc.target_month,
			doc.target_quarter,
			doc.from_date,
			fiscal_start_month(),
		)
		doc.target_amount = require_target_amount(doc.target_amount)
		qty, unit = clean_qty(doc.target_qty, doc.uom)
	except TargetError as exc:
		frappe.throw(str(exc))
	doc.period_type = period["period_type"]
	doc.target_month = period["target_month"]
	doc.target_quarter = period["target_quarter"]
	doc.from_date = period["from_date"]
	doc.to_date = period["to_date"]
	doc.item_group = clean_text(doc.item_group) or None
	doc.brand = clean_text(doc.brand) or None
	doc.sales_person = clean_text(doc.sales_person) or None
	doc.sales_user = clean_text(doc.sales_user) or None
	doc.uom = unit
	doc.target_qty = qty
	if doc.sales_person and not doc.sales_user:
		doc.sales_user = user_for_sales_person(doc.sales_person)
	doc.owner = assigned_owner(doc.sales_user, frappe.session.user)
	if not doc.currency and doc.company:
		doc.currency = company_currency(doc.company)
	current = doc.name if doc.name and not doc.is_new() else None
	hits = overlapping_targets(doc, current)
	if hits:
		other = hits[0]
		frappe.throw(
			_("This overlaps {0} for {1} ({2} to {3}) with the same item group and brand.").format(
				other.get("name"),
				doc.customer,
				frappe.format(other.get("from_date"), {"fieldtype": "Date"}),
				frappe.format(other.get("to_date"), {"fieldtype": "Date"}),
			)
		)
	apply_figures(doc, persist=False)


def refresh_achievement(doc, persist=True):
	apply_figures(doc, persist=persist)


def refresh_primary_targets():
	"""Daily job. Rewrites achieved amount, gap, percent, and status."""
	if not frappe.db.table_exists("Customer Primary Target"):
		return
	rows = frappe.get_all("Customer Primary Target", fields=TARGET_FIELDS, limit_page_length=10000)
	if not rows:
		return
	lines = fetch_lines(rows)
	descendants = descendant_map([row.item_group for row in rows if row.item_group])
	figures = achievement_for_targets(rows, lines, descendants, frappe.utils.today())
	for row in rows:
		fig = figures.get(row.name)
		if not fig or not figures_changed(row, fig):
			continue
		frappe.db.set_value(
			"Customer Primary Target",
			row.name,
			{key: fig[key] for key in FIGURE_FIELDS},
			update_modified=False,
		)


def primary_sales_people(customers) -> dict:
	if not customers or not frappe.db.table_exists("Sales Team"):
		return {}
	rows = frappe.db.sql(
		"""
		select parent, sales_person
		from `tabSales Team`
		where parenttype = 'Customer' and parent in %s
		order by ifnull(allocated_percentage, 0) desc
		""",
		(customers,),
		as_dict=True,
	)
	people = {}
	for row in rows:
		people.setdefault(row.parent, row.sales_person)
	return people


def existing_targets(company, start, end, item_group, brand, customers) -> dict:
	if not customers:
		return {}
	rows = frappe.db.sql(
		"""
		select name, customer, target_amount, target_qty, uom, sales_person
		from `tabCustomer Primary Target`
		where company = %s and from_date = %s and to_date = %s
			and ifnull(item_group, '') = %s and ifnull(brand, '') = %s
			and customer in %s
		""",
		(company, start, end, item_group or "", brand or "", customers),
		as_dict=True,
	)
	return {row.customer: row for row in rows}


@frappe.whitelist()
def period_dates(period_type, day):
	frappe.has_permission("Customer Primary Target", "read", throw=True)
	try:
		if period_type == "Quarterly":
			period = saved_period("Quarterly", None, day, day, fiscal_start_month())
		else:
			period = saved_period("Monthly", day, None, day, fiscal_start_month())
	except TargetError as exc:
		frappe.throw(str(exc))
	return {"from_date": period["from_date"].isoformat(), "to_date": period["to_date"].isoformat()}


@frappe.whitelist()
def sales_person_for_customer(customer):
	frappe.has_permission("Customer Primary Target", "read", throw=True)
	if not customer:
		return {"sales_person": None, "sales_user": None}
	person = primary_sales_people([customer]).get(customer)
	return {"sales_person": person, "sales_user": user_for_sales_person(person) if person else None}


@frappe.whitelist()
def customers_for_month(company, month, item_group=None, brand=None, sales_person=None, customer_group=None):
	require_editor()
	if not company or not month:
		frappe.throw(_("Pick a company and a month."))
	try:
		start, end = month_bounds(month)
	except TargetError as exc:
		frappe.throw(str(exc))
	if not frappe.db.table_exists("Customer"):
		frappe.throw(_("Customer is not installed on this site."))
	filters = {"disabled": ["!=", 1]}
	if customer_group:
		filters["customer_group"] = customer_group
	customers = frappe.get_list(
		"Customer",
		filters=filters,
		fields=["name", "customer_name", "territory"],
		order_by="customer_name asc",
		limit_page_length=501,
	)
	truncated = len(customers) > 500
	customers = customers[:500]
	if sales_person and frappe.db.table_exists("Sales Team"):
		allowed = set(
			frappe.db.sql(
				"""
				select parent from `tabSales Team`
				where parenttype = 'Customer' and sales_person = %s
				""",
				sales_person,
				pluck=True,
			)
		)
		customers = [row for row in customers if row.name in allowed]
	people = primary_sales_people([row.name for row in customers])
	existing = existing_targets(
		company,
		start,
		end,
		clean_text(item_group),
		clean_text(brand),
		[row.name for row in customers],
	)
	rows = []
	for row in customers:
		current = existing.get(row.name) or {}
		rows.append(
			{
				"customer": row.name,
				"customer_name": row.customer_name,
				"territory": row.territory,
				"sales_person": current.get("sales_person") or people.get(row.name) or "",
				"target_amount": current.get("target_amount"),
				"target_qty": current.get("target_qty"),
				"uom": current.get("uom"),
			}
		)
	return {
		"from_date": start.isoformat(),
		"to_date": end.isoformat(),
		"truncated": truncated,
		"rows": rows,
	}


@frappe.whitelist()
def create_monthly_targets(company, month, rows, item_group=None, brand=None):
	require_editor()
	frappe.has_permission("Customer Primary Target", "create", throw=True)
	if not company or not month:
		frappe.throw(_("Pick a company and a month."))
	try:
		start, end = month_bounds(month)
		if isinstance(rows, str):
			rows = json.loads(rows) if rows else []
		cleaned = clean_bulk_rows(rows)
	except TargetError as exc:
		frappe.throw(str(exc))
	except ValueError as exc:
		frappe.throw(str(exc))
	if not cleaned:
		frappe.throw(_("Enter a target amount for at least one customer."))
	item_group = clean_text(item_group) or None
	brand = clean_text(brand) or None
	existing = existing_targets(company, start, end, item_group, brand, [row["customer"] for row in cleaned])
	created = 0
	updated = 0
	for action in plan_bulk(cleaned, {customer: row.name for customer, row in existing.items()}):
		payload = {
			"customer": action["customer"],
			"company": company,
			"period_type": "Monthly",
			"target_month": start,
			"from_date": start,
			"to_date": end,
			"target_amount": action["target_amount"],
			"target_qty": action.get("target_qty"),
			"uom": action.get("uom"),
			"item_group": item_group,
			"brand": brand,
			"sales_person": action.get("sales_person"),
			"sales_user": user_for_sales_person(action.get("sales_person")) if action.get("sales_person") else None,
		}
		if action["action"] == "update":
			doc = frappe.get_doc("Customer Primary Target", action["existing"])
			doc.update(payload)
			doc.save()
			updated += 1
		else:
			doc = frappe.get_doc({"doctype": "Customer Primary Target", **payload})
			doc.insert()
			created += 1
	return {"created": created, "updated": updated}


def run_report(filters):
	filters = clean_filters(filters)
	if not filters.get("company"):
		return [], [], _("Pick a company."), None, None
	if not frappe.db.table_exists("Customer Primary Target"):
		return [], [], None, None, None
	list_filters = {"company": filters["company"]}
	for key in ("customer", "sales_person", "period_type"):
		if filters.get(key):
			list_filters[key] = filters[key]
	targets = frappe.get_list(
		"Customer Primary Target",
		filters=list_filters,
		fields=[
			"name",
			"customer",
			"company",
			"from_date",
			"to_date",
			"period_type",
			"target_amount",
			"target_qty",
			"uom",
			"item_group",
			"brand",
			"sales_person",
			"sales_user",
			"owner",
			"currency",
		],
		limit_page_length=5000,
		order_by="customer asc, from_date asc",
	)
	names = [row.customer for row in targets if row.customer]
	meta = {}
	if names and frappe.db.table_exists("Customer"):
		for row in frappe.get_all(
			"Customer",
			filters={"name": ["in", names]},
			fields=["name", "customer_name", "territory"],
			limit_page_length=len(names),
		):
			meta[row.name] = row
	enriched = []
	for row in targets:
		info = meta.get(row.customer)
		enriched.append(
			{
				**row,
				"customer_name": (info.customer_name if info else None) or row.customer,
				"territory": (info.territory if info else None) or "",
			}
		)
	lines = fetch_lines(enriched)
	descendants = descendant_map([row.get("item_group") for row in enriched])
	user = frappe.session.user
	viewer = {"user": user, "roles": frappe.get_roles(user), "sales_persons": sales_persons_for_user(user)}
	built = build_report(
		enriched,
		lines,
		descendants,
		filters,
		viewer,
		getdate(frappe.utils.today()),
		company_currency(filters["company"]),
	)
	columns = []
	for column in built["columns"]:
		column = dict(column)
		column["label"] = _(column["label"])
		columns.append(column)
	summary = built["summary"]
	if summary:
		for card in summary:
			card["label"] = _(card["label"])
	message = _(built["message"]) if built["message"] else None
	return columns, built["rows"], message, built["chart"], summary


def ensure_target_places():
	"""Add the two links to Selling and CRM without pinning those workspaces."""
	_quietly("Customer target sidebar", _ensure_sidebars)
	_quietly("Customer target workspace", _ensure_workspaces)


def _ensure_sidebars():
	if not frappe.db.table_exists("Custom Sidebar") or not frappe.db.table_exists("Module Def"):
		return
	for module in SIDEBAR_MODULES:
		if frappe.db.exists("Module Def", module):
			_add_sidebar_links(module)


def _add_sidebar_links(module):
	rows = frappe.get_all("Custom Sidebar", filters={"module": module}, fields=["name", "user"])
	site = next((row for row in rows if not row.user), None)
	if site:
		doc = frappe.get_doc("Custom Sidebar", site.name)
	else:
		doc = frappe.new_doc("Custom Sidebar")
		doc.module = module
	missing = missing_sidebar_links((row.link_type, row.link_to) for row in (doc.get("sidebar_items") or []))
	if not missing:
		return
	for link in missing:
		doc.append("sidebar_items", link)
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)


def _ensure_workspaces():
	if not frappe.db.table_exists("Workspace"):
		return
	for name in WORKSPACE_NAMES:
		if frappe.db.exists("Workspace", name):
			_add_workspace_links(name)


def _add_workspace_links(name):
	original = frappe.db.get_value("Workspace", name, "modified")
	doc = frappe.get_doc("Workspace", name)
	try:
		content = json.loads(doc.content or "[]")
	except ValueError:
		content = None
	labels = {row.label for row in doc.shortcuts}
	link_labels = {row.label for row in (doc.links or [])}
	block_names = set()
	if isinstance(content, list):
		for block in content:
			if isinstance(block, dict):
				block_names.add(clean_text((block.get("data") or {}).get("shortcut_name")))
	changed = False
	for link in TARGET_LINKS:
		label = link["label"]
		if label not in labels:
			doc.append("shortcuts", workspace_shortcut(link))
			labels.add(label)
			changed = True
		if isinstance(content, list) and label not in block_names:
			content.append(workspace_block(link, 3))
			block_names.add(label)
			changed = True
		if label not in link_labels:
			if "Targets" not in link_labels:
				doc.append(
					"links",
					{
						"type": "Card Break",
						"label": "Targets",
						"hidden": 0,
						"is_query_report": 0,
						"link_count": 0,
						"onboard": 0,
					},
				)
				link_labels.add("Targets")
			doc.append("links", workspace_link(link))
			link_labels.add(label)
			changed = True
	if not changed:
		return
	if isinstance(content, list):
		doc.content = json.dumps(content)
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.flags.ignore_mandatory = True
	doc.save(ignore_permissions=True)
	# Put the timestamp back so the next ERPNext migrate can still refresh this workspace.
	if original:
		frappe.db.sql("update `tabWorkspace` set modified=%s where name=%s", (original, name))
