# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Retire the Quick Actions workspace this app used to ship.

The six cards on the desk home are the quick actions. The apps-screen tile and
the workspace are not. A workspace with the same name in another module is left
alone.
"""

from __future__ import annotations

WORKSPACE_NAME = "Quick Actions"
MODULE_NAME = "Melliflous Branding"
SIDEBAR_NAME = "Melliflous Branding"


def workspace_is_ours(name, module) -> bool:
	"""True when this app created the workspace, including a row with a blank module."""
	if str(name or "").strip() != WORKSPACE_NAME:
		return False
	owner = str(module or "").strip()
	return not owner or owner == MODULE_NAME


def sidebar_item_is_quick_actions(row) -> bool:
	"""A sidebar link that opens the retired workspace."""
	if not isinstance(row, dict):
		link_type = getattr(row, "link_type", None)
		link_to = getattr(row, "link_to", None)
		label = getattr(row, "label", None)
	else:
		link_type = row.get("link_type")
		link_to = row.get("link_to")
		label = row.get("label")
	if link_type == "Workspace" and str(link_to or "").strip() == WORKSPACE_NAME:
		return True
	return str(label or "").strip() == WORKSPACE_NAME and link_type == "Workspace"


def remove_quick_actions_workspace():
	"""Delete the workspace when it is ours, and drop the sidebar link to it.

	If the delete is refused, the workspace is hidden so it leaves the sidebar
	and the apps list. Safe to run more than once.
	"""
	import frappe

	removed = False
	if frappe.db.table_exists("Workspace") and frappe.db.exists("Workspace", WORKSPACE_NAME):
		module = frappe.db.get_value("Workspace", WORKSPACE_NAME, "module")
		if workspace_is_ours(WORKSPACE_NAME, module):
			try:
				frappe.delete_doc(
					"Workspace",
					WORKSPACE_NAME,
					force=1,
					ignore_permissions=True,
					delete_permanently=True,
				)
				removed = True
			except Exception:
				frappe.logger("melliflous_branding").exception("Could not delete the Quick Actions workspace")
				frappe.db.set_value("Workspace", WORKSPACE_NAME, "is_hidden", 1, update_modified=False)
				removed = True
	if _drop_sidebar_link():
		removed = True
	if removed:
		frappe.clear_cache()
	return removed


def _drop_sidebar_link() -> bool:
	import frappe

	if not frappe.db.table_exists("Sidebar") or not frappe.db.exists("Sidebar", SIDEBAR_NAME):
		return False
	doc = frappe.get_doc("Sidebar", SIDEBAR_NAME)
	removed = [row for row in (doc.items or []) if sidebar_item_is_quick_actions(row)]
	if not removed:
		return False
	for row in removed:
		doc.remove(row)
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	return True
