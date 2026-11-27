# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import json
import unittest
from datetime import date, timedelta
from pathlib import Path

from melliflous_branding.customer_compliance import (
	CUSTOMER_CUSTOM_FIELDS,
	ComplianceError,
	block_message,
	clean_document,
	expiry_tone,
	plan_billing,
	present_documents,
	selling_party,
)
from melliflous_branding.distributors import build_history, history_window

PACKAGE = Path(__file__).resolve().parents[1]
TODAY = date(2026, 11, 27)


class TestDocuments(unittest.TestCase):
	def test_aadhaar_keeps_the_file_and_drops_the_number(self):
		with self.assertRaises(ComplianceError):
			clean_document({"document_type": "Aadhaar", "attach": "/files/mask.pdf", "document_no": "1234"})
		cleaned = clean_document({"document_type": "Aadhaar", "attach": "/files/mask.pdf", "document_no": ""})
		self.assertEqual(cleaned["document_no"], "")
		self.assertEqual(cleaned["attach"], "/files/mask.pdf")

	def test_expiry_is_red_then_amber_then_green(self):
		self.assertEqual(expiry_tone(None, TODAY), "neutral")
		self.assertEqual(expiry_tone(TODAY - timedelta(days=1), TODAY), "red")
		self.assertEqual(expiry_tone(TODAY, TODAY), "amber")
		self.assertEqual(expiry_tone(TODAY + timedelta(days=29), TODAY), "amber")
		self.assertEqual(expiry_tone(TODAY + timedelta(days=30), TODAY), "green")
		rows = present_documents(
			[
				{"document_type": "FSSAI Licence", "attach": "/files/f.pdf", "valid_till": "2026-10-01"},
				{"document_type": "GST Certificate", "attach": "/files/g.pdf", "valid_till": "2026-12-10"},
			],
			TODAY,
		)
		self.assertEqual(rows[0]["tone"], "red")
		self.assertEqual(rows[1]["tone"], "amber")

	def test_fields_are_a_fixture_and_the_page_can_upload(self):
		names = {row["fieldname"] for row in CUSTOMER_CUSTOM_FIELDS}
		self.assertIn("custom_billing_status", names)
		self.assertIn("custom_customer_documents", names)
		fixture = json.loads((PACKAGE / "fixtures" / "custom_field.json").read_text())
		customer_rows = [row for row in fixture if row.get("dt") == "Customer"]
		self.assertEqual({row["fieldname"] for row in customer_rows}, names)
		child = json.loads(
			(PACKAGE / "melliflous_branding" / "doctype" / "customer_document" / "customer_document.json").read_text()
		)
		self.assertEqual(child["istable"], 1)
		options = next(row["options"] for row in child["fields"] if row["fieldname"] == "document_type")
		self.assertIn("Aadhaar", options)
		self.assertNotIn("document_no", {row["fieldname"] for row in child["fields"] if row.get("reqd")})
		script = (PACKAGE / "melliflous_branding" / "page" / "distributor_360" / "distributor_360.js").read_text()
		self.assertIn("add_customer_document", script)
		self.assertIn("Upload", script)
		self.assertIn("custom_billing_status", (PACKAGE / "public" / "js" / "customer_list.js").read_text())


class TestBillingBlock(unittest.TestCase):
	def test_a_reason_is_required_and_there_is_no_override(self):
		with self.assertRaises(ComplianceError):
			plan_billing("Active", "", "Blocked", "", "boss@example.com", TODAY)
		planned = plan_billing("Active", "", "Blacklisted", "Overdue 90 days", "boss@example.com", TODAY)
		self.assertEqual(planned["status"], "Blacklisted")
		self.assertIn("Blacklisted", planned["comment"])
		self.assertEqual(planned["blocked_by"], "boss@example.com")
		cleared = plan_billing("Blocked", "Overdue", "Active", "Overdue", "boss@example.com", TODAY)
		self.assertEqual(cleared["reason"], "")
		self.assertIn("Active", cleared["comment"])
		self.assertIsNone(block_message("AJ Traders", "Active", "saving this Sales Invoice"))
		message = block_message("AJ Traders", "Blocked", "saving this Sales Invoice")
		self.assertIn("Unblock the customer", message)
		self.assertNotIn("Allow once", message)
		self.assertEqual(selling_party("Quotation", "Lead", "LEAD-1", ""), "")
		self.assertEqual(selling_party("Quotation", "Customer", "AJ Traders", ""), "AJ Traders")
		self.assertEqual(selling_party("Delivery Note", "", "", "AJ Traders"), "AJ Traders")
		records = (PACKAGE / "customer_records.py").read_text()
		self.assertIn("def block_selling", records)
		self.assertNotIn("Allow once", records)
		invoice = (PACKAGE / "melliflous_branding" / "page" / "quick_invoice" / "quick_invoice.js").read_text()
		self.assertIn("block_message", invoice)


