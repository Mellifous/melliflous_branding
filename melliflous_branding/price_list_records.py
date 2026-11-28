# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Give Priti a Price List she can create, without editing anyone else's rights.

Custom DocPerm is used because ERPNext owns the Price List, Item Price, and
Item fixtures. A second run finds the same rows and writes nothing.
"""

from __future__ import annotations

import frappe

from melliflous_branding.price_lists import (
	PRICE_RIGHTS,
	PRICE_ROLE,
	PRITI_EMAIL,
	copied_standard_perm,
	is_priti,
	permission_writes,
)


def ensure_priti_price_lists() -> None:
	if not frappe.db.exists("DocType", "Role") or not frappe.db.table_exists("Custom DocPerm"):
		return
	_ensure_role()
	_grant_priti()
	changed = []
	for doctype in PRICE_RIGHTS:
		if not frappe.db.exists("DocType", doctype):
			continue
		if _copy_standard_perms(doctype):
			changed.append(doctype)
		if _grant_role(doctype):
			changed.append(doctype)
	for doctype in set(changed):
		frappe.clear_cache(doctype=doctype)


def _ensure_role() -> None:
	if frappe.db.exists("Role", PRICE_ROLE):
		return
	frappe.get_doc({"doctype": "Role", "role_name": PRICE_ROLE, "desk_access": 1}).insert(ignore_permissions=True)


def _grant_priti() -> None:
	if not frappe.db.table_exists("User"):
		return
	seen = set()
	for row in frappe.get_all("User", filters={"email": PRITI_EMAIL}, fields=["name", "email"]):
		seen.add(row.name)
		if is_priti(row.name, row.email):
			_add_role(row.name)
	if PRITI_EMAIL not in seen and frappe.db.exists("User", PRITI_EMAIL) and is_priti(PRITI_EMAIL, PRITI_EMAIL):
		_add_role(PRITI_EMAIL)


def _add_role(user) -> None:
	if not frappe.db.exists("User", user) or not frappe.db.exists("Role", PRICE_ROLE):
		return
	if frappe.db.exists("Has Role", {"parent": user, "role": PRICE_ROLE, "parenttype": "User"}):
		return
	frappe.get_doc("User", user).add_roles(PRICE_ROLE)


def _copy_standard_perms(doctype) -> bool:
	"""Copy DocPerm once. Existing custom rows, including other roles, stay put."""
	if frappe.db.exists("Custom DocPerm", {"parent": doctype}):
		return False
	if not frappe.db.table_exists("DocPerm"):
		return False
	columns = set(frappe.db.get_table_columns("Custom DocPerm") or [])
	copied = False
	for row in frappe.get_all("DocPerm", filters={"parent": doctype}, fields=["*"]):
		payload = copied_standard_perm(row, doctype)
		if columns:
			payload = {
				key: value
				for key, value in payload.items()
				if key == "doctype" or key in columns
			}
		frappe.get_doc(payload).insert(ignore_permissions=True)
		copied = True
	return copied


def _grant_role(doctype) -> bool:
	rows = frappe.get_all(
		"Custom DocPerm",
		filters={"parent": doctype, "role": PRICE_ROLE},
		fields=["*"],
	)
	writes = permission_writes(rows, doctype)
	if not writes:
		return False
	columns = set(frappe.db.get_table_columns("Custom DocPerm") or [])
	wrote = False
	for change in writes:
		if change.get("insert"):
			payload = {
				"doctype": "Custom DocPerm",
				"parent": doctype,
				"parenttype": "DocType",
				"parentfield": "permissions",
				"role": PRICE_ROLE,
				"permlevel": 0,
			}
			payload.update({key: value for key, value in change.items() if key in columns})
			frappe.get_doc(payload).insert(ignore_permissions=True)
			wrote = True
			continue
		fields = {key: value for key, value in change.items() if key != "name" and key in columns}
		if fields:
			frappe.db.set_value("Custom DocPerm", change["name"], fields, update_modified=False)
			wrote = True
	return wrote
