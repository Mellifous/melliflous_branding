# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Save distributor records and serve Distributor 360. The rules live in distributors.py."""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import getdate

from melliflous_branding.distributors import (
	COMPLAINT_IDENTITY,
	DEFAULT_TARGET_AMOUNT,
	DISTRIBUTOR_CARD,
	DISTRIBUTOR_LINKS,
	GROWTH_FACTOR_DEFAULT,
	STATEMENT_IDENTITY,
	VISIT_IDENTITY,
	DistributorError,
	achievement_for_month,
	add_months,
	build_dashboard,
	build_distributor_mis,
	can_file,
	can_open_distributor_360,
	can_read_activity,
	can_see_profile,
	clean_complaint,
	clean_follow_up_filters,
	clean_growth_factor,
	clean_visit,
	find_duplicate_statement,
	follow_up_columns,
	follow_up_rows,
	is_manager,
	missing_sidebar_links,
	month_label,
	next_visit_due,
	normalize_lines,
	plan_target_save,
	prefill_rows,
	prepare_profile_values,
	received_by_item,
	recommended_monthly_target,
	statement_period,
	statement_period_key,
	trailing_months,
	workspace_block,
	workspace_link,
	workspace_shortcut,
)
from melliflous_branding.target_records import company_currency, require_editor, sales_persons_for_user
from melliflous_branding.targets import TargetError, as_flag, clean_text

PROFILE_FIELDS = (
	"name",
	"customer",
	"customer_name",
	"company",
	"account_manager",
	"sales_person",
	"salesman",
	"territory",
	"area",
	"counters",
	"visit_frequency",
	"last_visit_date",
	"next_visit_due",
	"is_active",
	"notes",
	"owner",
)


def _quietly(title, fn):
	try:
		return fn()
	except Exception:
		frappe.log_error(title=title)
		return None


def _viewer(user=None) -> dict:
	user = user or frappe.session.user
	return {"user": user, "roles": frappe.get_roles(user), "sales_persons": sales_persons_for_user(user)}


def _throw(exc):
	frappe.throw(str(exc))


def require_signed_in() -> str:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	return user


def _limited_user(user=None):
	"""A Sales User who is not a manager. None means the DocType permission is enough."""
	user = user or frappe.session.user
	if not user or user == "Administrator":
		return None
	roles = set(frappe.get_roles(user))
	if roles.intersection({"System Manager", "Sales Manager"}) or "Sales User" not in roles:
		return None
	return user


def _profile_match_sql(user, persons, table="`tabDistributor Profile`") -> str:
	escaped = frappe.db.escape(user)
	parts = [f"{table}.account_manager = {escaped}", f"{table}.salesman = {escaped}"]
	if persons:
		quoted = ", ".join(frappe.db.escape(person) for person in persons)
		parts.append(f"{table}.sales_person in ({quoted})")
	return "(" + " or ".join(parts) + ")"


def profile_permission_query(user=None):
	user = _limited_user(user)
	if not user:
		return ""
	return _profile_match_sql(user, sales_persons_for_user(user))


def _activity_permission_query(user, table, identity_columns, sales_person_column=False):
	user = _limited_user(user)
	if not user:
		return ""
	persons = sales_persons_for_user(user)
	escaped = frappe.db.escape(user)
	parts = [f"{table}.`{column}` = {escaped}" for column in identity_columns]
	if sales_person_column and persons:
		quoted = ", ".join(frappe.db.escape(person) for person in persons)
		parts.append(f"{table}.sales_person in ({quoted})")
	sub = (
		"select customer from `tabDistributor Profile` where "
		+ _profile_match_sql(user, persons, "`tabDistributor Profile`")
	)
	parts.append(f"{table}.distributor in ({sub})")
	return "(" + " or ".join(parts) + ")"


def visit_permission_query(user=None):
	return _activity_permission_query(user, "`tabDistributor Visit`", ("salesman", "owner"), True)


def statement_permission_query(user=None):
	return _activity_permission_query(user, "`tabDistributor Stock Statement`", ("owner",), False)


def complaint_permission_query(user=None):
	return _activity_permission_query(user, "`tabDistributor Complaint`", ("assigned_to", "owner"), False)


def _has_activity(doc, ptype, user, identity):
	if not doc or isinstance(doc, str):
		return True
	viewer = _viewer(user)
	if is_manager(viewer):
		return True
	if "Sales User" not in set(viewer["roles"]):
		return True
	if ptype == "delete":
		return False
	distributor = doc.get("distributor")
	profile = _profile_row(distributor) if distributor else None
	is_new = bool(getattr(doc, "is_new", lambda: False)())
	if ptype == "create" or is_new:
		return can_file(viewer, profile, is_new=True, owner=doc.get("owner"), distributor=distributor)
	if ptype == "write":
		before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
		previous = before.get("distributor") if before else distributor
		return can_file(
			viewer,
			profile,
			is_new=False,
			owner=doc.get("owner"),
			distributor=distributor,
			previous_distributor=previous,
		)
	return can_read_activity(viewer, doc, profile, identity)


def has_profile_permission(doc, ptype="read", user=None):
	if not doc or isinstance(doc, str):
		return True
	viewer = _viewer(user)
	if is_manager(viewer):
		return True
	if "Sales User" not in set(viewer["roles"]):
		return True
	if ptype == "delete" or ptype in {"write", "create", "import", "share"}:
		return False
	return can_see_profile(viewer, doc)


def has_visit_permission(doc, ptype="read", user=None):
	return _has_activity(doc, ptype, user, VISIT_IDENTITY)


def has_statement_permission(doc, ptype="read", user=None):
	return _has_activity(doc, ptype, user, STATEMENT_IDENTITY)


def has_complaint_permission(doc, ptype="read", user=None):
	return _has_activity(doc, ptype, user, COMPLAINT_IDENTITY)


def _profile_row(customer):
	if not customer or not frappe.db.table_exists("Distributor Profile"):
		return None
	row = frappe.db.get_value("Distributor Profile", {"customer": customer}, PROFILE_FIELDS, as_dict=True)
	return row


def _assert_can_file(doc):
	viewer = _viewer()
	profile = _profile_row(doc.get("distributor"))
	before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
	previous = before.get("distributor") if before else None
	if can_file(
		viewer,
		profile,
		is_new=bool(doc.is_new()),
		owner=doc.get("owner"),
		distributor=doc.get("distributor"),
		previous_distributor=previous,
	):
		return profile
	frappe.throw(_("This distributor is not assigned to you."), frappe.PermissionError)


def prepare_profile(doc):
	try:
		values = prepare_profile_values(
			{
				"customer": doc.customer,
				"company": doc.company,
				"visit_frequency": doc.visit_frequency,
				"counters": doc.counters,
				"is_active": doc.is_active,
				"area": doc.area,
				"last_visit_date": doc.last_visit_date,
			},
			getdate(frappe.utils.today()),
		)
	except DistributorError as exc:
		_throw(exc)
	for key, value in values.items():
		doc.set(key, value)


