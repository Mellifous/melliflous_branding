# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Melliflous Simple Mode. The desk hides extra modules until an admin turns it off.

Boot applies the same hide list even when this DocType has not been migrated yet.
Workspace.is_hidden is touched only once the Settings record exists, so the
previous value can be put back.
"""

from __future__ import annotations

import json

import frappe
from frappe import _

from melliflous_branding.access import require_desk_user
from melliflous_branding.desk import (
	ESSENTIAL_SHORTCUTS,
	HIDDEN_WORKSPACES,
	HR_EXTRAS,
	LOWER_WORKSPACES,
	filter_app_rows,
	filter_desktop_icons,
	filter_dock,
	filter_sidebars,
	plan_workspace_visibility,
)

SHOW_ALL_KEY = "melliflous_show_all"
SETTINGS = "Melliflous Settings"


def is_desk_admin(user, roles) -> bool:
	if not user or user == "Guest":
		return False
	if user == "Administrator":
		return True
	return "System Manager" in set(roles or [])


def simple_mode_enabled() -> bool:
	"""Site switch. Missing table, missing row, and a blank value all mean on."""
	try:
		if not frappe.db.exists("DocType", SETTINGS):
			return True
		if not frappe.db.table_exists(f"tab{SETTINGS}"):
			return True
		value = frappe.db.get_single_value(SETTINGS, "simple_mode")
	except Exception:
		return True
	if value is None or value == "":
		return True
	return bool(int(value)) if str(value).isdigit() else bool(value)


def user_wants_everything(user) -> bool:
	try:
		return str(frappe.defaults.get_user_default(SHOW_ALL_KEY, user) or "") == "1"
	except Exception:
		return False


def apply_simple_boot(bootinfo) -> None:
	"""Attach the switch and, when simple mode is on, filter the desk payload."""
	user = getattr(frappe.session, "user", None)
	try:
		roles = frappe.get_roles(user) if user else []
	except Exception:
		roles = []
	can_toggle = is_desk_admin(user, roles)
	enabled = simple_mode_enabled()
	show_all = bool(can_toggle and user_wants_everything(user))
	active = bool(enabled and not show_all)
	bootinfo.melliflous_simple = {
		"enabled": enabled,
		"show_all": show_all,
		"can_toggle": can_toggle,
		"active": active,
		"hidden": list(HIDDEN_WORKSPACES),
		"lower": list(LOWER_WORKSPACES),
		"hr_extras": list(HR_EXTRAS),
		"shortcuts": {key: list(names) for key, names in ESSENTIAL_SHORTCUTS.items()},
	}
	if not active:
		return
	try:
		bootinfo.app_data = filter_app_rows(getattr(bootinfo, "app_data", None))
	except Exception:
		frappe.logger("melliflous_branding").exception("Could not filter the apps grid")
	for field, fn in (
		("module_sidebars", filter_sidebars),
		("dock", filter_dock),
		("desktop_icons", filter_desktop_icons),
	):
		current = getattr(bootinfo, field, None)
		if current is None:
			continue
		try:
			setattr(bootinfo, field, fn(current))
		except Exception:
			frappe.logger("melliflous_branding").exception("Could not filter boot.%s", field)


@frappe.whitelist(methods=["POST"])
def set_show_all(show_all: str | int = 0) -> dict:
	"""Personal override for System Manager and Administrator. The site switch stays put."""
	user = require_desk_user()
	if not is_desk_admin(user, frappe.get_roles(user)):
		frappe.throw(_("Only an admin can show the full desk."), frappe.PermissionError)
	enabled = str(show_all).strip() in {"1", "true", "True"}
	frappe.defaults.set_user_default(SHOW_ALL_KEY, "1" if enabled else "0", user)
	_clear_boot_cache(user)
	return {"show_all": enabled, "simple_mode": simple_mode_enabled()}


def sync_simple_desk() -> None:
	"""Set or restore Workspace.is_hidden. Safe to run more than once."""
	if not _settings_ready() or not frappe.db.table_exists("tabWorkspace"):
		return
	rows = frappe.get_all("Workspace", fields=["name", "label", "is_hidden"])
	updates, memory = plan_workspace_visibility(rows, simple_mode_enabled(), _read_memory())
	for row in updates:
		frappe.db.set_value("Workspace", row["name"], "is_hidden", row["is_hidden"], update_modified=False)
	_write_memory(memory)
	_clear_boot_cache(None)


def ensure_simple_desk() -> None:
	"""Migrate hook. The Page and the Settings DocType are imported by the patch."""
	try:
		sync_simple_desk()
	except Exception:
		frappe.logger("melliflous_branding").exception("Could not sync the simple desk")


def _settings_ready() -> bool:
	try:
		return bool(frappe.db.exists("DocType", SETTINGS) and frappe.db.table_exists(f"tab{SETTINGS}"))
	except Exception:
		return False


def _read_memory() -> dict:
	if not _settings_ready():
		return {}
	raw = frappe.db.get_single_value(SETTINGS, "workspace_restore") or ""
	if not raw:
		return {}
	try:
		parsed = json.loads(raw)
	except Exception:
		return {}
	return parsed if isinstance(parsed, dict) else {}


def _write_memory(memory: dict) -> None:
	if not _settings_ready():
		return
	frappe.flags.melliflous_settings_sync = True
	try:
		frappe.db.set_single_value(
			SETTINGS,
			"workspace_restore",
			json.dumps(memory, sort_keys=True),
			update_modified=False,
		)
	finally:
		frappe.flags.melliflous_settings_sync = False


def _clear_boot_cache(user) -> None:
	try:
		if user:
			frappe.cache.hdel("bootinfo", user)
			return
		for key in frappe.cache.hkeys("bootinfo") or []:
			frappe.cache.hdel("bootinfo", key)
	except Exception:
		frappe.logger("melliflous_branding").exception("Could not clear the desk boot cache")
