# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import json
import unittest
from pathlib import Path

from melliflous_branding.divisions import (
	MIMT_COMPANY,
	SEEDED_DIVISIONS,
	DivisionError,
	choose_division,
	fields_for,
	validate_division,
)
from melliflous_branding.invoice_admin import gst_flags_to_clear

PACKAGE = Path(__file__).resolve().parents[1]


class TestDivisions(unittest.TestCase):
	def test_switching_company_picks_a_division_of_that_company(self):
		rows = [
			{"name": "SK Gourmet Spices", "company": MIMT_COMPANY, "is_active": 1},
			{"name": "Sunkeera", "company": MIMT_COMPANY, "is_active": 1},
			{"name": "Other", "company": "Another Co", "is_active": 1},
			{"name": "Closed", "company": MIMT_COMPANY, "is_active": 0},
		]
		self.assertEqual(choose_division(rows, MIMT_COMPANY, "Sunkeera"), "Sunkeera")
		self.assertEqual(choose_division(rows, MIMT_COMPANY, "Other"), "SK Gourmet Spices")
		self.assertEqual(choose_division(rows, "Missing", "Sunkeera"), "")
		validate_division(MIMT_COMPANY, MIMT_COMPANY)
		validate_division("", MIMT_COMPANY)
		with self.assertRaises(DivisionError):
			validate_division("Another Co", MIMT_COMPANY)

	def test_the_link_is_filtered_only_when_the_document_has_a_company(self):
		specs = fields_for(["Sales Invoice", "Customer", "Item", "CRM Lead"])
		self.assertIn("link_filters", specs["Sales Invoice"][0])
		self.assertNotIn("link_filters", specs["Customer"][0])
		self.assertNotIn("link_filters", specs["Item"][0])
		self.assertEqual(specs["Sales Invoice"][0]["fieldname"], "division")
		self.assertEqual(specs["Sales Invoice"][0]["options"], "Division")
		names = [row["division_name"] for row in SEEDED_DIVISIONS]
		self.assertEqual(names, ["SK Gourmet Spices", "Sunkeera"])
		doctype = json.loads((PACKAGE / "melliflous_branding" / "doctype" / "division" / "division.json").read_text())
		self.assertEqual(doctype["autoname"], "field:division_name")
		records = (PACKAGE / "division_records.py").read_text()
		self.assertIn("frappe.db.exists(\"Company\", MIMT_COMPANY)", records)
		self.assertIn("User Permissions on Division", doctype["description"])
		script = (PACKAGE / "public" / "js" / "melliflous_branding.js").read_text()
		self.assertIn("set_desk_context", script)
		self.assertIn("melliflous-division-switch", script)
		self.assertIn("desk_divisions", script)
		self.assertIn("melliflous-context-style", script)
		self.assertIn("20261128a", (PACKAGE / "hooks.py").read_text())
		self.assertIn("melliflous-context-chip", script)
		self.assertIn("melliflous-context-sheet", script)
		self.assertIn("is-compact", script)
		page = (PACKAGE / "melliflous_branding" / "page" / "distributor_360" / "distributor_360.js").read_text()
		self.assertIn("All divisions", page)
		self.assertIn("melliflous_branding.patches.v0_10.ensure_divisions", (PACKAGE / "patches.txt").read_text())
		self.assertIn(
			"melliflous_branding.patches.v0_12.remove_quick_actions_workspace",
			(PACKAGE / "patches.txt").read_text(),
		)
		from melliflous_branding.quick_actions_workspace import sidebar_item_is_quick_actions, workspace_is_ours

		self.assertTrue(workspace_is_ours("Quick Actions", "Melliflous Branding"))
		self.assertTrue(workspace_is_ours("Quick Actions", ""))
		self.assertFalse(workspace_is_ours("Quick Actions", "Selling"))
		self.assertFalse(workspace_is_ours("Selling", "Melliflous Branding"))
		self.assertTrue(sidebar_item_is_quick_actions({"link_type": "Workspace", "link_to": "Quick Actions", "label": "Quick Actions"}))
		self.assertFalse(sidebar_item_is_quick_actions({"link_type": "Page", "link_to": "quick-invoice", "label": "New Quick Invoice"}))
		remover = (PACKAGE / "quick_actions_workspace.py").read_text()
		self.assertIn("delete_doc", remover)
		self.assertIn("is_hidden", remover)

	def test_gst_submission_flags_are_cleared_even_when_the_saved_value_is_blank(self):
		columns = [
			"enable_e_invoice",
			"enable_e_waybill",
			"auto_generate_e_invoice",
			"auto_generate_e_waybill",
			"generate_e_waybill_with_e_invoice",
			"auto_cancel_e_invoice",
			"api_secret",
		]
		cleared = gst_flags_to_clear(columns, allow_auto=False)
		self.assertIn("auto_generate_e_invoice", cleared)
		self.assertIn("auto_generate_e_waybill", cleared)
		self.assertNotIn("enable_e_invoice", cleared)
		self.assertNotIn("api_secret", cleared)
		self.assertEqual(gst_flags_to_clear(columns, allow_auto=True), [])
		self.assertIn("auto_generate_e_waybill", gst_flags_to_clear([], allow_auto=False))
		self.assertIn("generate_e_waybill_with_e_invoice", gst_flags_to_clear([], allow_auto=False))
		records = (PACKAGE / "invoice_admin_records.py").read_text()
		self.assertIn("tabSingles", records)
		self.assertIn("'0'", records)
		self.assertIn("frappe.db.commit()", records)
		self.assertIn("clear_cache", records)
		self.assertIn(
			"melliflous_branding.patches.v0_11.clear_gst_auto",
			(PACKAGE / "patches.txt").read_text(),
		)
		self.assertIn("keep_einvoice_manual()", (PACKAGE / "install.py").read_text())


if __name__ == "__main__":
	unittest.main()
