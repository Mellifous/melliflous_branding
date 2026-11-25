# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Company list for the current user. User Permissions restrict it; otherwise all."""

from __future__ import annotations

import frappe

from melliflous_branding.branding import companies_for_user


def get_permitted_companies() -> list[str]:
	"""Companies this user may switch to.

	A User Permission on Company limits the list to those documents (including
	ones that apply only to a specific DocType). A user with no Company user
	permission is unrestricted and sees every Company they can read.
	"""
	user = getattr(frappe.session, "user", None)
	if not user or user == "Guest":
		return []
	if not frappe.db.exists("DocType", "Company"):
		return []

	from frappe.core.doctype.user_permission.user_permission import get_user_permissions

	permission_names: list[str] = []
	for row in get_user_permissions().get("Company") or []:
		docname = row.get("doc") if isinstance(row, dict) else None
		if docname:
			permission_names.append(docname)

	# limit=0 is "no LIMIT" on the v16 query engine (a truthy limit is what pages).
	readable = frappe.get_list("Company", pluck="name", order_by="name asc", limit=0)
	names = companies_for_user(permission_names, list(readable or []))
	if permission_names and not readable and names:
		existing = set(
			frappe.get_all(
				"Company",
				filters={"name": ["in", names]},
				pluck="name",
				limit=0,
			)
		)
		names = [name for name in names if name in existing]
	return names
