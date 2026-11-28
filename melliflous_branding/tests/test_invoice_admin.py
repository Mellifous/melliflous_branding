# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import json
import unittest
from pathlib import Path

from melliflous_branding.invoice_admin import (
	DELETE_NEEDS_REASON,
	SEED_OWNER_EMAIL,
	auto_fields_to_disable,
	can_delete_invoices,
	can_generate_einvoice,
	can_manage_invoices,
	delete_block,
	delete_permission_updates,
	deletion_log_block,
	deletion_log_entry,
	needs_gst_warning,
	rename_block,
	seed_admin_names,
	with_deletion_log_shortcut,
)
from melliflous_branding.invoice_number import plan_invoice

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
		roles = ["Invoice Admin", "Accounts Manager", "System Manager"]
		self.assertFalse(can_delete_invoices(SEED_OWNER_EMAIL, [], roles))
		self.assertEqual(
			delete_block(SEED_OWNER_EMAIL, [], 0, "", roles, reason="Duplicate", require_reason=True),
			"Only an Invoice Admin can rename or delete invoices.",
		)
		self.assertTrue(can_delete_invoices(SEED_OWNER_EMAIL, [SEED_OWNER_EMAIL], []))
		self.assertIsNone(
			delete_block(SEED_OWNER_EMAIL, [SEED_OWNER_EMAIL], 0, "", reason="Duplicate", require_reason=True)
		)
		self.assertIsNone(
			delete_block(SEED_OWNER_EMAIL, [SEED_OWNER_EMAIL], 2, "", reason="Cancelled in error", require_reason=True)
		)
		self.assertEqual(
			delete_block(SEED_OWNER_EMAIL, [SEED_OWNER_EMAIL], 1, "", reason="Too late", require_reason=True),
			"Cancel this invoice before deleting it.",
		)
		self.assertEqual(
			delete_block("Administrator", [], 0, "", reason="  ", require_reason=True),
			DELETE_NEEDS_REASON,
		)
		self.assertFalse(can_delete_invoices("sales@example.com", [], ["Sales User", "Accounts User"]))
		self.assertEqual(
			delete_block("sales@example.com", [], 2, "", ["Sales User"], reason="No", require_reason=True),
			"Only an Invoice Admin can rename or delete invoices.",
		)
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
		self.assertIn("melliflous_can_delete_invoice", records)
		self.assertIn("delete_sales_invoices", records)
		self.assertIn("revoke_sales_invoice_delete", records)
		self.assertIn("DELETION_LOG_DOCTYPE", records)
		script = (PACKAGE / "public" / "js" / "invoice_admin.js").read_text()
		self.assertIn("Reason for deletion", script)
		self.assertIn("delete_sales_invoices", script)
		self.assertIn("hideDelete", script)
		self.assertNotIn("melliflous_can_delete_invoice", script)
		listing = (PACKAGE / "public" / "js" / "invoice_admin_list.js").read_text()
		self.assertIn("Reason for deletion", listing)
		self.assertIn("melliflous_invoice_admin", listing)
		self.assertIn("invoice_admin_list.js", (PACKAGE / "hooks.py").read_text())
		self.assertIn(
			"melliflous_branding.patches.v0_14.restrict_sales_invoice_delete",
			(PACKAGE / "patches.txt").read_text(),
		)
		log = json.loads(
			(PACKAGE / "melliflous_branding" / "doctype" / "invoice_deletion_log" / "invoice_deletion_log.json").read_text()
		)
		self.assertEqual(log["name"], "Invoice Deletion Log")
		perms = {row["role"]: row for row in log["permissions"]}
		for role in ("System Manager", "Accounts Manager", "Invoice Admin"):
			self.assertEqual(perms[role]["read"], 1)
			self.assertEqual(perms[role]["write"], 0)
			self.assertEqual(perms[role]["delete"], 0)
		turned_off = delete_permission_updates(
			[
				{"name": "perm-admin", "role": "Invoice Admin", "permlevel": 0, "delete": 1},
				{"name": "perm-accounts", "role": "Accounts Manager", "permlevel": 0, "delete": 1},
				{"name": "perm-system", "role": "System Manager", "permlevel": 0, "delete": 1},
				{"name": "perm-sales", "role": "Sales User", "permlevel": 0, "delete": 1},
				{"name": "perm-level1", "role": "Accounts Manager", "permlevel": 1, "delete": 1},
			],
			"Sales Invoice",
		)
		self.assertEqual(
			turned_off,
			[
				{"name": "perm-admin", "delete": 0},
				{"name": "perm-accounts", "delete": 0},
				{"name": "perm-system", "delete": 0},
				{"name": "perm-sales", "delete": 0},
			],
		)
		purchase = delete_permission_updates(
			[
				{"name": "perm-admin", "role": "Invoice Admin", "permlevel": 0, "delete": 1},
				{"name": "perm-accounts", "role": "Accounts Manager", "permlevel": 0, "delete": 1},
			],
			"Purchase Invoice",
		)
		self.assertEqual(purchase, [{"name": "perm-accounts", "delete": 0}])
		entry = deletion_log_entry(
			"MIMT00001",
			"MIMT00001",
			"Melliflous",
			"Hotel",
			"2026-11-01",
			1500,
			2,
			"Raised in error",
			SEED_OWNER_EMAIL,
			"2026-11-28 02:20:00",
		)
		self.assertEqual(entry["status"], "Cancelled")
		self.assertEqual(entry["reason"], "Raised in error")
		self.assertEqual(entry["invoice_no"], "MIMT00001")
		self.assertIsNone(deletion_log_block("Administrator", is_new=False, deleting=True))
		self.assertIsNone(deletion_log_block(SEED_OWNER_EMAIL, is_new=True))
		self.assertEqual(
			deletion_log_block(SEED_OWNER_EMAIL, is_new=False, deleting=True),
			"Only Administrator can change an invoice deletion log.",
		)
		shortcuts = with_deletion_log_shortcut([{"label": "Sales Invoice", "link_to": "Sales Invoice"}])
		self.assertEqual(shortcuts[-1]["label"], "Invoice Deletion Log")
		self.assertEqual(len(with_deletion_log_shortcut(shortcuts)), len(shortcuts))
		# Without a deletion log, the next number is still one past the highest stored.
		# A cancelled invoice stays in the table, so its number stays taken.
		self.assertEqual(
			plan_invoice("MIMT/", [{"name": "MIMT/0002", "posting_date": "2026-11-02", "docstatus": 1}], "2026-11-03")[
				"suggested"
			],
			"MIMT/0003",
		)
		self.assertEqual(
			plan_invoice("MIMT/", [{"name": "MIMT/0001", "posting_date": "2026-11-01", "docstatus": 2}], "2026-11-03")[
				"suggested"
			],
			"MIMT/0002",
		)


if __name__ == "__main__":
	unittest.main()
