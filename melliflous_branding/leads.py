# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Quick Lead: a CRM Lead when that app is installed, otherwise an ERPNext Lead."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.desk.form.assign_to import _add as assign_to_user
from frappe.utils import strip_html, today

from melliflous_branding.access import require_desk_user
from melliflous_branding.quick import (
	LEAD_SOURCES,
	choose_lead_doctype,
	clean_source,
	is_overdue,
	is_protected_user,
	next_day,
	phone_links,
	split_name,
)
from melliflous_branding.tasks import _require_enabled_user


@frappe.whitelist()
def form_options() -> dict:
	require_desk_user()
	return {
		"people": _people(),
		"sources": list(LEAD_SOURCES),
		"follow_up": next_day(frappe.utils.getdate(today())),
		"lead_doctype": _lead_doctype(),
	}


@frappe.whitelist(methods=["POST"])
def save_lead(
	full_name: str,
	mobile: str,
	shop: str | None = None,
	city: str | None = None,
	source: str | None = None,
	assign_to: str | None = None,
	follow_up: str | None = None,
) -> dict:
	actor = require_desk_user()
	full_name = (full_name or "").strip()
	mobile = (mobile or "").strip()
	shop = (shop or "").strip()
	city = (city or "").strip()
	if not full_name:
		frappe.throw(_("Enter the person's name."))
	if not mobile:
		frappe.throw(_("Enter a mobile number so you can call them."))
	try:
		source = clean_source(source)
	except ValueError as error:
		frappe.throw(_(str(error)))

	assignee = (assign_to or "").strip() or actor
	if is_protected_user(assignee):
		frappe.throw(_("Choose a person to follow up."))
	_require_enabled_user(assignee)
	due = (follow_up or "").strip() or next_day(frappe.utils.getdate(today()))

	doctype = _lead_doctype()
	if not frappe.has_permission(doctype, "create"):
		frappe.throw(_("You are not allowed to add a lead."), frappe.PermissionError)

	lead = _make_lead(doctype, full_name, mobile, shop, city, source, assignee)
	description = _follow_up_text(full_name, shop, city, mobile)
	assign_to_user(
		{
			"assign_to": [assignee],
			"doctype": lead.doctype,
			"name": lead.name,
			"description": description,
			"priority": "Medium",
			"date": due,
			"assigned_by": actor,
		},
		ignore_permissions=False,
	)
	return {
		"message": _("Lead saved. Follow-up set for {0}.").format(due),
		"lead": lead.name,
		"lead_doctype": lead.doctype,
	}


@frappe.whitelist()
def my_follow_ups() -> dict:
	user = require_desk_user()
	rows = frappe.get_all(
		"ToDo",
		filters={
			"status": "Open",
			"allocated_to": user,
			"reference_type": ["in", ["CRM Lead", "Lead"]],
			"date": ["<=", today()],
		},
		fields=["name", "description", "date", "reference_type", "reference_name"],
		order_by="date asc",
		limit=200,
	)
	today_text = today()
	follow_ups = []
	for row in rows:
		lead = _lead_summary(row.reference_type, row.reference_name)
		due = str(row.date) if row.date else ""
		links = phone_links(lead.get("mobile"))
		follow_ups.append(
			{
				"name": row.name,
				"title": lead.get("title") or strip_html(row.description or "").split("\n")[0],
				"shop": lead.get("shop") or "",
				"city": lead.get("city") or "",
				"mobile": lead.get("mobile") or "",
				"tel": links["tel"],
				"whatsapp": links["whatsapp"],
				"date": due,
				"overdue": is_overdue(due, today_text),
				"description": strip_html(row.description or "").strip(),
			}
		)
	return {"follow_ups": follow_ups, "today": today_text}


def _lead_doctype() -> str:
	available = set()
	for name in ("CRM Lead", "Lead"):
		if frappe.db.exists("DocType", name):
			available.add(name)
	chosen = choose_lead_doctype(available)
	if not chosen:
		frappe.throw(_("Leads are not installed on this site."))
	return chosen


