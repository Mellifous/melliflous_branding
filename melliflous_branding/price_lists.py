# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Who may create a Price List. No Frappe import.

This app does not already give Priti an operations role. Van Editor is the van
role and other people can hold it. Melliflous Operations is created for her
email only, so Sales User, Sales Manager, and everyone else keep the rights
they already have.
"""

from __future__ import annotations

PRITI_EMAIL = "priti@skgourmetspices.com"
PRICE_ROLE = "Melliflous Operations"

# Level 0. Create and edit the list and its prices. Read items so a price can
# point at one. No delete, submit, or cancel.
PRICE_RIGHTS = {
	"Price List": {
		"select": 1,
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 0,
		"submit": 0,
		"cancel": 0,
		"amend": 0,
		"report": 1,
		"print": 1,
		"export": 1,
		"if_owner": 0,
	},
	"Item Price": {
		"select": 1,
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 0,
		"submit": 0,
		"cancel": 0,
		"amend": 0,
		"report": 1,
		"print": 1,
		"export": 1,
		"if_owner": 0,
	},
	"Item": {
		"select": 1,
		"read": 1,
		"write": 0,
		"create": 0,
		"delete": 0,
		"submit": 0,
		"cancel": 0,
		"amend": 0,
		"report": 1,
		"print": 0,
		"export": 0,
		"if_owner": 0,
	},
}

DOC_PERM_SKIP = frozenset(
	{"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx", "doctype"}
)


def clean(value) -> str:
	return " ".join(str(value or "").split())


def is_priti(user, email="") -> bool:
	"""The named account only. A similar name does not match."""
	wanted = PRITI_EMAIL.casefold()
	return clean(user).casefold() == wanted or clean(email).casefold() == wanted


def copied_standard_perm(row, doctype) -> dict:
	"""One standard DocPerm copied onto Custom DocPerm, flags unchanged.

	Frappe ignores DocPerm once any Custom DocPerm exists for the DocType, so
	the first run has to copy every current row before adding a new role.
	"""
	copied = {key: row.get(key) for key in row if key not in DOC_PERM_SKIP}
	copied["doctype"] = "Custom DocPerm"
	copied["parent"] = doctype
	copied["parenttype"] = "DocType"
	copied["parentfield"] = "permissions"
	return copied


def permission_writes(rows, doctype, role=PRICE_ROLE) -> list:
	"""Insert or update only this role at level 0. Other roles are not listed."""
	wanted = PRICE_RIGHTS[doctype]
	own = [
		row
		for row in rows or []
		if isinstance(row, dict) and clean(row.get("role")) == role and int(row.get("permlevel") or 0) == 0
	]
	if not own:
		return [{"insert": True, "role": role, "permlevel": 0, **wanted}]
	changes = {}
	for key, value in wanted.items():
		current = int(own[0].get(key) or 0)
		if current != int(value):
			changes[key] = int(value)
	if not changes or not own[0].get("name"):
		return []
	return [{"name": own[0]["name"], **changes}]