def link_existing_activity(doc):
	"""Point older visits, statements, and complaints at this profile."""
	if not doc.name or not doc.customer:
		return
	for doctype in ("Distributor Visit", "Distributor Stock Statement", "Distributor Complaint"):
		if not frappe.db.table_exists(doctype):
			continue
		frappe.db.sql(
			f"""
			update `tab{doctype}`
			set distributor_profile = %s
			where distributor = %s and ifnull(distributor_profile, '') = ''
			""",
			(doc.name, doc.customer),
		)


def prepare_visit(doc):
	if not doc.visit_date:
		doc.visit_date = frappe.utils.today()
	for row in list(doc.stock_lines or []):
		if not clean_text(row.item) and row.qty in (None, "", 0):
			doc.remove(row)
	profile = _assert_can_file(doc)
	try:
		clean_visit(doc.as_dict(), [row.as_dict() for row in (doc.stock_lines or [])])
	except DistributorError as exc:
		_throw(exc)
	_apply_profile_defaults(doc, profile)
	if not doc.salesman:
		doc.salesman = frappe.session.user if frappe.session.user != "Administrator" else doc.salesman


def sync_profile_visits(customer, exclude=None):
	if not customer or not frappe.db.table_exists("Distributor Profile") or not frappe.db.table_exists("Distributor Visit"):
		return
	profile_name = frappe.db.get_value(
		"Distributor Profile", {"customer": customer}, ["name", "visit_frequency"], as_dict=True
	)
	if not profile_name:
		return
	rows = frappe.get_all(
		"Distributor Visit",
		filters={"distributor": customer},
		fields=["name", "visit_date"],
		order_by="visit_date desc, modified desc",
		limit_page_length=30,
		ignore_permissions=True,
	)
	last = None
	for row in rows:
		if exclude and row.name == exclude:
			continue
		last = row.visit_date
		break
	try:
		due = next_visit_due(last, profile_name.visit_frequency, getdate(frappe.utils.today()))
	except DistributorError:
		due = None
	frappe.db.set_value(
		"Distributor Profile",
		profile_name.name,
		{"last_visit_date": last, "next_visit_due": due},
		update_modified=True,
	)


def prepare_statement(doc):
	if not doc.distributor:
		frappe.throw(_("Pick a distributor."))
	if not doc.company:
		frappe.throw(_("Pick a company."))
	if not doc.statement_month:
		frappe.throw(_("Pick a month."))
	for row in list(doc.items or []):
		if not clean_text(row.item) and not row.opening_qty and not row.secondary_qty and not row.primary_qty:
			doc.remove(row)
	profile = _assert_can_file(doc)
	try:
		start, end = statement_period(doc.statement_month)
	except (DistributorError, TargetError) as exc:
		_throw(exc)
	doc.statement_month = start
	doc.from_date = start
	doc.to_date = end
	doc.period_key = statement_period_key(doc.distributor, doc.company, start)
	if not doc.currency:
		doc.currency = company_currency(doc.company)
	current = doc.name if doc.name and not doc.is_new() else None
	others = []
	if frappe.db.table_exists("Distributor Stock Statement"):
		others = frappe.db.sql(
			"""
			select name, distributor, company, from_date
			from `tabDistributor Stock Statement`
			where distributor = %s and company = %s and from_date between %s and %s
			""",
			(doc.distributor, doc.company, start, end),
			as_dict=True,
		)
	duplicate = find_duplicate_statement(others, doc.distributor, doc.company, start, current)
	if duplicate:
		frappe.throw(
			_("{0} already has a stock statement for {1} ({2}).").format(
				doc.distributor, month_label(start), duplicate.get("name")
			)
		)
	previous = _previous_closing(doc.distributor, doc.company, start, current)
	received = received_by_item(_invoice_item_lines(doc.distributor, doc.company, start, end))
	try:
		lines, totals = normalize_lines([row.as_dict() for row in (doc.items or [])], previous, received)
	except DistributorError as exc:
		_throw(exc)
	for child, line in zip(doc.items or [], lines, strict=True):
		for key, value in line.items():
			child.set(key, value)
		if doc.currency:
			child.set("currency", doc.currency)
	for key, value in totals.items():
		doc.set(key, value)
	_apply_profile_defaults(doc, profile)


def prepare_complaint(doc):
	if not doc.complaint_date:
		doc.complaint_date = frappe.utils.today()
	if not doc.status:
		doc.status = "Open"
	for row in list(doc.attachments or []):
		if not row.attachment and not clean_text(row.caption):
			doc.remove(row)
	profile = _assert_can_file(doc)
	_apply_profile_defaults(doc, profile)
	if profile and not doc.assigned_to:
		doc.assigned_to = profile.get("account_manager")
	credit = None
	if doc.credit_note and frappe.db.table_exists("Sales Invoice"):
		credit = frappe.db.get_value(
			"Sales Invoice", doc.credit_note, ["name", "is_return", "customer"], as_dict=True
		)
	try:
		cleaned = clean_complaint(doc.as_dict(), credit)
	except DistributorError as exc:
		_throw(exc)
	doc.complaint_type = cleaned["complaint_type"]
	doc.status = cleaned["status"]


def _apply_profile_defaults(doc, profile):
	if not profile:
		if not doc.company:
			doc.company = frappe.defaults.get_user_default("company")
		return
	doc.distributor_profile = profile.get("name")
	if not doc.company:
		doc.company = profile.get("company")
	if doc.doctype == "Distributor Visit":
		if not doc.sales_person and profile.get("sales_person"):
			doc.sales_person = profile.get("sales_person")
		if not doc.salesman and profile.get("salesman"):
			doc.salesman = profile.get("salesman")


def _previous_closing(distributor, company, start, current_name):
	if not frappe.db.table_exists("Distributor Stock Statement"):
		return {}
	previous = frappe.db.sql(
		"""
		select name
		from `tabDistributor Stock Statement`
		where distributor = %s and company = %s and from_date < %s
			and (%s is null or name != %s)
		order by from_date desc
		limit 1
		""",
		(distributor, company, start, current_name, current_name),
		as_dict=True,
	)
	if not previous:
		return {}
	rows = frappe.get_all(
		"Distributor Stock Statement Item",
		filters={"parent": previous[0].name},
		fields=["item", "closing_qty"],
		limit_page_length=500,
		ignore_permissions=True,
	)
	return {row.item: row.closing_qty for row in rows if row.item}


