# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Which desk modules stay on screen in Melliflous Simple Mode.

No Frappe import. The boot hook and the migrate step both call these rules.
Turning simple mode off restores a workspace's previous is_hidden value.
Nothing here deletes a workspace, a shortcut, or a permission.
"""

from __future__ import annotations

# Hidden from the sidebar and from the apps-screen dock. Names are the English
# workspace, module, or sidebar labels. A translated label still matches when
# link_to is the English name, which is what the desk stores.
HIDDEN_WORKSPACES: tuple[str, ...] = (
	"Manufacturing",
	"Projects",
	"Assets",
	"Quality",
	"Quality Management",
	"Support",
	"Website",
	"Tools",
	"Build",
	"Integrations",
	"ERPNext Settings",
	"Subcontracting",
	"Loans",
	"Loan Management",
	"Payroll",
)

# Loan and payroll links that sit inside HR rather than as their own workspace.
HR_EXTRAS: tuple[str, ...] = (
	"Payroll",
	"Salary Slip",
	"Salary Structure",
	"Salary Structure Assignment",
	"Payroll Entry",
	"Salary Component",
	"Loan",
	"Loan Application",
	"Loan Product",
	"Loan Type",
	"Loan Disbursement",
	"Loan Repayment",
)

# Kept, but moved under the everyday modules.
LOWER_WORKSPACES: tuple[str, ...] = (
	"HR",
	"Frappe HR",
	"HRMS",
	"Attendance",
	"Leaves",
	"Shift & Attendance",
	"Employees",
)

# App tiles taken off the apps grid. The app stays in the boot payload so the
# desk can still resolve its name. Raven, Drive, CRM, ERPNext, and HR stay.
OFF_GRID_APP_TITLES: tuple[str, ...] = (
	"Frappe Framework",
	"Framework",
	"Build",
	"Website",
)

LOWER_APP_TITLES: tuple[str, ...] = ("Frappe HR", "HR", "HRMS")
LOWER_SEQUENCE = 80

# Shortcuts a kept workspace still shows while simple mode is on. Other
# shortcuts stay in the workspace document; the desk script only hides them.
ESSENTIAL_SHORTCUTS: dict[str, tuple[str, ...]] = {
	"Selling": (
		"Quick Invoice",
		"New Quick Invoice",
		"Quotation",
		"New Quotation",
		"Sales Order",
		"New Sales Order",
		"Sales Invoice",
		"Invoice Deletion Log",
		"Payment Entry",
		"Payment Received",
		"Customer",
		"Distributor 360",
	),
	"Stock": ("Item", "Stock Entry", "Stock Balance", "Delivery Note"),
	"Buying": ("Supplier", "Purchase Order", "Purchase Invoice"),
	"Accounting": ("Payment Entry", "Journal Entry", "General Ledger", "Accounts Receivable"),
	"Accounts": ("Payment Entry", "Journal Entry", "General Ledger", "Accounts Receivable"),
}

SECTION_TYPES = frozenset({"Section Break", "Spacer"})


def fold(value) -> str:
	return " ".join(str(value or "").split()).casefold()


def _names(rows: tuple[str, ...]) -> set[str]:
	return {fold(row) for row in rows}


HIDDEN_NAMES = _names(HIDDEN_WORKSPACES + HR_EXTRAS)
LOWER_NAMES = _names(LOWER_WORKSPACES)
OFF_GRID_NAMES = _names(OFF_GRID_APP_TITLES)
LOWER_APP_NAMES = _names(LOWER_APP_TITLES)


def name_is_hidden(value) -> bool:
	text = fold(value)
	return bool(text) and text in HIDDEN_NAMES


def name_is_lower(value) -> bool:
	text = fold(value)
	return bool(text) and text in LOWER_NAMES


def shortcut_kept(workspace, label) -> bool:
	"""True when this shortcut stays visible, or when the workspace is not trimmed."""
	allow = None
	folded = fold(workspace)
	for key, names in ESSENTIAL_SHORTCUTS.items():
		if fold(key) == folded:
			allow = names
			break
	if allow is None:
		return True
	return fold(label) in _names(allow)


def _entry_text(entry: dict) -> list[str]:
	return [entry.get("link_to"), entry.get("title"), entry.get("label"), entry.get("name")]


def entry_hidden(entry) -> bool:
	if not isinstance(entry, dict):
		return False
	return any(name_is_hidden(value) for value in _entry_text(entry))


def entry_lower(entry) -> bool:
	if not isinstance(entry, dict):
		return False
	return any(name_is_lower(value) for value in _entry_text(entry))


def _split_lower(entries: list) -> list:
	head = []
	tail = []
	for entry in entries:
		if entry_lower(entry):
			tail.append(entry)
		else:
			head.append(entry)
	return head + tail


def filter_app_rows(rows) -> list:
	"""Apps grid. Hidden modules leave the dock. Framework leaves the grid.

	The row itself stays in the list when it is an app the desk still has to
	name. on_apps_screen is cleared for Framework, Build, and Website.
	"""
	kept = []
	for row in rows or []:
		if not isinstance(row, dict):
			kept.append(row)
			continue
		copy = dict(row)
		title = copy.get("app_title") or ""
		if fold(title) in OFF_GRID_NAMES:
			copy["on_apps_screen"] = False
		if fold(title) in LOWER_APP_NAMES:
			copy["sequence_id"] = LOWER_SEQUENCE
		dock = [entry for entry in (copy.get("dock") or []) if not entry_hidden(entry)]
		copy["dock"] = _split_lower(dock)
		kept.append(copy)
	return kept


def filter_dock(dock):
	"""boot.dock is keyed by app. Hidden destinations are dropped."""
	if not isinstance(dock, dict):
		return dock
	out = {}
	for app, entries in dock.items():
		if not isinstance(entries, list):
			out[app] = entries
			continue
		visible = [entry for entry in entries if not entry_hidden(entry)]
		out[app] = _split_lower(visible)
	return out


def item_hidden(item) -> bool:
	if not isinstance(item, dict):
		return False
	if item.get("type") in SECTION_TYPES:
		return name_is_hidden(item.get("label"))
	return entry_hidden(item)


def arrange_items(items) -> list:
	"""Drop hidden links, keep HR-style links, and move those under the rest."""
	kept = []
	lowered = []
	for item in items or []:
		if not isinstance(item, dict):
			kept.append(item)
			continue
		if item_hidden(item):
			continue
		if item.get("type") not in SECTION_TYPES and entry_lower(item):
			lowered.append(item)
			continue
		kept.append(item)
	return _drop_empty_sections(kept) + lowered


def _drop_empty_sections(items) -> list:
	"""A section header with nothing under it is just clutter."""
	result = []
	pending = []
	for item in items:
		kind = item.get("type") if isinstance(item, dict) else None
		if kind in SECTION_TYPES:
			pending.append(item)
			continue
		result.extend(pending)
		pending = []
		result.append(item)
	return result


def filter_sidebars(payload):
	"""Drop hidden shells and hidden items. Other shells are copied."""
	if not isinstance(payload, dict):
		return payload
	out = {}
	for key, sidebar in payload.items():
		if name_is_hidden(key):
			continue
		if not isinstance(sidebar, dict):
			out[key] = sidebar
			continue
		if name_is_hidden(sidebar.get("name")) or name_is_hidden(sidebar.get("label")):
			# A shell whose own name is Manufacturing, Payroll, and so on.
			# A shell titled Selling that merely links to those stays.
			if fold(sidebar.get("name") or key) in _names(HIDDEN_WORKSPACES) or fold(
				sidebar.get("label") or ""
			) in _names(HIDDEN_WORKSPACES):
				continue
		copy = dict(sidebar)
		copy["items"] = arrange_items(copy.get("items") or [])
		out[key] = copy
	return out


def filter_desktop_icons(icons):
	if not isinstance(icons, list):
		return icons
	kept = []
	for icon in icons:
		if isinstance(icon, dict) and (
			name_is_hidden(icon.get("label"))
			or name_is_hidden(icon.get("module_name"))
			or name_is_hidden(icon.get("link"))
		):
			continue
		kept.append(icon)
	return kept


def plan_workspace_visibility(rows, simple_on: bool, remembered: dict | None) -> tuple[list[dict], dict]:
	"""Decide is_hidden updates, and the memory used to undo them.

	`remembered` maps a workspace name to the is_hidden value it had before
	this app hid it. Turning simple mode off writes those values back and
	forgets them, so a workspace someone hid on their own is not reopened
	later by accident.
	"""
	memory = {str(key): int(value) for key, value in (remembered or {}).items()}
	updates = []
	if simple_on:
		kept = {}
		for row in rows or []:
			name = str(row.get("name") or "")
			if not name:
				continue
			if not (
				name_is_hidden(row.get("label"))
				or name_is_hidden(name)
				or fold(row.get("label")) in _names(HIDDEN_WORKSPACES)
				or fold(name) in _names(HIDDEN_WORKSPACES)
			):
				continue
			current = int(row.get("is_hidden") or 0)
			previous = memory.get(name, current)
			kept[name] = int(previous)
			if current != 1:
				updates.append({"name": name, "is_hidden": 1})
		return updates, kept

	for row in rows or []:
		name = str(row.get("name") or "")
		if name not in memory:
			continue
		target = int(memory[name])
		current = int(row.get("is_hidden") or 0)
		if current != target:
			updates.append({"name": name, "is_hidden": target})
	return updates, {}
