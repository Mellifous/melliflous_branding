# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Add or update a team member: user, roles, and one permission per company."""

from __future__ import annotations

import frappe
from frappe import _

from melliflous_branding.access import require_system_manager
from melliflous_branding.quick import (
	ROLE_CHOICES,
	clean_companies,
	guess_role,
	is_protected_user,
	managed_roles,
	role_label,
	roles_to_assign,
	split_name,
)
from melliflous_branding.raven_roles import grant_raven_role_on_user


@frappe.whitelist()
def form_options() -> dict:
	require_system_manager()
	return {
		"companies": _companies(),
		"roles": [{"key": choice["key"], "label": choice["label"]} for choice in ROLE_CHOICES],
	}


@frappe.whitelist()
def list_members() -> list[dict]:
	require_system_manager()
	users = frappe.get_all(
		"User",
		filters={
			"user_type": "System User",
			"name": ["not in", ["Administrator", "Guest"]],
		},
		fields=["name", "full_name", "enabled", "mobile_no"],
		order_by="full_name asc",
		limit=0,
	)
	if not users:
		return []
	names = [user.name for user in users]
	permissions = frappe.get_all(
		"User Permission",
		filters={"allow": "Company", "user": ["in", names]},
		fields=["user", "for_value", "is_default"],
		limit=0,
	)
	role_rows = frappe.get_all(
		"Has Role",
		filters={"parent": ["in", names], "parenttype": "User"},
		fields=["parent", "role"],
		limit=0,
	)
	companies_by_user: dict[str, list[dict]] = {}
	for row in permissions:
		companies_by_user.setdefault(row.user, []).append(row)
	roles_by_user: dict[str, set[str]] = {}
	for row in role_rows:
		roles_by_user.setdefault(row.parent, set()).add(row.role)

	members = []
	for user in users:
		if is_protected_user(user.name):
			continue
		companies = companies_by_user.get(user.name, [])
		default = next((row.for_value for row in companies if row.is_default), "")
		if not default and companies:
			default = companies[0].for_value
		role_key = guess_role(roles_by_user.get(user.name, set()))
		members.append(
			{
				"email": user.name,
				"full_name": user.full_name or user.name,
				"mobile": user.mobile_no or "",
				"enabled": int(user.enabled or 0),
				"companies": [row.for_value for row in companies],
				"default_company": default,
				"role": role_key or "",
				"role_label": role_label(role_key),
			}
		)
	return members


@frappe.whitelist(methods=["POST"])
def save_member(
	full_name: str,
	email: str,
	mobile: str | None = None,
	companies: str | list | None = None,
	default_company: str | None = None,
	role: str | None = None,
) -> dict:
	"""Create or update one person. System Manager only. Never Administrator or Guest."""
	require_system_manager()
	full_name = (full_name or "").strip()
	email = (email or "").strip().lower()
	mobile = (mobile or "").strip()
	if not full_name:
		frappe.throw(_("Enter their full name."))
	if "@" not in email or email.startswith("@") or email.endswith("@"):
		frappe.throw(_("Enter a real email address."))
	if is_protected_user(email):
		frappe.throw(_("That account is protected and cannot be changed here."))

	try:
		ticked, default = clean_companies(frappe.parse_json(companies) or [], default_company)
	except ValueError as error:
		frappe.throw(_(str(error)))

	missing = [name for name in ticked if not frappe.db.exists("Company", name)]
	if missing:
		frappe.throw(_("That company is not on this site: {0}").format(", ".join(missing)))

	choice_roles = _installed_roles(role)
	first_name, last_name = split_name(full_name)

	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
		if is_protected_user(user.name):
			frappe.throw(_("That account is protected and cannot be changed here."))
		created = False
	else:
		user = frappe.new_doc("User")
		user.email = email
		user.name = email
		created = True

	user.enabled = 1
	user.user_type = "System User"
	user.send_welcome_email = 0
	user.first_name = first_name
	user.last_name = last_name
	user.mobile_no = mobile
	_apply_roles(user, choice_roles)
	# Raven User is not one of the job roles. Add it when the role exists so a
	# new person can open Team Chat without waiting for the next migrate.
	grant_raven_role_on_user(user)
	user.flags.ignore_permissions = True
	user.save()

	_sync_company_permissions(user.name, ticked, default)
	frappe.defaults.set_user_default("company", default, user.name)

	message = _("Saved. {0} is set up. No email was sent. Set a password before they sign in.").format(
		user.full_name or full_name
	)
	if not created:
		message = _("Saved changes for {0}.").format(user.full_name or full_name)
	return {"email": user.name, "full_name": user.full_name or full_name, "message": message}


def _companies() -> list[str]:
	return frappe.get_all("Company", pluck="name", order_by="name asc", limit=0)


def _installed_roles(role_key: str | None) -> list[str]:
	from melliflous_branding.quick import role_choice

	choice = role_choice(role_key)
	if not choice:
		frappe.throw(_("Choose what this person does."))
	installed = set(frappe.get_all("Role", pluck="name", limit=0))
	wanted = roles_to_assign(choice["key"], installed)
	if not wanted:
		frappe.throw(_("The {0} role is not installed on this site yet.").format(choice["label"]))
	return wanted


def _apply_roles(user, wanted: list[str]) -> None:
	"""Replace the jobs we manage. Leave unrelated roles such as Employee alone.

	Any Role Profile is cleared. On v16 a profile replaces the user's whole
	role list on save, which would undo this choice and drop roles it does
	not name.
	"""
	if user.meta.has_field("role_profiles"):
		user.role_profiles = []
	if user.meta.has_field("role_profile_name"):
		user.role_profile_name = None

	managed = managed_roles()
	user.roles = [row for row in user.roles if row.role not in managed or row.role in wanted]
	have = {row.role for row in user.roles}
	for role in wanted:
		if role not in have:
			user.append("roles", {"role": role})


def _sync_company_permissions(user: str, companies: list[str], default: str) -> None:
	rows = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Company"},
		fields=["name", "for_value"],
		limit=0,
	)
	keep = set(companies)
	for row in rows:
		if row.for_value not in keep:
			frappe.delete_doc("User Permission", row.name, ignore_permissions=True, force=True)

	# Clear every default first so two Company permissions are never default together.
	frappe.db.set_value(
		"User Permission",
		{"user": user, "allow": "Company"},
		"is_default",
		0,
		update_modified=False,
	)
	existing = {
		row.for_value: row.name
		for row in frappe.get_all(
			"User Permission",
			filters={"user": user, "allow": "Company"},
			fields=["name", "for_value"],
			limit=0,
		)
	}
	for company in companies:
		if company in existing:
			frappe.db.set_value(
				"User Permission",
				existing[company],
				{
					"apply_to_all_doctypes": 1,
					"applicable_for": "",
					"is_default": 1 if company == default else 0,
				},
				update_modified=False,
			)
			continue
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Company",
				"for_value": company,
				"apply_to_all_doctypes": 1,
				"is_default": 1 if company == default else 0,
			}
		).insert(ignore_permissions=True)