def _previous_statement_rows(distributor, company, start):
	if not frappe.db.table_exists("Distributor Stock Statement"):
		return []
	previous = frappe.db.sql(
		"""
		select name
		from `tabDistributor Stock Statement`
		where distributor = %s and company = %s and from_date < %s
		order by from_date desc
		limit 1
		""",
		(distributor, company, start),
		as_dict=True,
	)
	if not previous:
		return []
	return frappe.get_all(
		"Distributor Stock Statement Item",
		filters={"parent": previous[0].name},
		fields=["item", "item_name", "uom", "closing_qty", "rate"],
		limit_page_length=500,
		ignore_permissions=True,
	)


def _column(columns, *names, fallback="null"):
	for name in names:
		if name in columns:
			return f"`{name}`"
	return fallback


def _invoice_headers(customer, company, start, end):
	if not frappe.db.table_exists("Sales Invoice"):
		return []
	columns = set(frappe.db.get_table_columns("Sales Invoice") or [])
	if "posting_date" not in columns or "customer" not in columns:
		return []
	amount = _column(columns, "base_net_total", "net_total", "base_grand_total", fallback=None)
	if not amount:
		return []
	outstanding = _column(columns, "outstanding_amount", fallback="0")
	due = _column(columns, "due_date")
	is_return = _column(columns, "is_return", fallback="0")
	company_field = "company" if "company" in columns else "null"
	company_sql = "and company = %s" if "company" in columns else ""
	params = [customer, start, end]
	if company_sql:
		params.append(company)
	rows = frappe.db.sql(
		f"""
		select name, posting_date, {company_field} as company, {is_return} as is_return, {amount} as amount,
			{outstanding} as outstanding, {due} as due_date
		from `tabSales Invoice`
		where docstatus = 1 and customer = %s and posting_date between %s and %s
			{company_sql}
		order by posting_date desc, name desc
		""",
		tuple(params),
		as_dict=True,
	)
	for row in rows:
		row["is_return"] = as_flag(row.get("is_return"))
	latest = _latest_sale_row(customer, company, columns, amount, is_return)
	if latest and not any(row.name == latest.name for row in rows):
		latest["is_return"] = as_flag(latest.get("is_return"))
		rows.append(latest)
	return rows


def _latest_sale_row(customer, company, columns, amount, is_return):
	company_field = "company" if "company" in columns else "null"
	company_sql = "and company = %s" if "company" in columns else ""
	params = [customer]
	if company_sql:
		params.append(company)
	rows = frappe.db.sql(
		f"""
		select name, posting_date, {company_field} as company, {is_return} as is_return, {amount} as amount,
			0 as outstanding, null as due_date
		from `tabSales Invoice`
		where docstatus = 1 and customer = %s and ifnull({is_return}, 0) = 0
			{company_sql}
		order by posting_date desc, name desc
		limit 1
		""",
		tuple(params),
		as_dict=True,
	)
	return rows[0] if rows else None


def _invoice_totals(customer, company, today):
	if not frappe.db.table_exists("Sales Invoice"):
		return 0, 0
	columns = set(frappe.db.get_table_columns("Sales Invoice") or [])
	if "outstanding_amount" not in columns or "customer" not in columns:
		return 0, 0
	company_sql = "and company = %s" if "company" in columns else ""
	params = [customer]
	if company_sql:
		params.append(company)
	outstanding = frappe.db.sql(
		f"""
		select coalesce(sum(outstanding_amount), 0)
		from `tabSales Invoice`
		where docstatus = 1 and customer = %s {company_sql}
		""",
		tuple(params),
	)[0][0]
	overdue = 0
	if "due_date" in columns:
		overdue_params = [customer, today]
		if company_sql:
			overdue_params.append(company)
		overdue = frappe.db.sql(
			f"""
			select coalesce(sum(outstanding_amount), 0)
			from `tabSales Invoice`
			where docstatus = 1 and customer = %s and outstanding_amount > 0 and due_date < %s
				{company_sql}
			""",
			tuple(overdue_params),
		)[0][0]
	return outstanding, overdue


def _invoice_item_lines(customer, company, start, end):
	if not frappe.db.table_exists("Sales Invoice") or not frappe.db.table_exists("Sales Invoice Item"):
		return []
	item = set(frappe.db.get_table_columns("Sales Invoice Item") or [])
	invoice = set(frappe.db.get_table_columns("Sales Invoice") or [])
	if "item_code" not in item or "posting_date" not in invoice or "customer" not in invoice:
		return []
	amount = _column(item, "base_net_amount", "net_amount", fallback=None)
	if not amount:
		return []
	is_return = _column(invoice, "is_return", fallback="0")
	company_sql = "and si.company = %s" if "company" in invoice else ""
	params = [customer, start, end]
	if company_sql:
		params.append(company)
	rows = frappe.db.sql(
		f"""
		select sii.item_code as item, {_column(item, "item_name")} as item_name,
			si.posting_date as posting_date, si.company as company,
			{is_return} as is_return, {amount} as amount,
			{_column(item, "qty")} as qty, {_column(item, "stock_qty")} as stock_qty,
			{_column(item, "uom")} as uom, {_column(item, "stock_uom")} as stock_uom
		from `tabSales Invoice` si
		inner join `tabSales Invoice Item` sii on sii.parent = si.name
		where si.docstatus = 1 and si.customer = %s and si.posting_date between %s and %s
			{company_sql}
		""",
		tuple(params),
		as_dict=True,
	)
	for row in rows:
		row["is_return"] = as_flag(row.get("is_return"))
	return rows


def _payments(customer, company):
	if not frappe.db.table_exists("Payment Entry"):
		return []
	columns = set(frappe.db.get_table_columns("Payment Entry") or [])
	if "party" not in columns or "posting_date" not in columns:
		return []
	amount = _column(columns, "base_paid_amount", "paid_amount", fallback=None)
	if not amount:
		return []
	company_field = "company" if "company" in columns else "null"
	company_sql = "and company = %s" if "company" in columns else ""
	party_type = "and party_type = 'Customer'" if "party_type" in columns else ""
	status = _column(columns, "status", fallback="''")
	docstatus = "docstatus" if "docstatus" in columns else "1"
	params = [customer]
	if company_sql:
		params.append(company)
	return frappe.db.sql(
		f"""
		select name, posting_date, {company_field} as company, {amount} as amount,
			{status} as status, {docstatus} as docstatus
		from `tabPayment Entry`
		where {docstatus} < 2 and party = %s {party_type} {company_sql}
		order by posting_date desc, name desc
		limit 24
		""",
		tuple(params),
		as_dict=True,
	)


def _quotations(customer, company):
	if not frappe.db.table_exists("Quotation"):
		return []
	columns = set(frappe.db.get_table_columns("Quotation") or [])
	if "transaction_date" not in columns:
		return []
	if "party_name" in columns and "quotation_to" in columns:
		party_sql = "quotation_to = 'Customer' and party_name = %s"
	elif "customer" in columns:
		party_sql = "customer = %s"
	else:
		return []
	return _selling_rows("Quotation", customer, company, "transaction_date", party_sql, columns)


