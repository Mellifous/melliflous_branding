# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Give a task, list open tasks, and mark a ToDo done."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.desk.form.assign_to import _add as assign_to_user
from frappe.utils import strip_html, today

from melliflous_branding.access import is_system_manager, require_desk_user
from melliflous_branding.quick import (
	LINKABLE_DOCTYPES,
	clean_priority,
	is_overdue,
	is_protected_user,
	next_day,
)


@frappe.whitelist()
def form_options() -> dict:
	require_desk_user()
	return {
		"people": _people(),
		"companies": frappe.get_all("Company", pluck="name", order_by="name asc", limit=0),
		"link_types": [name for name in LINKABLE_DOCTYPES if frappe.db.exists("DocType", name)],
		"due_date": next_day(frappe.utils.getdate(today())),
		"priorities": ["Low", "Medium", "High"],
	}


@frappe.whitelist(methods=["POST"])
def give_task(
	person: str,
	description: str,
	due_date: str | None = None,
	priority: str | None = None,
	company: str | None = None,
	reference_type: str | None = None,
	reference_name: str | None = None,
) -> dict:
	actor = require_desk_user()
	if not frappe.has_permission("ToDo", "create"):
		frappe.throw(_("You are not allowed to give tasks."), frappe.PermissionError)

	person = (person or "").strip()
	description = strip_html(description or "").strip()
	company = (company or "").strip()
	if not person or is_protected_user(person):
		frappe.throw(_("Choose a person."))
	if not description:
		frappe.throw(_("Write what they need to do."))
	_require_enabled_user(person)

	try:
		priority = clean_priority(priority)
	except ValueError as error:
		frappe.throw(_(str(error)))

	due = (due_date or "").strip() or next_day(frappe.utils.getdate(today()))
	if company and not frappe.db.exists("Company", company):
		frappe.throw(_("That company was not found."))
	if company:
		description = f"{description}\nCompany: {company}"

	reference_type, reference_name = _clean_reference(reference_type, reference_name)
	if reference_type:
		assign_to_user(
			{
				"assign_to": [person],
				"doctype": reference_type,
				"name": reference_name,
				"description": description,
				"priority": priority,
				"date": due,
				"assigned_by": actor,
			},
			ignore_permissions=False,
		)
	else:
		frappe.get_doc(
			{
				"doctype": "ToDo",
				"allocated_to": person,
				"assigned_by": actor,
				"description": description,
				"date": due,
				"priority": priority,
				"status": "Open",
			}
		).insert(ignore_permissions=True)

	who = frappe.db.get_value("User", person, "full_name") or person
	return {"message": _("Task given to {0}.").format(who)}


@frappe.whitelist()
def list_tasks(mine: int | str = 0) -> dict:
	user = require_desk_user()
	mine = frappe.utils.cint(mine)
	filters: dict = {"status": "Open"}
	if mine or not is_system_manager():
		if mine:
			filters["allocated_to"] = user
		else:
			filters["assigned_by"] = user
	rows = frappe.get_all(
		"ToDo",
		filters=filters,
		fields=[
			"name",
			"description",
			"date",
			"priority",
			"allocated_to",
			"assigned_by",
			"reference_type",
			"reference_name",
		],
		order_by="date asc",
		limit=200,
	)
	names = {row.allocated_to for row in rows if row.allocated_to}
	full_names = {}
	if names:
		for person in frappe.get_all(
			"User",
			filters={"name": ["in", list(names)]},
			fields=["name", "full_name"],
			limit=0,
		):
			full_names[person.name] = person.full_name or person.name

	today_text = today()
	grouped: dict[str, dict] = {}
	for row in rows:
		person = row.allocated_to or ""
		bucket = grouped.setdefault(
			person,
			{
				"user": person,
				"person": full_names.get(person) or person or _("Unassigned"),
				"tasks": [],
			},
		)
		due = str(row.date) if row.date else ""
		bucket["tasks"].append(
			{
				"name": row.name,
				"description": strip_html(row.description or "").strip(),
				"date": due,
				"priority": row.priority or "Medium",
				"overdue": is_overdue(due, today_text),
				"reference_type": row.reference_type or "",
				"reference_name": row.reference_name or "",
				"can_close": _can_close(row, user),
			}
		)
	groups = sorted(grouped.values(), key=lambda group: group["person"].lower())
	return {"groups": groups, "today": today_text}


@frappe.whitelist(methods=["POST"])
def close_task(name: str) -> dict:
	user = require_desk_user()
	name = (name or "").strip()
	if not name or not frappe.db.exists("ToDo", name):
		frappe.throw(_("That task was not found."))
	todo = frappe.get_doc("ToDo", name)
	if not _can_close(todo, user):
		frappe.throw(_("You cannot close this task."), frappe.PermissionError)
	if todo.status == "Closed":
		return {"message": _("Already done.")}
	todo.status = "Closed"
	todo.flags.ignore_permissions = True
	todo.save()
	return {"message": _("Marked done.")}


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


def _require_enabled_user(person: str) -> None:
	row = frappe.db.get_value("User", person, ["enabled", "user_type", "name"], as_dict=True)
	if not row or not row.enabled or row.user_type != "System User" or is_protected_user(row.name):
		frappe.throw(_("Choose someone who can log in."))


def _clean_reference(reference_type: str | None, reference_name: str | None) -> tuple[str, str]:
	reference_type = (reference_type or "").strip()
	reference_name = (reference_name or "").strip()
	if not reference_type and not reference_name:
		return "", ""
	if reference_type not in LINKABLE_DOCTYPES:
		frappe.throw(_("Choose a record type from the list, or leave it empty."))
	if not reference_name:
		frappe.throw(_("Choose which record to attach, or clear the record type."))
	if not frappe.db.exists("DocType", reference_type) or not frappe.db.exists(
		reference_type, reference_name
	):
		frappe.throw(_("That record was not found."))
	if not frappe.has_permission(reference_type, "read", reference_name):
		frappe.throw(_("You cannot open that record."), frappe.PermissionError)
	return reference_type, reference_name


@frappe.whitelist()
def search_records(doctype: str, text: str | None = None) -> list[dict]:
	"""A short list of records the signed-in person is allowed to read."""
	require_desk_user()
	doctype = (doctype or "").strip()
	if doctype not in LINKABLE_DOCTYPES or not frappe.db.exists("DocType", doctype):
		return []
	if not frappe.has_permission(doctype, "read"):
		return []
	text = (text or "").strip()
	filters = {"name": ["like", f"%{text}%"]} if text else None
	rows = frappe.get_list(doctype, filters=filters, fields=["name"], limit=20, order_by="modified desc")
	return [{"name": row.name} for row in rows]


def _can_close(todo, user: str) -> bool:
	return bool(is_system_manager() or todo.allocated_to == user or todo.assigned_by == user)
