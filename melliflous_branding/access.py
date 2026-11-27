# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Who may open the apps-screen tiles. Checked again inside every whitelisted method."""

from __future__ import annotations

import frappe
from frappe import _

from melliflous_branding.distributors import can_open_distributor_360


def can_show_quick_actions() -> bool:
	"""Apps-screen tile. Guests stay on the login page, so they never see it."""
	try:
		user = frappe.session.user
	except Exception:
		return False
	return bool(user) and user != "Guest"


def can_show_distributor_360() -> bool:
	"""Distributor 360 tile. System Manager, Sales Manager, and Sales User only."""
	try:
		user = frappe.session.user
	except Exception:
		return False
	try:
		roles = frappe.get_roles(user)
	except Exception:
		roles = []
	return can_open_distributor_360(user, roles)


def require_system_manager() -> None:
	frappe.only_for("System Manager")


def require_desk_user() -> str:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	user_type = frappe.db.get_value("User", user, "user_type")
	if user_type != "System User":
		frappe.throw(_("You are not allowed to do this."), frappe.PermissionError)
	return user


def is_system_manager() -> bool:
	return "System Manager" in set(frappe.get_roles())
