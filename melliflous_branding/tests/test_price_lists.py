# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import unittest
from pathlib import Path

from melliflous_branding.price_lists import (
	PRICE_RIGHTS,
	PRICE_ROLE,
	PRITI_EMAIL,
	copied_standard_perm,
	is_priti,
	permission_writes,
)

PACKAGE = Path(__file__).resolve().parents[1]


class TestPritiPriceLists(unittest.TestCase):
	def test_only_the_named_account_matches(self):
		self.assertTrue(is_priti("Priti", PRITI_EMAIL))
		self.assertTrue(is_priti(PRITI_EMAIL, ""))
		self.assertFalse(is_priti("Sasank", "sasank@skgourmetspices.com"))
		self.assertFalse(is_priti("priti.sharma@example.com", "priti.sharma@example.com"))
		self.assertFalse(is_priti("Administrator", ""))

	def test_rights_are_create_without_delete_or_submit(self):
		for doctype in ("Price List", "Item Price"):
			rights = PRICE_RIGHTS[doctype]
			self.assertEqual(rights["read"], 1)
			self.assertEqual(rights["write"], 1)
			self.assertEqual(rights["create"], 1)
			self.assertEqual(rights["delete"], 0)
			self.assertEqual(rights["submit"], 0)
			self.assertEqual(rights["cancel"], 0)
		item = PRICE_RIGHTS["Item"]
		self.assertEqual(item["read"], 1)
		self.assertEqual(item["write"], 0)
		self.assertEqual(item["create"], 0)
		self.assertEqual(item["delete"], 0)
		self.assertEqual(item["submit"], 0)
		self.assertEqual(item["cancel"], 0)

	def test_other_roles_are_copied_unchanged_and_not_rewritten(self):
		copied = copied_standard_perm(
			{"name": "perm-sales", "role": "Sales Manager", "permlevel": 0, "read": 1, "write": 0, "create": 0, "delete": 1, "submit": 1, "cancel": 1},
			"Price List",
		)
		self.assertEqual(copied["role"], "Sales Manager")
		self.assertEqual(copied["delete"], 1)
		self.assertEqual(copied["submit"], 1)
		self.assertEqual(copied["cancel"], 1)
		self.assertNotIn("name", copied)
		self.assertEqual(copied["parent"], "Price List")
		rows = [
			{"name": "perm-sales", "role": "Sales Manager", "permlevel": 0, "read": 1, "delete": 1, "submit": 1, "cancel": 1},
			{"name": "perm-item", "role": "Item Manager", "permlevel": 0, "read": 1, "write": 1, "create": 1, "delete": 1},
		]
		writes = permission_writes(rows, "Price List")
		self.assertEqual(writes, [{"insert": True, "role": PRICE_ROLE, "permlevel": 0, **PRICE_RIGHTS["Price List"]}])
		self.assertNotIn("Sales Manager", {row.get("role") for row in writes})
		again = permission_writes(
			[{"name": "perm-ops", "role": PRICE_ROLE, "permlevel": 0, **PRICE_RIGHTS["Item"]}],
			"Item",
		)
		self.assertEqual(again, [])

	def test_patch_is_wired_and_does_not_edit_shared_roles(self):
		self.assertIn(
			"melliflous_branding.patches.v0_18.ensure_priti_price_lists",
			(PACKAGE / "patches.txt").read_text(),
		)
		self.assertIn("ensure_priti_price_lists", (PACKAGE / "install.py").read_text())
		records = (PACKAGE / "price_list_records.py").read_text()
		rules = (PACKAGE / "price_lists.py").read_text()
		self.assertIn('set_value("Custom DocPerm"', records)
		self.assertNotIn('set_value("DocPerm"', records)
		self.assertIn(PRICE_ROLE, rules)
		self.assertNotIn("Sales User", records)
		self.assertNotIn("Van Editor", records)