def _make_lead(doctype, full_name, mobile, shop, city, source, assignee):
	first_name, last_name = split_name(full_name)
	lead = frappe.new_doc(doctype)
	_set(lead, "first_name", first_name)
	_set(lead, "last_name", last_name)
	_set(lead, "lead_name", full_name)
	_set(lead, "mobile_no", mobile)
	_set(lead, "phone", mobile)
	if doctype == "CRM Lead":
		_set(lead, "organization", shop)
		_set(lead, "lead_owner", assignee)
		_set(lead, "source", _ensure_source("CRM Lead Source", "source_name", source))
		status = _crm_status()
		if status:
			_set(lead, "status", status)
		if city and not lead.meta.has_field("city"):
			_set(lead, "company_description", _("City: {0}").format(city))
	else:
		_set(lead, "company_name", shop)
		_set(lead, "source", _ensure_source("Lead Source", "source_name", source))
		if lead.meta.has_field("status"):
			options = (lead.meta.get_field("status").options or "").split("\n")
			if "Lead" in options:
				lead.status = "Lead"
	if city and lead.meta.has_field("city"):
		lead.city = city
	status_field = lead.meta.get_field("status")
	if status_field and status_field.reqd and not lead.get("status"):
		frappe.throw(_("Add a lead status called New Lead, then try again."))
	lead.insert()
	return lead


def _set(doc, fieldname: str, value: str) -> None:
	if value and doc.meta.has_field(fieldname):
		doc.set(fieldname, value)


def _ensure_source(doctype: str, fieldname: str, value: str) -> str:
	if not frappe.db.exists("DocType", doctype):
		return value
	if frappe.db.exists(doctype, value):
		return value
	doc = frappe.new_doc(doctype)
	if doc.meta.has_field(fieldname):
		doc.set(fieldname, value)
	else:
		doc.name = value
	doc.insert(ignore_permissions=True)
	return doc.name


def _crm_status() -> str:
	if not frappe.db.exists("DocType", "CRM Lead Status"):
		return ""
	if frappe.db.exists("CRM Lead Status", "New Lead"):
		return "New Lead"
	names = frappe.get_all("CRM Lead Status", pluck="name", limit=1)
	return names[0] if names else ""


def _follow_up_text(full_name, shop, city, mobile) -> str:
	lines = [_("Follow up with {0}").format(full_name)]
	if shop:
		lines.append(_("Shop: {0}").format(shop))
	if city:
		lines.append(_("City: {0}").format(city))
	if mobile:
		lines.append(_("Mobile: {0}").format(mobile))
	return "\n".join(lines)


def _lead_summary(doctype: str, name: str) -> dict:
	if not doctype or not name or not frappe.db.exists(doctype, name):
		return {}
	fields = ["name"]
	meta = frappe.get_meta(doctype)
	for field in (
		"lead_name",
		"first_name",
		"mobile_no",
		"organization",
		"company_name",
		"city",
		"company_description",
	):
		if meta.has_field(field):
			fields.append(field)
	row = frappe.db.get_value(doctype, name, fields, as_dict=True) or {}
	title = row.get("lead_name") or row.get("first_name") or name
	shop = row.get("organization") or row.get("company_name") or ""
	city = row.get("city") or ""
	if not city:
		note = row.get("company_description") or ""
		if note.startswith("City: "):
			city = note.split("City: ", 1)[1].strip()
	return {"title": title, "shop": shop, "city": city, "mobile": row.get("mobile_no") or ""}


def _people() -> list[dict]:
	rows = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User", "name": ["not in", ["Guest", "Administrator"]]},
		fields=["name", "full_name"],
		order_by="full_name asc",
		limit=0,
	)
	return [
		{"email": row.name, "full_name": row.full_name or row.name}
		for row in rows
		if not is_protected_user(row.name)
	]
