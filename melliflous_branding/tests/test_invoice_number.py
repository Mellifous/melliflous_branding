# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import json
import unittest
from datetime import date
from pathlib import Path

from melliflous_branding.invoice_number import (
	INVOICE_NO_FIELD,
	conflicting_property_setters,
	duplicate_message,
	format_problem,
	invoice_number_field_visibility,
	plan_invoice,
	series_prefix,
	validate_series_settings,
)

PACKAGE = Path(__file__).resolve().parents[1]
PREFIX = "MIMT/"


def row(name, posting_date, docstatus):
	return {"name": name, "posting_date": posting_date, "docstatus": docstatus}


class TestInvoiceNumber(unittest.TestCase):
	def test_gst_shape_and_the_duplicate_sentence(self):
		self.assertIsNone(format_problem("MIMT/26-27/0042"))
		self.assertIsNone(format_problem("A/B-1"))
		self.assertIn("16 characters", format_problem("A" * 17))
		self.assertIn("letters, numbers", format_problem("MIMT 0001"))
		self.assertIn("letters, numbers", format_problem("MIMT_0001"))
		self.assertIn("serial at the end", format_problem("MIMT/26-27/"))
		self.assertEqual(
			duplicate_message("MIMT/0005", "MIMT/0006"),
			"Invoice no MIMT/0005 is already used. Please change it (next free number: MIMT/0006).",
		)

	def test_next_serial_includes_drafts_cancelled_and_a_typed_number(self):
		rows = [
			row("MIMT/0005", "2026-11-01", 0),
			row("MIMT/0009", "2026-11-20", 1),
			row("MIMT/0007", "2026-11-15", 2),
			row("SK/9999", "2026-11-01", 1),
		]
		backdated = plan_invoice(PREFIX, rows, "2026-11-10")
		self.assertEqual(backdated["suggested"], "MIMT/0006")
		self.assertIsNone(backdated["warning"])
		latest = plan_invoice(PREFIX, rows, "2026-11-21")
		self.assertEqual(latest["suggested"], "MIMT/0010")
		typed = plan_invoice(PREFIX, [row("MIMT/0500", "2026-11-01", 1)], "2026-11-02")
		self.assertEqual(typed["suggested"], "MIMT/0501")
		again = plan_invoice(PREFIX, [row("MIMT/00008", "2026-11-01", 1)], "2026-11-02")
		self.assertEqual(again["suggested"], "MIMT/00009")

	def test_starting_number_and_the_naming_series_default(self):
		fresh = plan_invoice(PREFIX, [], "2026-11-27", starting_number=151, digits=4)
		self.assertEqual(fresh["suggested"], "MIMT/0151")
		higher = plan_invoice(
			PREFIX,
			[row("MIMT/0500", "2026-11-01", 1)],
			"2026-11-02",
			starting_number=151,
		)
		self.assertEqual(higher["suggested"], "MIMT/0501")
		prefix, digits = series_prefix("ACC-SINV-.YYYY.-", date(2026, 11, 27))
		self.assertEqual((prefix, digits), ("ACC-SINV-2026-", 5))
		fitted = plan_invoice(prefix, [], date(2026, 11, 27), digits=digits)
		self.assertEqual(fitted["suggested"], "ACC-SINV-2026-01")
		self.assertEqual(len(fitted["suggested"]), 16)
		self.assertEqual(validate_series_settings([
			{"company": "Melliflous", "prefix": "MIMT/26-27/", "starting_number": 151},
			{"company": "Foods", "prefix": "", "starting_number": 0},
		]), [])
		problems = validate_series_settings([
			{"company": "Melliflous", "prefix": "MIMT/26-27/", "starting_number": 1},
			{"company": "Melliflous", "prefix": "X/", "starting_number": 1},
		])
		self.assertTrue(any("listed twice" in problem for problem in problems))
		self.assertTrue(validate_series_settings([{"company": "Melliflous", "prefix": "/BAD", "starting_number": 1}]))

	def test_posting_date_order_and_cancelled_invoices(self):
		later = plan_invoice(PREFIX, [row("MIMT/0010", "2026-11-10", 1)], "2026-11-01", chosen="MIMT/0020")
		self.assertEqual(
			later["error"],
			"Invoice no MIMT/0020 on 01-11-2026 is out of order: "
			"invoice MIMT/0010 dated 10-11-2026 already uses a lower number. "
			"Please choose a number between MIMT/0001 and MIMT/0009 or change the date.",
		)
		earlier = plan_invoice(PREFIX, [row("MIMT/0020", "2026-11-01", 1)], "2026-11-20", chosen="MIMT/0010")
		self.assertEqual(
			earlier["error"],
			"Invoice no MIMT/0010 on 20-11-2026 is out of order: "
			"invoice MIMT/0020 dated 01-11-2026 already uses a higher number. "
			"Please choose a number from MIMT/0021 upwards or change the date.",
		)
		same_day = plan_invoice(PREFIX, [row("MIMT/0010", "2026-11-01", 1)], "2026-11-01", chosen="MIMT/0003")
		self.assertIsNone(same_day["error"])
		gap = plan_invoice(
			PREFIX,
			[row("MIMT/0010", "2026-11-01", 1), row("MIMT/0020", "2026-11-20", 1)],
			"2026-11-10",
			chosen="MIMT/0015",
		)
		self.assertIsNone(gap["error"])
		self.assertEqual(
			plan_invoice(
				PREFIX,
				[row("MIMT/0010", "2026-11-01", 1), row("MIMT/0020", "2026-11-20", 1)],
				"2026-11-10",
			)["suggested"],
			"MIMT/0011",
		)
		tight = [
			row("MIMT/0010", "2026-11-01", 1),
			row("MIMT/0011", "2026-11-10", 1),
		]
		none = plan_invoice(PREFIX, tight, "2026-11-05")
		self.assertIsNone(none["suggested"])
		self.assertIn("No free invoice number fits 05-11-2026", none["warning"])
		self.assertIn("leave no number between them", none["warning"])
		blocked = plan_invoice(PREFIX, tight, "2026-11-05", chosen="MIMT/0012")
		self.assertIn("already uses a lower number", blocked["error"])
		self.assertIn("No free number fits this date. Please change the date.", blocked["error"])
		before = plan_invoice(PREFIX, [row("MIMT/0010", "2026-11-20", 1)], "2026-11-01")
		self.assertEqual(before["suggested"], "MIMT/0009")
		reused = plan_invoice(
			PREFIX,
			[row("MIMT/0007", "2026-11-15", 2), row("MIMT/0005", "2026-11-01", 0)],
			"2026-11-21",
			chosen="MIMT/0007",
		)
		self.assertEqual(
			reused["error"],
			"Invoice no MIMT/0007 is already used. Please change it (next free number: MIMT/0008).",
		)
		# A cancelled invoice does not force a later date to sit above it.
		after_cancel = plan_invoice(PREFIX, [row("MIMT/0050", "2026-11-01", 2)], "2026-11-20", chosen="MIMT/0040")
		self.assertIsNone(after_cancel["error"])
		self.assertEqual(
			plan_invoice(PREFIX, [row("MIMT/0050", "2026-11-01", 2)], "2026-11-20")["suggested"],
			"MIMT/0051",
		)
		# A deleted number is offered again, lowest free gap first, even when it is not the highest.
		reused_gap = plan_invoice(
			PREFIX,
			[row("MIMT/0004", "2026-11-20", 1)],
			"2026-11-05",
			deleted=["MIMT/0003", "MIMT/0001"],
		)
		self.assertEqual(reused_gap["suggested"], "MIMT/0001")
		self.assertIsNone(reused_gap["warning"])
		consumed = plan_invoice(
			PREFIX,
			[row("MIMT/0001", "2026-11-01", 1), row("MIMT/0004", "2026-11-20", 1)],
			"2026-11-10",
			deleted=["MIMT/0001", "MIMT/0003"],
		)
		self.assertEqual(consumed["suggested"], "MIMT/0003")
		self.assertIsNone(consumed["warning"])
		# The gap is a lower number than an earlier invoice, so it is not reused.
		out_of_order = plan_invoice(
			PREFIX,
			[row("MIMT/0001", "2026-11-01", 1), row("MIMT/0004", "2026-11-10", 1)],
			"2026-11-20",
			deleted=["MIMT/0002"],
		)
		self.assertEqual(out_of_order["suggested"], "MIMT/0005")
		self.assertIn("Deleted invoice number MIMT/0002 is free", out_of_order["warning"])
		self.assertIn("MIMT/0004", out_of_order["warning"])
		self.assertIn("The next number MIMT/0005 is suggested instead.", out_of_order["warning"])
		between = plan_invoice(
			PREFIX,
			[row("MIMT/0001", "2026-11-01", 1), row("MIMT/0004", "2026-11-10", 1)],
			"2026-11-05",
			deleted=["MIMT/0002"],
		)
		self.assertEqual(between["suggested"], "MIMT/0002")
		self.assertIsNone(between["warning"])
		# A draft does.
		draft_blocks = plan_invoice(PREFIX, [row("MIMT/0010", "2026-11-20", 0)], "2026-11-01", chosen="MIMT/0011")
		self.assertIn("lower number", draft_blocks["error"])
		own = plan_invoice(
			PREFIX,
			[row("MIMT/0010", "2026-11-01", 0)],
			"2026-11-01",
			current_name="MIMT/0010",
			chosen="MIMT/0010",
		)
		self.assertIsNone(own["error"])

	def test_the_field_hooks_and_the_form_script(self):
		fixture = json.loads((PACKAGE / "fixtures" / "custom_field.json").read_text())
		saved = next(row for row in fixture if row["name"] == "Sales Invoice-custom_invoice_no")
		self.assertEqual(saved["fieldname"], INVOICE_NO_FIELD["fieldname"])
		self.assertEqual(saved["insert_after"], "customer_section")
		self.assertEqual(saved["length"], 16)
		self.assertEqual(saved["label"], "Invoice No")
		hooks = (PACKAGE / "hooks.py").read_text()
		self.assertIn("hsn_records.validate_document", hooks)
		self.assertIn("recipe_records.guard_recipe_stock", hooks)
		self.assertIn("invoice_number_records.assign_invoice_number", hooks)
		self.assertIn("invoice_number_records.validate_invoice_number", hooks)
		self.assertIn("invoice_number_records.sync_invoice_number", hooks)
		self.assertIn("public/js/invoice_number.js", hooks)
		self.assertIn("Sales Invoice-custom_invoice_no", hooks)
		self.assertIn("melliflous_branding.patches.v0_12.ensure_invoice_numbers", (PACKAGE / "patches.txt").read_text())
		self.assertIn("ensure_invoice_numbers", (PACKAGE / "install.py").read_text())
		self.assertEqual((PACKAGE / "__init__.py").read_text().strip(), '__version__ = "0.8.6"')
		self.assertIn("melliflous_branding.patches.v0_13.show_invoice_number", (PACKAGE / "patches.txt").read_text())
		records = (PACKAGE / "invoice_number_records.py").read_text()
		self.assertIn("for update", records)
		self.assertIn("tabSales Invoice", records)
		self.assertIn("_deleted_numbers", records)
		self.assertIn("Invoice Deletion Log", records)
		self.assertNotIn("docstatus=", records)
		self.assertIn("melliflous_invoice_no_edit", (PACKAGE / "invoice_admin_records.py").read_text())
		script = (PACKAGE / "public" / "js" / "invoice_number.js").read_text()
		self.assertIn("suggest_invoice_no", script)
		self.assertIn("check_invoice_no", script)
		self.assertIn("posting_date", script)
		self.assertIn("melliflous-invoice-no", script)
		settings = json.loads(
			(PACKAGE / "melliflous_branding" / "doctype" / "melliflous_settings" / "melliflous_settings.json").read_text()
		)
		fields = {row["fieldname"]: row for row in settings["fields"]}
		self.assertEqual(fields["sales_invoice_series"]["options"], "Sales Invoice Series")
		series = json.loads(
			(
				PACKAGE / "melliflous_branding" / "doctype" / "sales_invoice_series" / "sales_invoice_series.json"
			).read_text()
		)
		self.assertEqual({row["fieldname"] for row in series["fields"]}, {"company", "prefix", "starting_number"})
		self.assertIn("151", series["fields"][2]["description"])

	def test_invoice_no_stays_visible_when_no_prefix_is_configured(self):
		shown = invoice_number_field_visibility()
		self.assertEqual(shown["hidden"], 0)
		self.assertEqual(shown["read_only"], 0)
		self.assertEqual(shown["depends_on"], "")
		self.assertEqual(shown["insert_after"], "customer_section")
		self.assertEqual(INVOICE_NO_FIELD["hidden"], 0)
		fixture = json.loads((PACKAGE / "fixtures" / "custom_field.json").read_text())
		saved = next(row for row in fixture if row["name"] == "Sales Invoice-custom_invoice_no")
		self.assertEqual(saved["hidden"], 0)
		removed = conflicting_property_setters(
			[
				{
					"name": "Sales Invoice-custom_invoice_no-hidden",
					"doc_type": "Sales Invoice",
					"field_name": "custom_invoice_no",
					"property": "hidden",
					"value": "1",
				},
				{
					"name": "Sales Invoice-custom_invoice_no-depends_on",
					"doc_type": "Sales Invoice",
					"field_name": "custom_invoice_no",
					"property": "depends_on",
					"value": "eval:doc.company",
				},
				{
					"name": "Sales Invoice-customer-hidden",
					"doc_type": "Sales Invoice",
					"field_name": "customer",
					"property": "hidden",
					"value": "1",
				},
				{
					"name": "Customer-custom_invoice_no-hidden",
					"doc_type": "Customer",
					"field_name": "custom_invoice_no",
					"property": "hidden",
					"value": "1",
				},
			]
		)
		self.assertEqual(
			removed,
			[
				"Sales Invoice-custom_invoice_no-hidden",
				"Sales Invoice-custom_invoice_no-depends_on",
			],
		)
		script = (PACKAGE / "public" / "js" / "invoice_number.js").read_text()
		self.assertNotIn('.form-page").first().find(".section-body").first()', script)
		self.assertIn("empty section", script)
		self.assertIn('frm.get_field("company")', script)
		self.assertIn('frm.set_df_property("custom_invoice_no", "hidden", 0)', script)
		records = (PACKAGE / "invoice_number_records.py").read_text()
		self.assertIn("def show_invoice_number_field", records)
		self.assertIn("conflicting_property_setters", records)
		# No saved prefix still uses the Sales Invoice series, so the field is not withheld.
		fallback = series_prefix("ACC-SINV-.YYYY.-", date(2026, 11, 27))
		self.assertEqual(fallback[0], "ACC-SINV-2026-")


if __name__ == "__main__":
	unittest.main()