def _sales_orders(customer, company):
	if not frappe.db.table_exists("Sales Order"):
		return []
	columns = set(frappe.db.get_table_columns("Sales Order") or [])
	if "customer" not in columns or "transaction_date" not in columns:
		return []
	return _selling_rows("Sales Order", customer, company, "transaction_date", "customer = %s", columns)


def _draft_invoices(customer, company):
	"""Unsubmitted invoices. They are listed and are not part of primary billing."""
	if not frappe.db.table_exists("Sales Invoice"):
		return []
	columns = set(frappe.db.get_table_columns("Sales Invoice") or [])
	if "customer" not in columns or "posting_date" not in columns or "docstatus" not in columns:
		return []
	is_return = "and ifnull(is_return, 0) = 0" if "is_return" in columns else ""
	rows = _selling_rows(
		"Sales Invoice",
		customer,
		company,
		"posting_date",
		f"customer = %s and docstatus = 0 {is_return}",
		columns,
		limit=20,
	)
	for row in rows:
		row["docstatus"] = 0
		row["is_return"] = 0
		row["posting_date"] = row.get("transaction_date")
	return rows


def _selling_rows(doctype, customer, company, date_field, party_sql, columns, limit=30):
	amount = _column(columns, "base_net_total", "net_total", "base_grand_total", "grand_total", fallback=None)
	if not amount:
		return []
	company_field = "company" if "company" in columns else "null"
	company_sql = "and company = %s" if "company" in columns else ""
	status = _column(columns, "status", fallback="''")
	docstatus = "docstatus" if "docstatus" in columns else "0"
	params = [customer]
	if company_sql:
		params.append(company)
	# party_sql is built only from column names in this module, never from the request.
	return frappe.db.sql(
		f"""
		select name, `{date_field}` as transaction_date, {company_field} as company,
			{status} as status, {docstatus} as docstatus, {amount} as amount
		from `tab{doctype}`
		where {docstatus} < 2 and {party_sql} {company_sql}
		order by `{date_field}` desc, name desc
		limit {int(limit)}
		""",
		tuple(params),
		as_dict=True,
	)


def _open_complaint_count(customer, company):
	if not frappe.db.table_exists("Distributor Complaint"):
		return 0
	return frappe.db.sql(
		"""
		select count(*)
		from `tabDistributor Complaint`
		where distributor = %s and status in ('Open', 'In Progress')
			and (company = %s or ifnull(company, '') = '')
		""",
		(customer, company),
	)[0][0]


def fetch_bundle(customer, company, profile):
	today = getdate(frappe.utils.today())
	start = statement_period(today)[0]
	# Twelve calendar months, including this one.
	window_start = add_months(start, -11)
	window_end = statement_period(today)[1]
	outstanding, overdue = _invoice_totals(customer, company, today)
	customer_name = ""
	if frappe.db.table_exists("Customer"):
		customer_name = frappe.db.get_value("Customer", customer, "customer_name") or ""
	visits = []
	if frappe.db.table_exists("Distributor Visit"):
		visits = frappe.get_all(
			"Distributor Visit",
			filters={"distributor": customer},
			fields=["name", "visit_date", "salesman", "sales_person", "company", "order_amount", "counters_visited"],
			order_by="visit_date desc",
			limit_page_length=12,
			ignore_permissions=True,
		)
	statements = []
	if frappe.db.table_exists("Distributor Stock Statement"):
		statements = frappe.get_all(
			"Distributor Stock Statement",
			filters={"distributor": customer, "company": company},
			fields=[
				"name",
				"from_date",
				"to_date",
				"company",
				"total_secondary_qty",
				"total_secondary_value",
				"total_closing_qty",
				"total_closing_value",
			],
			order_by="from_date desc",
			limit_page_length=18,
			ignore_permissions=True,
		)
	complaints = []
	if frappe.db.table_exists("Distributor Complaint"):
		complaints = frappe.get_all(
			"Distributor Complaint",
			filters={"distributor": customer},
			fields=["name", "complaint_date", "complaint_type", "status", "item", "company", "assigned_to"],
			order_by="complaint_date desc",
			limit_page_length=12,
			ignore_permissions=True,
		)
	return {
		"customer": customer,
		"customer_name": customer_name or (profile or {}).get("customer_name") or customer,
		"company": company,
		"currency": company_currency(company),
		"profile": profile,
		"invoices": _invoice_headers(customer, company, window_start, window_end),
		"draft_invoices": _draft_invoices(customer, company),
		"lines": _invoice_item_lines(customer, company, window_start, window_end),
		"payments": _payments(customer, company),
		"quotations": _quotations(customer, company),
		"sales_orders": _sales_orders(customer, company),
		"statements": statements,
		"visits": visits,
		"complaints": complaints,
		"outstanding": outstanding,
		"overdue_amount": overdue,
		"open_complaints": _open_complaint_count(customer, company),
	}


@frappe.whitelist()
def profile_defaults(customer):
	require_signed_in()
	row = _profile_row(clean_text(customer))
	if not row:
		return {}
	viewer = _viewer()
	if not can_see_profile(viewer, row):
		frappe.throw(_("This distributor is not assigned to you."), frappe.PermissionError)
	return {
		"distributor_profile": row.name,
		"company": row.company,
		"account_manager": row.account_manager,
		"sales_person": row.sales_person,
		"salesman": row.salesman,
		"territory": row.territory,
		"area": row.area,
		"counters": row.counters,
		"visit_frequency": row.visit_frequency,
	}


@frappe.whitelist()
def dashboard(customer, company=None, growth_pct=None):
	require_signed_in()
	customer = clean_text(customer)
	if not customer:
		frappe.throw(_("Pick a distributor."))
	profile = _profile_row(customer)
	viewer = _viewer()
	if not is_manager(viewer) and not can_see_profile(viewer, profile):
		frappe.throw(_("This distributor is not assigned to you."), frappe.PermissionError)
	company = clean_text(company) or (profile or {}).get("company") or frappe.defaults.get_user_default("company")
	if not company:
		frappe.throw(_("Pick a company."))
	try:
		bundle = fetch_bundle(customer, company, profile)
		bundle["current_target"] = _current_month_target(customer, company)
		return build_dashboard(bundle, getdate(frappe.utils.today()), growth_pct, _target_settings())
	except DistributorError as exc:
		_throw(exc)


