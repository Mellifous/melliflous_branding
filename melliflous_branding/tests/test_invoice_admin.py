# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import json
import unittest
from pathlib import Path

from melliflous_branding.cancelled_ledger import ledger_rows_to_remove, live_link_message, uncleared_ledger_message
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
	payment_delete_block,
	rename_block,
	invoice_admin_row_plan,
	role_keeps_invoice_delete,
	sales_invoice_menu_shows_delete,
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

	def test_the_owner_is_seeded_when_the_user_exists(self):
		roles = ["System Manager", "Accounts Manager", "Invoice Admin"]
		seeded = seed_admin_names(
			"Administrator",
			{SEED_OWNER_EMAIL: "akash@skgourmetspices.com"},
			{"akash@skgourmetspices.com": roles},
		)
		self.assertEqual(seeded, ["Administrator", "akash@skgourmetspices.com"])
		# A migrate that cannot see System Manager still puts the User on the list.
		without_roles = seed_admin_names(
			"Administrator",
			{SEED_OWNER_EMAIL: "akash@skgourmetspices.com"},
			{},
		)
		self.assertEqual(without_roles, ["Administrator", "akash@skgourmetspices.com"])
		self.assertEqual(seed_admin_names("Administrator", {}, {}), ["Administrator"])

	def test_invoice_admin_rows_are_deduped_and_adding_akash_is_idempotent(self):
		rows = []
		for index in range(10):
			rows.append({"name": f"admin-{index}", "user": "Administrator", "idx": index * 2 + 1})
			rows.append({"name": f"akash-{index}", "user": SEED_OWNER_EMAIL, "idx": index * 2 + 2})
		rows.append({"name": "blank", "user": "  ", "idx": 99})
		required = ["Administrator", SEED_OWNER_EMAIL]
		plan = invoice_admin_row_plan(rows, required)
		self.assertEqual(plan["keep"], ["Administrator", SEED_OWNER_EMAIL])
		self.assertEqual(plan["add"], [])
		self.assertEqual(len(plan["delete"]), 19)
		self.assertIn("blank", plan["delete"])
		self.assertIn("admin-1", plan["delete"])
		again = invoice_admin_row_plan(
			[
				{"name": "admin-0", "user": "Administrator", "idx": 1},
				{"name": "akash-0", "user": SEED_OWNER_EMAIL, "idx": 2},
			],
			required,
		)
		self.assertEqual(again["delete"], [])
		self.assertEqual(again["add"], [])
		missing = invoice_admin_row_plan(
			[{"name": "admin-0", "user": "Administrator", "idx": 1}],
			required,
		)
		self.assertEqual(missing["add"], [SEED_OWNER_EMAIL])
		self.assertEqual(missing["delete"], [])

	def test_cancelled_invoice_ledger_rows_are_removed_and_a_live_payment_blocks(self):
		invoice = "MIMT00001"
		rows = [
			{
				"doctype": "Payment Ledger Entry",
				"name": "PLE-original",
				"voucher_type": "Sales Invoice",
				"voucher_no": invoice,
				"against_voucher_type": "Sales Invoice",
				"against_voucher_no": invoice,
				"delinked": 1,
			},
			{
				"doctype": "Payment Ledger Entry",
				"name": "PLE-reversal",
				"voucher_type": "Sales Invoice",
				"voucher_no": invoice,
				"against_voucher_type": "Sales Invoice",
				"against_voucher_no": invoice,
				"delinked": 1,
			},
			{
				"doctype": "GL Entry",
				"name": "GLE-cancel",
				"voucher_type": "Sales Invoice",
				"voucher_no": invoice,
				"is_cancelled": 1,
			},
			{
				"doctype": "Stock Ledger Entry",
				"name": "SLE-cancel",
				"voucher_type": "Sales Invoice",
				"voucher_no": invoice,
				"is_cancelled": 1,
			},
			{
				"doctype": "Advance Payment Ledger Entry",
				"name": "ADV-1",
				"voucher_type": "Sales Invoice",
				"voucher_no": invoice,
				"delinked": 1,
			},
			{
				"doctype": "Repost Item Valuation",
				"name": "RIV-1",
				"voucher_type": "Sales Invoice",
				"voucher_no": invoice,
				"docstatus": 2,
			},
			{
				"doctype": "Repost Payment Ledger Items",
				"name": "RPL-item",
				"voucher_type": "Sales Invoice",
				"voucher_no": invoice,
			},
		]
		removed = {(row["doctype"], row["name"]) for row in ledger_rows_to_remove("Sales Invoice", invoice, rows)}
		self.assertEqual(
			removed,
			{
				("Payment Ledger Entry", "PLE-original"),
				("Payment Ledger Entry", "PLE-reversal"),
				("GL Entry", "GLE-cancel"),
				("Stock Ledger Entry", "SLE-cancel"),
				("Advance Payment Ledger Entry", "ADV-1"),
				("Repost Item Valuation", "RIV-1"),
				("Repost Payment Ledger Items", "RPL-item"),
			},
		)
		live_ledger = rows + [
			{
				"doctype": "Payment Ledger Entry",
				"name": "PLE-live",
				"voucher_type": "Payment Entry",
				"voucher_no": "PE-0001",
				"against_voucher_type": "Sales Invoice",
				"against_voucher_no": invoice,
				"delinked": 0,
			}
		]
		self.assertNotIn(("Payment Ledger Entry", "PLE-live"), {(row["doctype"], row["name"]) for row in ledger_rows_to_remove("Sales Invoice", invoice, live_ledger)})
		self.assertIn("PLE-live", uncleared_ledger_message("Sales Invoice", invoice, live_ledger))
		self.assertIsNone(uncleared_ledger_message("Sales Invoice", invoice, rows))
		self.assertIn(
			"Payment Entry PE-0001",
			live_link_message(
				"Sales Invoice",
				invoice,
				[{"doctype": "Payment Entry", "name": "PE-0001", "docstatus": 1}],
			),
		)
		self.assertIsNone(
			live_link_message(
				"Sales Invoice",
				invoice,
				[
					{"doctype": "Payment Entry", "name": "PE-0001", "docstatus": 2},
					{"doctype": "Payment Ledger Entry", "name": "PLE-original", "docstatus": 0},
				],
			)
		)
		self.assertIsNone(payment_delete_block("Administrator", [], 2, "Duplicate receipt"))
		self.assertEqual(payment_delete_block("Administrator", [], 1, "Duplicate receipt"), "Cancel this payment before deleting it.")
		self.assertEqual(payment_delete_block(SEED_OWNER_EMAIL, [], 2, "Duplicate receipt"), "Only an Invoice Admin can rename or delete invoices.")

	def test_akash_roles_show_the_menu_and_the_list_allows_the_delete(self):
		"""Akash has System Manager, Accounts Manager, and Invoice Admin.

		The menu is drawn from the Invoice Admin role. The server still refuses
		him until his user name is on the Invoice Admin list, and a cancelled
		invoice still needs a reason.
		"""
		roles = ["System Manager", "Accounts Manager", "Invoice Admin", "Sales User"]
		self.assertTrue(sales_invoice_menu_shows_delete(SEED_OWNER_EMAIL, [], roles, []))
		self.assertFalse(can_delete_invoices(SEED_OWNER_EMAIL, [], roles))
		self.assertEqual(
			delete_block(SEED_OWNER_EMAIL, [], 2, "", roles, reason="Wrong bill", require_reason=True),
			"Only an Invoice Admin can rename or delete invoices.",
		)
		self.assertTrue(sales_invoice_menu_shows_delete(SEED_OWNER_EMAIL, [SEED_OWNER_EMAIL], roles, []))
		self.assertIsNone(
			delete_block(
				SEED_OWNER_EMAIL,
				[SEED_OWNER_EMAIL],
				2,
				"",
				roles,
				reason="Wrong bill",
				require_reason=True,
			)
		)
		self.assertFalse(
			sales_invoice_menu_shows_delete(
				"accounts@example.com",
				[],
				["System Manager", "Accounts Manager"],
				[],
			)
		)
		self.assertTrue(role_keeps_invoice_delete("Invoice Admin", "Sales Invoice"))
		self.assertFalse(role_keeps_invoice_delete("Accounts Manager", "Sales Invoice"))
		self.assertFalse(role_keeps_invoice_delete("System Manager", "Sales Invoice"))
		updates = delete_permission_updates(
			[
				{"name": "perm-admin", "role": "Invoice Admin", "permlevel": 0, "delete": 0},
				{"name": "perm-accounts", "role": "Accounts Manager", "permlevel": 0, "delete": 1},
				{"name": "perm-system", "role": "System Manager", "permlevel": 0, "delete": 1},
			],
			"Sales Invoice",
		)
		self.assertEqual(
			updates,
			[
				{"name": "perm-admin", "delete": 1},
				{"name": "perm-accounts", "delete": 0},
				{"name": "perm-system", "delete": 0},
			],
		)

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
		self.assertIn("may_delete_sales_invoice", records)
		self.assertIn("sync_invoice_admin_list", records)
		self.assertIn("revoke_sales_invoice_delete", records)
		self.assertIn("DELETION_LOG_DOCTYPE", records)
		script = (PACKAGE / "public" / "js" / "invoice_admin.js").read_text()
		self.assertIn("Reason for deletion", script)
		self.assertIn("delete_sales_invoices", script)
		self.assertIn("Delete Invoice", script)
		self.assertIn("may_delete_sales_invoice", script)
		self.assertIn("Delete Payment", script)
		self.assertIn("serverErrorText", script)
		self.assertIn("delete_payment_entries", script)
		self.assertIn('text === "Delete Invoice"', script)
		self.assertIn('text === "Delete"', script)
		self.assertNotIn("melliflous_can_delete_invoice", script)
		listing = (PACKAGE / "public" / "js" / "invoice_admin_list.js").read_text()
		self.assertIn("Reason for deletion", listing)
		self.assertIn("Delete with reason", listing)
		self.assertIn("may_delete_sales_invoice", listing)
		self.assertIn("delete_payment_entries", listing)
		self.assertIn("serverErrorText", listing)
		self.assertIn('doctype_list_js', (PACKAGE / "hooks.py").read_text())
		hooks = (PACKAGE / "hooks.py").read_text()
		self.assertIn('"Payment Entry": "public/js/invoice_admin.js"', hooks)
		self.assertIn('"Payment Entry": "public/js/invoice_admin_list.js"', hooks)
		self.assertGreaterEqual(hooks.count("invoice_admin_records.guard_delete"), 3)
		self.assertNotIn("can_delete = false", listing)
		self.assertNotIn("melliflous_invoice_admin", listing)
		self.assertIn("invoice_admin_list.js", (PACKAGE / "hooks.py").read_text())
		self.assertIn(
			"melliflous_branding.patches.v0_14.restrict_sales_invoice_delete",
			(PACKAGE / "patches.txt").read_text(),
		)
		self.assertIn(
			"melliflous_branding.patches.v0_15.restore_invoice_admin_delete",
			(PACKAGE / "patches.txt").read_text(),
		)
		self.assertIn(
			"melliflous_branding.patches.v0_16.dedupe_invoice_admins",
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