class TestDistributorHistory(unittest.TestCase):
	def test_ranges_and_the_history_sections(self):
		self.assertEqual(history_window("12M", TODAY)["preset"], "12M")
		self.assertEqual(history_window("This month", TODAY)["start"], date(2026, 11, 1))
		self.assertEqual(history_window("FY", TODAY, 4)["start"], date(2026, 4, 1))
		self.assertIsNone(history_window("All", TODAY)["start"])
		self.assertEqual(history_window("nope", TODAY)["preset"], "12M")
		built = build_history(
			{
				"invoices": [
					{"name": "SI-1", "posting_date": "2026-11-10", "docstatus": 1, "is_return": 0, "net": 1000, "tax": 50, "grand": 1050, "outstanding": 100},
					{"name": "SI-OLD", "posting_date": "2024-01-02", "docstatus": 1, "is_return": 0, "net": 9000, "tax": 0, "grand": 9000, "outstanding": 0},
					{"name": "CN-1", "posting_date": "2026-11-12", "docstatus": 1, "is_return": 1, "net": -200, "tax": -10, "grand": -210, "outstanding": 0},
					{"name": "SI-D", "posting_date": "2026-11-20", "docstatus": 0, "is_return": 0, "net": 400, "tax": 20, "grand": 420, "outstanding": 0},
				],
				"complaints": [
					{"name": "DC-1", "complaint_date": "2026-11-01", "complaint_type": "Quality", "status": "Open"},
					{"name": "DC-2", "complaint_date": "2026-11-02", "complaint_type": "Damage", "status": "Resolved"},
				],
				"quotations": [
					{"name": "QTN-1", "transaction_date": "2026-11-03", "status": "Ordered", "docstatus": 1, "amount": 500},
					{"name": "QTN-2", "transaction_date": "2026-11-04", "status": "Open", "docstatus": 1, "amount": 300},
					{"name": "QTN-X", "transaction_date": "2026-11-05", "status": "Cancelled", "docstatus": 2, "amount": 999},
				],
				"benefits": [
					{"name": "DB-1", "benefit_date": "2026-11-06", "benefit_type": "Gift", "status": "Given", "value": 80, "description": "Hamper"},
					{"name": "DB-2", "benefit_date": "2026-11-07", "benefit_type": "Incentive", "status": "Planned", "value": 20},
				],
				"item_lines": [
					{"item": "Turmeric", "item_name": "Turmeric", "posting_date": "2026-11-10", "qty": 10, "amount": 800, "rate": 80, "name": "SI-1"},
					{"item": "Turmeric", "item_name": "Turmeric", "posting_date": "2026-10-10", "qty": 4, "amount": 400, "rate": 100, "name": "SI-0"},
					{"item": "Chilli", "item_name": "Chilli", "posting_date": "2026-11-11", "qty": 2, "amount": 200, "rate": 100, "name": "SI-2"},
				],
				"price_rows": [
					{"item": "Turmeric", "price_list": "Classic Distributor", "rate": 90},
					{"item": "Turmeric", "price_list": "Standard Selling", "rate": 110},
					{"item": "Chilli", "price_list": "Classic Distributor", "rate": 80},
				],
			},
			TODAY,
			"12M",
		)
		self.assertEqual(built["billing"]["net"], 1000)
		self.assertEqual(built["billing"]["tax"], 50)
		self.assertEqual(len(built["billing"]["drafts"]), 1)
		self.assertEqual(built["billing"]["drafts"][0]["name"], "SI-D")
		self.assertEqual(built["credit_notes"]["count"], 1)
		self.assertEqual(built["credit_notes"]["net"], 200)
		self.assertEqual(built["complaints"]["open"], 1)
		self.assertEqual(next(row["tone"] for row in built["complaints"]["rows"] if row["name"] == "DC-1"), "red")
		self.assertEqual(built["quotations"]["ordered"], 1)
		self.assertEqual(built["quotations"]["count"], 2)
		self.assertEqual(built["quotations"]["conversion"], 50)
		self.assertEqual(built["benefits"]["given"], 80)
		self.assertEqual(built["benefits"]["primary"], 800)
		self.assertEqual(built["benefits"]["roi"], 10)
		self.assertEqual(built["most_bought"]["by_qty"][0]["item"], "Turmeric")
		self.assertEqual(built["most_bought"]["by_qty"][0]["share"], 87.5)
		prices = {row["item"]: row for row in built["prices"]}
		self.assertEqual(prices["Turmeric"]["min"], 80)
		self.assertEqual(prices["Turmeric"]["max"], 100)
		self.assertEqual(prices["Turmeric"]["last"], 80)
		self.assertTrue(prices["Turmeric"]["below_distributor"])
		self.assertFalse(prices["Chilli"]["below_distributor"])
		self.assertEqual(prices["Turmeric"]["lists"]["Standard Selling"], 110)
		wide = build_history(
			{"invoices": [{"name": "SI-OLD", "posting_date": "2024-01-02", "docstatus": 1, "net": 5, "tax": 0, "grand": 5, "outstanding": 0}]},
			TODAY,
			"All",
		)
		self.assertEqual(wide["billing"]["invoices"][0]["name"], "SI-OLD")
		script = (PACKAGE / "melliflous_branding" / "page" / "distributor_360" / "distributor_360.js").read_text()
		self.assertIn("Historic billing", script)
		self.assertIn("New Gift/Incentive", script)
		self.assertIn("item-sales.csv", script)
		self.assertIn("Classic Distributor", script)
		self.assertIn("history_preset", script)
		benefit = json.loads(
			(PACKAGE / "melliflous_branding" / "doctype" / "distributor_benefit" / "distributor_benefit.json").read_text()
		)
		self.assertEqual(
			{row["fieldname"] for row in benefit["fields"]}
			& {"distributor", "benefit_date", "benefit_type", "description", "item", "qty", "value", "status", "attachment"},
			{"distributor", "benefit_date", "benefit_type", "description", "item", "qty", "value", "status", "attachment"},
		)


if __name__ == "__main__":
	unittest.main()