def _current_month_target(customer, company, start=None):
	"""Whole-customer primary target for this month, if a Sales Manager has set one."""
	if not frappe.db.table_exists("Customer Primary Target"):
		return None
	start = start or statement_period(getdate(frappe.utils.today()))[0]
	fields = ["name", "target_amount", "item_group", "brand"]
	fields.extend(_target_audit_fields())
	rows = frappe.get_all(
		"Customer Primary Target",
		filters={
			"customer": customer,
			"company": company,
			"period_type": "Monthly",
			"from_date": start,
		},
		fields=fields,
		limit_page_length=20,
		ignore_permissions=True,
	)
	whole = [row for row in rows if not row.item_group and not row.brand]
	chosen = (whole or rows)[:1]
	if not chosen:
		return None
	row = chosen[0]
	return {
		"name": row.name,
		"target_amount": row.target_amount,
		"target_source": row.get("target_source"),
		"recommended_amount": row.get("recommended_amount"),
		"set_by": row.get("set_by"),
		"set_on": row.get("set_on"),
	}


@frappe.whitelist()
def create_next_target(customer, company=None, growth_pct=None):
	"""Create or update next month's whole-customer primary target from the 360 suggestion."""
	require_editor()
	built = dashboard(customer, company, growth_pct)
	suggestion = built["suggestion"]
	amount = suggestion["amount"]
	if not amount or float(amount) <= 0:
		frappe.throw(_("There is no primary billing in the last three months to base a target on."))
	start = suggestion["from_date"]
	if isinstance(start, str):
		start = getdate(start)
	profile = _profile_row(built["customer"]) or {}
	existing = []
	if frappe.db.table_exists("Customer Primary Target"):
		existing = frappe.get_all(
			"Customer Primary Target",
			filters={
				"customer": built["customer"],
				"company": built["company"],
				"period_type": "Monthly",
				"from_date": start,
			},
			fields=["name", "item_group", "brand"],
			limit_page_length=20,
		)
	match = next((row for row in existing if not row.item_group and not row.brand), None)
	if match:
		doc = frappe.get_doc("Customer Primary Target", match.name)
		doc.target_amount = amount
		doc.save()
		created = False
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Customer Primary Target",
				"customer": built["customer"],
				"company": built["company"],
				"period_type": "Monthly",
				"target_month": start,
				"target_amount": amount,
				"sales_person": profile.get("sales_person"),
				"sales_user": profile.get("salesman") or profile.get("account_manager"),
			}
		)
		doc.insert()
		created = True
	return {
		"name": doc.name,
		"target_amount": doc.target_amount,
		"from_date": doc.from_date,
		"to_date": doc.to_date,
		"created": created,
		"period_label": suggestion["period_label"],
	}


def _require_360() -> str:
	user = require_signed_in()
	if not can_open_distributor_360(user, frappe.get_roles(user)):
		frappe.throw(_("You cannot open Distributor 360."), frappe.PermissionError)
	return user


def _target_settings() -> dict:
	"""Growth factor and the default for a distributor with no recent billing."""
	growth = GROWTH_FACTOR_DEFAULT
	default_amount = DEFAULT_TARGET_AMOUNT
	if not frappe.db.table_exists("Distributor Settings"):
		return {"growth_factor": growth, "default_amount": default_amount}
	stored_growth = frappe.db.get_single_value("Distributor Settings", "growth_factor")
	stored_default = frappe.db.get_single_value("Distributor Settings", "default_target")
	try:
		if stored_growth not in (None, ""):
			growth = clean_growth_factor(stored_growth)
	except DistributorError:
		growth = GROWTH_FACTOR_DEFAULT
	try:
		if stored_default not in (None, ""):
			default_amount = float(stored_default)
	except (TypeError, ValueError):
		default_amount = DEFAULT_TARGET_AMOUNT
	return {"growth_factor": growth, "default_amount": default_amount}


def _target_audit_fields() -> list:
	if not frappe.db.table_exists("Customer Primary Target"):
		return []
	columns = set(frappe.db.get_table_columns("Customer Primary Target") or [])
	return [
		name
		for name in ("target_source", "recommended_amount", "set_by", "set_on", "recommendation_basis", "remarks")
		if name in columns
	]


def _visible_profiles(company):
	if not frappe.db.table_exists("Distributor Profile"):
		return []
	filters = {"company": company} if company else {}
	return frappe.get_list(
		"Distributor Profile",
		filters=filters,
		fields=list(PROFILE_FIELDS),
		limit_page_length=5000,
	)


@frappe.whitelist()
def distributor_mis(company=None, activity=None, search=None, territory=None, account_manager=None, sales_person=None, rag=None):
	"""Book of distributors the user may see. Totals come from grouped queries, not one query per row."""
	_require_360()
	company = clean_text(company) or frappe.defaults.get_user_default("company")
	if not company:
		frappe.throw(_("Pick a company."))
	today = getdate(frappe.utils.today())
	profiles = _visible_profiles(company)
	months = trailing_months(today, 6)
	metrics = _mis_metrics(profiles, company, today, months)
	try:
		return build_distributor_mis(
			profiles,
			metrics,
			{
				"activity": activity,
				"search": search,
				"territory": territory,
				"account_manager": account_manager,
				"sales_person": sales_person,
				"rag": rag,
			},
			today,
			months,
			_target_settings(),
		) | {"company": company, "currency": company_currency(company)}
	except DistributorError as exc:
		_throw(exc)


@frappe.whitelist()
def set_distributor_target(customer, company=None, source=None, amount=None, target_month=None, note=None):
	"""Create or update one month's whole-customer target. Older months are left in place."""
	require_editor()
	user = _require_360()
	customer = clean_text(customer)
	if not customer:
		frappe.throw(_("Pick a distributor."))
	profile = _profile_row(customer)
	viewer = _viewer()
	if profile and not can_see_profile(viewer, profile):
		frappe.throw(_("This distributor is not assigned to you."), frappe.PermissionError)
	if not profile and not is_manager(viewer):
		frappe.throw(_("This distributor is not assigned to you."), frappe.PermissionError)
	company = clean_text(company) or (profile or {}).get("company") or frappe.defaults.get_user_default("company")
	if not company:
		frappe.throw(_("Pick a company."))
	today = getdate(frappe.utils.today())
	months = trailing_months(today, 6)
	metrics = _mis_metrics([{"customer": customer}], company, today, months)
	facts = metrics.get(customer) or {}
	keys = [(day.year, day.month) for day in months]
	spark = [facts.get("months", {}).get(key, 0) for key in keys]
	settings = _target_settings()
	recommendation = recommended_monthly_target(spark, settings["growth_factor"], settings["default_amount"])
	try:
		planned = plan_target_save(source, amount, recommendation["amount"], note)
		start, _end = statement_period(target_month or today)
	except (DistributorError, TargetError) as exc:
		_throw(exc)
	saved = _save_primary_target(customer, company, start, planned, profile or {}, recommendation, user)
	saved["currency"] = company_currency(company)
	saved["recommendation_basis"] = recommendation["basis"]
	return saved


