# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import json
import unittest
from pathlib import Path

from melliflous_branding.invoice_admin import (
	SEED_OWNER_EMAIL,
	auto_fields_to_disable,
	can_generate_einvoice,
	can_manage_invoices,
	delete_block,
	needs_gst_warning,
	rename_block,
	seed_admin_names,
)

PACKAGE = Path(__file__).resolve().parents[1]


class TestInvoiceAdmin(unittest.TestCase):
	def test_only_the_list_and_administrator_may_manage_invoices(self):
		self.assertTrue(can_manage_invoices("Administrator", []))
		self.assertFalse(can_manage_invoices(SEED_OWNER_EMAIL, []))
		self.assertTrue(can_manage_invoices("owner@example.com", ["owner@example.com"]))
		self.assertFalse(can_manage_invoices("accounts@example.com", ["owner@example.com"]))
		self.assertFalse(can_manage_invoices("Guest", ["Guest"]))
		self.assertTrue(can_generate_einvoice("boss@example.com", [], ["System Manager"]))
		self.assertFalse(can_generate_einvoice("accounts@example.com", [], ["Accounts User"]))

	def test_delete_and_rename_rules(self):
		self.assertEqual(delete_block("accounts@example.com", [], 0, ""), "Only an Invoice Admin can rename or delete invoices.")
		self.assertEqual(delete_block("Administrator", [], 1, ""), "Cancel this invoice before deleting it.")
		self.assertEqual(delete_block("Administrator", [], 2, "IRN123"), "This invoice has an IRN. Cancel the e-invoice before deleting it.")
		self.assertIsNone(delete_block("Administrator", [], 2, ""))
		self.assertIsNone(delete_block("Administrator", [], 0, ""))
		self.assertEqual(rename_block("accounts@example.com", [], 0, "because"), "Only an Invoice Admin can rename or delete invoices.")
		self.assertEqual(rename_block("Administrator", [], 1, ""), "Enter a reason for renaming this invoice.")
		self.assertIsNone(rename_block("Administrator", [], 1, "Series was wrong"))
		self.assertIsNone(rename_block("Administrator", [], 0, ""))
		self.assertTrue(needs_gst_warning(1))
		self.assertTrue(needs_gst_warning(2))
		self.assertFalse(needs_gst_warning(0))

	def test_the_owner_email_is_only_seeded_for_a_system_manager(self):
		seeded = seed_admin_names(
			"Administrator",
			{SEED_OWNER_EMAIL: "akash@skgourmetspices.com"},
			{"akash@skgourmetspices.com": ["System Manager", "Sales User"]},
		)
		self.assertEqual(seeded, ["Administrator", "akash@skgourmetspices.com"])
		not_manager = seed_admin_names(
			"Administrator",
			{SEED_OWNER_EMAIL: "akash@skgourmetspices.com"},
			{"akash@skgourmetspices.com": ["Accounts User"]},
		)
		self.assertEqual(not_manager, ["Administrator"])
		self.assertEqual(seed_admin_names("Administrator", {}, {}), ["Administrator"])

	def test_auto_einvoice_flags_are_cleared_and_features_stay(self):
		columns = [
			"enable_e_invoice",
			"enable_e_waybill",
			"auto_generate_e_invoice",
			"auto_generate_e_waybill",
			"generate_e_waybill_with_e_invoice",
			"auto_cancel_e_invoice",
			"api_secret",
			"username",
			"gst_username",
		]
		chosen = auto_fields_to_disable(columns)
		self.assertIn("auto_generate_e_invoice", chosen)
		self.assertIn("auto_generate_e_waybill", chosen)
		self.assertIn("generate_e_waybill_with_e_invoice", chosen)
		self.assertIn("auto_cancel_e_invoice", chosen)
		self.assertNotIn("enable_e_invoice", chosen)
		self.assertNotIn("enable_e_waybill", chosen)
		self.assertNotIn("api_secret", chosen)
		self.assertNotIn("username", chosen)

	def test_settings_hooks_and_the_form_script(self):
		settings = json.loads(
			(PACKAGE / "melliflous_branding" / "doctype" / "melliflous_settings" / "melliflous_settings.json").read_text()
		)
		fields = {row["fieldname"]: row for row in settings["fields"]}
		self.assertEqual(fields["invoice_admin_users"]["options"], "Invoice Admin User")
		self.assertEqual(fields["allow_auto_einvoice"]["default"], "0")
		self.assertEqual(fields["allow_auto_einvoice"]["label"], "Allow auto e-Invoice/e-Way Bill")
		log = json.loads(
			(PACKAGE / "melliflous_branding" / "doctype" / "invoice_audit_log" / "invoice_audit_log.json").read_text()
		)
		self.assertTrue(
			{"action", "old_name", "new_name", "party", "grand_total", "posting_date", "reason", "user", "timestamp"}
			<= {row["fieldname"] for row in log["fields"]}
		)
		hooks = (PACKAGE / "hooks.py").read_text()
		self.assertIn("invoice_admin_records.guard_delete", hooks)
		self.assertIn("invoice_admin_records.guard_rename", hooks)
		self.assertIn("public/js/invoice_admin.js", hooks)
		self.assertIn("melliflous_branding.patches.v0_9.ensure_invoice_admin", (PACKAGE / "patches.txt").read_text())
		self.assertIn("ensure_invoice_admin", (PACKAGE / "install.py").read_text())
		self.assertIn("apply_invoice_boot", (PACKAGE / "boot.py").read_text())
		script = (PACKAGE / "public" / "js" / "invoice_admin.js").read_text()
		self.assertIn("GSTR-1", script)
		self.assertIn("Generate e-Invoice", script)
		self.assertIn("Generate e-Waybill", script)
		self.assertIn("rename_invoice", script)
		self.assertIn("This invoice has an IRN", script)
		records = (PACKAGE / "invoice_admin_records.py").read_text()
		self.assertIn("keep_einvoice_manual", records)
		self.assertIn("allow_rename", records)
		self.assertIn(SEED_OWNER_EMAIL, (PACKAGE / "invoice_admin.py").read_text())
		self.assertNotIn("api_secret", records)


if __name__ == "__main__":
	unittest.main()
