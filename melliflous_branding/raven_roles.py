# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Give desk users the Raven User role when that role is installed."""

from __future__ import annotations

import frappe

from melliflous_branding.quick import RAVEN_ROLE, is_protected_user, raven_role_targets


def grant_missing_raven_roles() -> int:
	"""Add Raven User to every enabled System User who does not have it.

	Does nothing when the Role is missing, and never changes Administrator or Guest.
	"""
	if not frappe.db.exists("Role", RAVEN_ROLE):
		return 0
	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name"],
		limit=0,
	)
	if not users:
		return 0
	names = [row.name for row in users]
	already = set(
		frappe.get_all(
			"Has Role",
			filters={"parent": ["in", names], "parenttype": "User", "role": RAVEN_ROLE},
			pluck="parent",
		)
	)
	targets = raven_role_targets(
		[
			{
				"name": row.name,
				"enabled": 1,
				"user_type": "System User",
				"roles": {RAVEN_ROLE} if row.name in already else set(),
			}
			for row in users
		],
		role_exists=True,
	)
	granted = 0
	for name in targets:
		if is_protected_user(name):
			continue
		user = frappe.get_doc("User", name)
		user.add_roles(RAVEN_ROLE)
		granted += 1
	return granted


def grant_raven_role_on_user(user) -> None:
	"""Append Raven User before the caller saves. No extra save, and no-op if the role is missing."""
	if is_protected_user(getattr(user, "name", None)):
		return
	if getattr(user, "user_type", None) != "System User":
		return
	if not frappe.db.exists("Role", RAVEN_ROLE):
		return
	if any(getattr(row, "role", None) == RAVEN_ROLE for row in (user.roles or [])):
		return
	user.append("roles", {"role": RAVEN_ROLE})