@frappe.whitelist()
def apply_recommended_targets(customers=None, company=None, target_month=None):
	"""Set this month's target to the recommended amount for each selected distributor."""
	require_editor()
	user = _require_360()
	if isinstance(customers, str):
		try:
			customers = json.loads(customers)
		except ValueError:
			customers = [customers]
	names = []
	for name in customers or []:
		cleaned = clean_text(name)
		if cleaned and cleaned not in names:
			names.append(cleaned)
	if not names:
		frappe.throw(_("Select at least one distributor."))
	if len(names) > 500:
		frappe.throw(_("Select up to 500 distributors at a time."))
	company = clean_text(company) or frappe.defaults.get_user_default("company")
	if not company:
		frappe.throw(_("Pick a company."))
	viewer = _viewer()
	profiles = _visible_profiles(company)
	by_customer = {row.customer: row for row in profiles if row.get("customer")}
	today = getdate(frappe.utils.today())
	try:
		start, _end = statement_period(target_month or today)
	except (DistributorError, TargetError) as exc:
		_throw(exc)
	months = trailing_months(today, 6)
	allowed = []
	skipped = []
	for name in names:
		profile = by_customer.get(name)
		if not profile or not can_see_profile(viewer, profile):
			skipped.append({"customer": name, "reason": "This distributor is not assigned to you."})
			continue
		allowed.append(profile)
	metrics = _mis_metrics(allowed, company, today, months)
	settings = _target_settings()
	keys = [(day.year, day.month) for day in months]
	applied = []
	for profile in allowed:
		customer = profile.customer
		facts = metrics.get(customer) or {}
		spark = [facts.get("months", {}).get(key, 0) for key in keys]
		recommendation = recommended_monthly_target(spark, settings["growth_factor"], settings["default_amount"])
		try:
			planned = plan_target_save("Recommended", None, recommendation["amount"], None)
		except DistributorError as exc:
			skipped.append({"customer": customer, "reason": str(exc)})
			continue
		saved = _save_primary_target(customer, company, start, planned, profile, recommendation, user)
		applied.append(
			{"customer": customer, "name": saved["name"], "target_amount": saved["target_amount"]}
		)
	return {"applied": applied, "skipped": skipped, "currency": company_currency(company)}


def _save_primary_target(customer, company, start, planned, profile, recommendation, user) -> dict:
	"""Update the whole-customer target for this month, or insert one. Other months stay."""
	if not frappe.db.table_exists("Customer Primary Target"):
		frappe.throw(_("Customer Primary Target is not installed on this site."))
	existing = frappe.get_all(
		"Customer Primary Target",
		filters={
			"customer": customer,
			"company": company,
			"period_type": "Monthly",
			"from_date": start,
		},
		fields=["name", "item_group", "brand"],
		limit_page_length=20,
	)
	match = next((row for row in existing if not row.item_group and not row.brand), None)
	audit = set(_target_audit_fields())
	values = {"target_amount": planned["target_amount"]}
	if "target_source" in audit:
		values["target_source"] = planned["source"]
	if "recommended_amount" in audit:
		values["recommended_amount"] = planned["recommended_amount"]
	if "set_by" in audit:
		values["set_by"] = user
	if "set_on" in audit:
		values["set_on"] = frappe.utils.now_datetime()
	if "recommendation_basis" in audit:
		values["recommendation_basis"] = recommendation.get("basis")
	if "remarks" in audit and planned.get("note") is not None:
		values["remarks"] = planned["note"]
	if match:
		doc = frappe.get_doc("Customer Primary Target", match.name)
		for key, value in values.items():
			doc.set(key, value)
		doc.save()
		created = False
	else:
		payload = {
			"doctype": "Customer Primary Target",
			"customer": customer,
			"company": company,
			"period_type": "Monthly",
			"target_month": start,
			"sales_person": (profile or {}).get("sales_person"),
			"sales_user": (profile or {}).get("salesman") or (profile or {}).get("account_manager"),
		}
		payload.update(values)
		doc = frappe.get_doc(payload)
		doc.insert()
		created = True
	return {
		"name": doc.name,
		"target_amount": doc.target_amount,
		"target_source": planned["source"],
		"recommended_amount": planned["recommended_amount"],
		"from_date": doc.from_date,
		"to_date": doc.to_date,
		"created": created,
		"period_label": month_label(start),
	}


def _signed_amount_sql(amount_expr, is_return_expr) -> str:
	"""Submitted net total. A credit note subtracts. The expressions are column names from this module."""
	return (
		f"case when ifnull({is_return_expr}, 0) = 1 then -abs(ifnull({amount_expr}, 0)) "
		f"else ifnull({amount_expr}, 0) end"
	)


def _mis_metrics(profiles, company, today, months) -> dict:
	"""Grouped facts for the book. One query per measure, chunked, never one query per distributor."""
	customers = []
	for profile in profiles or []:
		customer = clean_text(profile.get("customer") if isinstance(profile, dict) else getattr(profile, "customer", None))
		if customer and customer not in customers:
			customers.append(customer)
	metrics = {customer: {"months": {}} for customer in customers}
	if not customers:
		return metrics
	start = months[0]
	end = statement_period(months[-1])[1]
	month_start = statement_period(today)[0]
	_fill_disabled(metrics, customers)
	_fill_invoice_metrics(metrics, customers, company, today, start, end, month_start)
	_fill_target_metrics(metrics, customers, company, month_start)
	_fill_quotation_metrics(metrics, customers, company)
	_fill_collection_metrics(metrics, customers, company, month_start, statement_period(today)[1])
	_fill_visit_metrics(metrics, customers, company, month_start, statement_period(today)[1])
	return metrics


def _fill_disabled(metrics, customers):
	if not frappe.db.table_exists("Customer"):
		return
	columns = set(frappe.db.get_table_columns("Customer") or [])
	if "disabled" not in columns:
		return
	for chunk in _chunks(customers, 300):
		for row in frappe.get_all(
			"Customer",
			filters={"name": ["in", chunk]},
			fields=["name", "disabled"],
			limit_page_length=500,
			ignore_permissions=True,
		):
			metrics[row.name]["disabled"] = row.disabled


def _fill_invoice_metrics(metrics, customers, company, today, start, end, month_start):
	"""Submitted invoices only. Drafts stay out of primary, the sparkline, and the last bill."""
	if not frappe.db.table_exists("Sales Invoice"):
		return
	columns = set(frappe.db.get_table_columns("Sales Invoice") or [])
	if "customer" not in columns or "posting_date" not in columns or "docstatus" not in columns:
		return
	amount = _column(columns, "base_net_total", "net_total", "base_grand_total", fallback=None)
	if not amount:
		return
	is_return = _column(columns, "is_return", fallback="0")
	signed = _signed_amount_sql(amount, is_return)
	company_sql = "and company = %s" if "company" in columns else ""
	outstanding = _column(columns, "outstanding_amount", fallback="0")
	due = _column(columns, "due_date", fallback="null")
	for chunk in _chunks(customers, 300):
		params = [start, end, chunk]
		if company_sql:
			params.append(company)
		for row in frappe.db.sql(
			f"""
			select customer,
				year(posting_date) as year,
				month(posting_date) as month,
				coalesce(sum({signed}), 0) as amount
			from `tabSales Invoice`
			where docstatus = 1 and posting_date between %s and %s and customer in %s
				{company_sql}
			group by customer, year(posting_date), month(posting_date)
			""",
			tuple(params),
			as_dict=True,
		):
			metrics[row.customer]["months"][(int(row.year), int(row.month))] = float(row.amount or 0)
		primary_params = [month_start, end, chunk]
		if company_sql:
			primary_params.append(company)
		for row in frappe.db.sql(
			f"""
			select customer, coalesce(sum({signed}), 0) as amount
			from `tabSales Invoice`
			where docstatus = 1 and posting_date between %s and %s and customer in %s
				{company_sql}
			group by customer
			""",
			tuple(primary_params),
			as_dict=True,
		):
			metrics[row.customer]["primary_mtd"] = float(row.amount or 0)
		if "outstanding_amount" in columns:
			out_params = [today, chunk]
			if company_sql:
				out_params.append(company)
			for row in frappe.db.sql(
				f"""
				select customer,
					coalesce(sum({outstanding}), 0) as outstanding,
					coalesce(sum(case
						when {outstanding} > 0 and {due} < %s then {outstanding}
						else 0
					end), 0) as overdue
				from `tabSales Invoice`
				where docstatus = 1 and customer in %s
					{company_sql}
				group by customer
				""",
				tuple(out_params),
				as_dict=True,
			):
				metrics[row.customer]["outstanding"] = float(row.outstanding or 0)
				metrics[row.customer]["overdue"] = float(row.overdue or 0)
		last_params = [chunk]
		if company_sql:
			last_params.append(company)
		not_return = f"and ifnull({is_return}, 0) = 0" if "is_return" in columns else ""
		for row in frappe.db.sql(
			f"""
			select customer, max(posting_date) as last_billing
			from `tabSales Invoice`
			where docstatus = 1 {not_return} and customer in %s
				{company_sql}
			group by customer
			""",
			tuple(last_params),
			as_dict=True,
		):
			metrics[row.customer]["last_billing"] = row.last_billing


def _fill_target_metrics(metrics, customers, company, month_start):
	if not frappe.db.table_exists("Customer Primary Target"):
		return
	audit = _target_audit_fields()
	extra = ""
	for name in ("target_source", "recommended_amount"):
		if name in audit:
			extra += f", `{name}`"
	for chunk in _chunks(customers, 300):
		for row in frappe.db.sql(
			f"""
			select name, customer, target_amount, item_group, brand {extra}
			from `tabCustomer Primary Target`
			where company = %s and period_type = 'Monthly' and from_date = %s and customer in %s
			""",
			(company, month_start, chunk),
			as_dict=True,
		):
			current = metrics[row.customer]
			whole = not clean_text(row.item_group) and not clean_text(row.brand)
			if current.get("target_name") and not whole:
				continue
			if current.get("target_name") and whole and current.get("_whole_target"):
				continue
			current["target_amount"] = row.target_amount
			current["target_name"] = row.name
			current["target_source"] = row.get("target_source")
			current["_whole_target"] = whole


def _fill_quotation_metrics(metrics, customers, company):
	"""Open quotation value: drafts and submitted Open or Replied. Lost, ordered, and cancelled stay out."""
	if not frappe.db.table_exists("Quotation"):
		return
	columns = set(frappe.db.get_table_columns("Quotation") or [])
	amount = _column(columns, "base_net_total", "net_total", "base_grand_total", fallback=None)
	if not amount or "docstatus" not in columns:
		return
	if "party_name" in columns:
		party = "party_name"
		who = "quotation_to = 'Customer'" if "quotation_to" in columns else "1 = 1"
	elif "customer" in columns:
		party = "customer"
		who = "1 = 1"
	else:
		return
	company_sql = "and company = %s" if "company" in columns else ""
	status_sql = ""
	if "status" in columns:
		status_sql = "and ifnull(status, '') in ('', 'Draft', 'Open', 'Replied')"
	for chunk in _chunks(customers, 300):
		params = [chunk]
		if company_sql:
			params.append(company)
		for row in frappe.db.sql(
			f"""
			select `{party}` as customer, coalesce(sum({amount}), 0) as amount
			from `tabQuotation`
			where docstatus < 2 and {who} {status_sql} and `{party}` in %s
				{company_sql}
			group by `{party}`
			""",
			tuple(params),
			as_dict=True,
		):
			if row.customer in metrics:
				metrics[row.customer]["open_quotations"] = float(row.amount or 0)


def _fill_collection_metrics(metrics, customers, company, month_start, month_end):
	"""Submitted Payment Entries only. Draft receipts are not collections."""
	if not frappe.db.table_exists("Payment Entry"):
		return
	columns = set(frappe.db.get_table_columns("Payment Entry") or [])
	if "party" not in columns or "posting_date" not in columns or "docstatus" not in columns:
		return
	amount = _column(columns, "base_paid_amount", "paid_amount", fallback=None)
	if not amount:
		return
	party_type = "and party_type = 'Customer'" if "party_type" in columns else ""
	company_sql = "and company = %s" if "company" in columns else ""
	for chunk in _chunks(customers, 300):
		params = [month_start, month_end, chunk]
		if company_sql:
			params.append(company)
		for row in frappe.db.sql(
			f"""
			select party as customer, coalesce(sum({amount}), 0) as amount
			from `tabPayment Entry`
			where docstatus = 1 {party_type} and posting_date between %s and %s and party in %s
				{company_sql}
			group by party
			""",
			tuple(params),
			as_dict=True,
		):
			if row.customer in metrics:
				metrics[row.customer]["collections_mtd"] = float(row.amount or 0)


def _fill_visit_metrics(metrics, customers, company, month_start, month_end):
	if not frappe.db.table_exists("Distributor Visit"):
		return
	columns = set(frappe.db.get_table_columns("Distributor Visit") or [])
	if "distributor" not in columns or "visit_date" not in columns:
		return
	company_sql = ""
	if "company" in columns:
		company_sql = "and (ifnull(company, '') = '' or company = %s)"
	for chunk in _chunks(customers, 300):
		params = [month_start, month_end, chunk]
		if company_sql:
			params.append(company)
		for row in frappe.db.sql(
			f"""
			select distributor as customer, count(*) as total
			from `tabDistributor Visit`
			where visit_date between %s and %s and distributor in %s
				{company_sql}
			group by distributor
			""",
			tuple(params),
			as_dict=True,
		):
			if row.customer in metrics:
				metrics[row.customer]["visits_mtd"] = int(row.total or 0)


@frappe.whitelist()
def prefill_statement(distributor, company, statement_month):
	require_signed_in()
	distributor = clean_text(distributor)
	company = clean_text(company)
	if not distributor or not company or not statement_month:
		frappe.throw(_("Pick a distributor, a company, and a month."))
	profile = _profile_row(distributor)
	viewer = _viewer()
	if not can_file(viewer, profile, is_new=True, owner=None, distributor=distributor):
		frappe.throw(_("This distributor is not assigned to you."), frappe.PermissionError)
	try:
		start, end = statement_period(statement_month)
	except (DistributorError, TargetError) as exc:
		_throw(exc)
	rows = prefill_rows(
		_previous_statement_rows(distributor, company, start),
		_invoice_item_lines(distributor, company, start, end),
	)
	return {
		"from_date": start,
		"to_date": end,
		"currency": company_currency(company),
		"items": rows,
		"month_label": month_label(start),
	}


def run_follow_up(filters=None):
	try:
		filters = clean_follow_up_filters(filters or {})
	except DistributorError as exc:
		_throw(exc)
	viewer = _viewer()
	if not frappe.db.table_exists("Distributor Profile"):
		columns = [_label(column) for column in follow_up_columns()]
		return columns, [], _("Nothing needs a follow-up."), None, []
	query_filters = {"company": filters["company"]} if filters["company"] else {}
	profiles = frappe.get_list(
		"Distributor Profile",
		filters=query_filters,
		fields=list(PROFILE_FIELDS),
		limit_page_length=5000,
	)
	facts = _follow_up_facts(profiles)
	built = follow_up_rows(profiles, facts, filters, viewer, getdate(frappe.utils.today()))
	columns = [_label(column) for column in built["columns"]]
	summary = built["summary"]
	for card in summary:
		card["label"] = _(card["label"])
	return columns, built["rows"], _(built["message"]), None, summary


def _label(column):
	column = dict(column)
	column["label"] = _(column["label"])
	return column


def _chunks(values, size):
	values = list(values)
	for index in range(0, len(values), size):
		yield values[index : index + size]


def _follow_up_facts(profiles):
	customers = [row.customer for row in profiles if row.get("customer")]
	customers = list(dict.fromkeys(customers))
	last_orders = {}
	overdue = {}
	complaints = {}
	targets = {}
	today = getdate(frappe.utils.today())
	if customers and frappe.db.table_exists("Sales Invoice"):
		columns = set(frappe.db.get_table_columns("Sales Invoice") or [])
		if "posting_date" in columns and "customer" in columns and "company" in columns:
			is_return = "ifnull(is_return, 0) = 0" if "is_return" in columns else "1 = 1"
			for chunk in _chunks(customers, 300):
				for row in frappe.db.sql(
					f"""
					select customer, company, max(posting_date) as last_order
					from `tabSales Invoice`
					where docstatus = 1 and {is_return} and customer in %s
					group by customer, company
					""",
					(chunk,),
					as_dict=True,
				):
					last_orders[(row.customer, row.company)] = row.last_order
			if "outstanding_amount" in columns and "due_date" in columns:
				for chunk in _chunks(customers, 300):
					for row in frappe.db.sql(
						"""
						select customer, company, coalesce(sum(outstanding_amount), 0) as overdue
						from `tabSales Invoice`
						where docstatus = 1 and outstanding_amount > 0 and due_date < %s
							and customer in %s
						group by customer, company
						""",
						(today, chunk),
						as_dict=True,
					):
						overdue[(row.customer, row.company)] = row.overdue
	if customers and frappe.db.table_exists("Distributor Complaint"):
		for chunk in _chunks(customers, 300):
			for row in frappe.db.sql(
				"""
				select distributor, ifnull(company, '') as company, count(*) as total
				from `tabDistributor Complaint`
				where status in ('Open', 'In Progress') and distributor in %s
				group by distributor, ifnull(company, '')
				""",
				(chunk,),
				as_dict=True,
			):
				complaints[(row.distributor, row.company)] = int(row.total or 0)
	if customers and frappe.db.table_exists("Customer Primary Target"):
		start = statement_period(today)[0]
		for chunk in _chunks(customers, 300):
			for row in frappe.get_all(
				"Customer Primary Target",
				filters={"customer": ["in", chunk], "from_date": start, "period_type": "Monthly"},
				fields=["customer", "company", "from_date", "period_type", "item_group", "brand", "achievement_pct"],
				limit_page_length=5000,
				ignore_permissions=True,
			):
				targets.setdefault(row.customer, []).append(row)
	facts = {}
	for profile in profiles:
		customer = profile.get("customer")
		company = clean_text(profile.get("company"))
		if company:
			open_count = complaints.get((customer, company), 0) + complaints.get((customer, ""), 0)
		else:
			open_count = complaints.get((customer, ""), 0)
		facts[customer] = {
			"last_order_date": last_orders.get((customer, company)),
			"overdue_amount": overdue.get((customer, company), 0),
			"open_complaints": open_count,
			"achievement_pct": achievement_for_month(targets.get(customer) or [], today, company),
		}
	return facts


def ensure_distributor_places():
	"""Put the distributor shortcuts back if a migrate left them off the workspace or the sidebar."""
	_quietly("Distributor shortcuts", _ensure_workspace)
	_quietly("Distributor sidebar", _ensure_sidebar)


def _ensure_workspace():
	"""Append distributor shortcuts. Shortcuts already on Quick Actions are left as they are."""
	if not frappe.db.table_exists("Workspace") or not frappe.db.exists("Workspace", "Quick Actions"):
		return
	doc = frappe.get_doc("Workspace", "Quick Actions")
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
	for link in DISTRIBUTOR_LINKS:
		label = link["label"]
		if label not in labels:
			doc.append("shortcuts", workspace_shortcut(link))
			labels.add(label)
			changed = True
		if isinstance(content, list) and label not in block_names:
			content.append(workspace_block(link))
			block_names.add(label)
			changed = True
		if label not in link_labels:
			if DISTRIBUTOR_CARD not in link_labels:
				doc.append(
					"links",
					{
						"type": "Card Break",
						"label": DISTRIBUTOR_CARD,
						"hidden": 0,
						"is_query_report": 0,
						"link_count": 0,
						"onboard": 0,
					},
				)
				link_labels.add(DISTRIBUTOR_CARD)
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


def _ensure_sidebar():
	if not frappe.db.table_exists("Sidebar") or not frappe.db.exists("Sidebar", "Melliflous Branding"):
		return
	doc = frappe.get_doc("Sidebar", "Melliflous Branding")
	missing = missing_sidebar_links((row.link_type, row.link_to) for row in (doc.items or []))
	if not missing:
		return
	for link in missing:
		doc.append("items", link)
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
