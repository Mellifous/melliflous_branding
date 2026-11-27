# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import json
import unittest
from datetime import date, timedelta
from pathlib import Path

from melliflous_branding import hooks
from melliflous_branding.distributors import (
	DISTRIBUTOR_LINKS,
	DistributorError,
	achievement_for_month,
	achievement_tone,
	add_months,
	apply_statement_line,
	billing_tone,
	build_dashboard,
	build_distributor_mis,
	can_file,
	can_open_distributor_360,
	can_see_profile,
	clean_complaint,
	clean_days,
	clean_growth,
	clean_visit,
	cover_tone,
	days_of_cover,
	distributor_activity,
	find_duplicate_statement,
	follow_up_rows,
	merge_distributor_workspace,
	mis_rag,
	missing_sidebar_links,
	next_visit_due,
	normalize_lines,
	place_distributor_360_app,
	plan_target_save,
	prefill_rows,
	prepare_profile_values,
	product_pace,
	quote_tone,
	received_by_item,
	recommended_monthly_target,
	statement_period,
	summarize_quotations,
	target_suggestion,
	trailing_months,
	visit_tone,
)

PACKAGE = Path(__file__).resolve().parents[1]
TODAY = date(2026, 11, 27)
SALES = {"user": "priya@example.com", "roles": ["Sales User"], "sales_persons": ["Priya"]}
MANAGER = {"user": "boss@example.com", "roles": ["Sales Manager"], "sales_persons": []}


def profile(**overrides):
	row = {
		"name": "AJ Traders",
		"customer": "AJ Traders",
		"customer_name": "AJ Traders",
		"company": "Melliflous Foods (OPC) Pvt Ltd",
		"account_manager": "priya@example.com",
		"sales_person": "Priya",
		"salesman": "ravi@example.com",
		"territory": "North",
		"area": "Andheri",
		"counters": 40,
		"visit_frequency": "Weekly",
		"last_visit_date": None,
		"next_visit_due": None,
		"is_active": 1,
	}
	row.update(overrides)
	return row


class TestSchedule(unittest.TestCase):
	def test_month_ends_and_the_twelve_month_window(self):
		self.assertEqual(add_months("2026-01-31", 1), date(2026, 2, 28))
		self.assertEqual(add_months("2024-01-31", 1), date(2024, 2, 29))
		self.assertEqual(add_months("2026-03-31", -1), date(2026, 2, 28))
		months = trailing_months(TODAY, 12)
		self.assertEqual(months[0], date(2025, 12, 1))
		self.assertEqual(months[-1], date(2026, 11, 1))
		self.assertEqual(len(months), 12)

	def test_next_visit_follows_the_frequency(self):
		self.assertIsNone(next_visit_due(None, "Weekly", TODAY))
		self.assertEqual(next_visit_due("2026-11-01", "Weekly", TODAY), date(2026, 11, 8))
		self.assertEqual(next_visit_due("2026-11-01", "Fortnightly", TODAY), date(2026, 11, 15))
		self.assertEqual(next_visit_due("2026-01-31", "Monthly", TODAY), date(2026, 2, 28))
		with self.assertRaises(DistributorError):
			next_visit_due("2026-11-01", "Daily", TODAY)

	def test_profile_keeps_an_inactive_tick_and_computes_the_due_date(self):
		saved = prepare_profile_values(
			{"customer": "AJ Traders", "company": "Foods", "visit_frequency": "Weekly", "last_visit_date": "2026-11-01", "is_active": 0, "counters": 3},
			TODAY,
		)
		self.assertEqual(saved["is_active"], 0)
		self.assertEqual(saved["next_visit_due"], date(2026, 11, 8))
		self.assertEqual(saved["counters"], 3)
		with self.assertRaises(DistributorError):
			prepare_profile_values({"customer": "", "company": "Foods"}, TODAY)


class TestStock(unittest.TestCase):
	def test_closing_uses_the_formula_until_it_is_edited(self):
		row = apply_statement_line(
			{"item": "Turmeric", "opening_qty": 10, "secondary_qty": 3, "rate": 20},
			previous_closing=None,
			received_qty=5,
		)
		self.assertEqual(row["closing_qty"], 12)
		self.assertEqual(row["closing_value"], 240)
		self.assertEqual(row["secondary_value"], 60)
		kept = apply_statement_line(
			{"item": "Turmeric", "opening_qty": 10, "secondary_qty": 3, "closing_qty": 9, "closing_edited": 1, "rate": 20},
			previous_closing=None,
			received_qty=5,
		)
		self.assertEqual(kept["closing_qty"], 9)
		self.assertEqual(kept["closing_value"], 180)

	def test_opening_comes_from_last_month_unless_the_row_keeps_it(self):
		copied = apply_statement_line(
			{"item": "Turmeric", "opening_qty": 99, "secondary_qty": 1, "rate": 10},
			previous_closing=8,
			received_qty=-2,
		)
		self.assertEqual(copied["opening_qty"], 8)
		self.assertEqual(copied["primary_qty"], -2)
		self.assertEqual(copied["closing_qty"], 5)
		kept = apply_statement_line(
			{"item": "Turmeric", "opening_qty": 4, "opening_edited": 1, "secondary_qty": 0, "rate": 0},
			previous_closing=8,
			received_qty=0,
		)
		self.assertEqual(kept["opening_qty"], 4)
		self.assertEqual(kept["closing_value"], 0)

	def test_credit_notes_reduce_primary_received(self):
		got = received_by_item(
			[
				{"item": "Turmeric", "qty": 10, "is_return": 0},
				{"item": "Turmeric", "qty": -2, "is_return": 1},
				{"item": "Turmeric", "stock_qty": 1, "is_return": 1},
				{"item": "Chilli", "qty": 4, "is_return": 0},
			]
		)
		self.assertEqual(got["Turmeric"], 7)
		self.assertEqual(got["Chilli"], 4)

	def test_prefill_carries_closing_stock_and_drops_empty_items(self):
		rows = prefill_rows(
			[
				{"item": "Turmeric", "item_name": "Turmeric Powder", "uom": "Kg", "closing_qty": 8, "rate": 20},
				{"item": "Old", "closing_qty": 0, "rate": 5},
			],
			[
				{"item": "Turmeric", "item_name": "Turmeric Powder", "stock_uom": "Kg", "qty": 2, "is_return": 0},
				{"item": "Chilli", "item_name": "Chilli", "qty": 3, "is_return": 0},
			],
		)
		by_item = {row["item"]: row for row in rows}
		self.assertNotIn("Old", by_item)
		self.assertEqual(by_item["Turmeric"]["opening_qty"], 8)
		self.assertEqual(by_item["Turmeric"]["primary_qty"], 2)
		self.assertEqual(by_item["Turmeric"]["closing_qty"], 10)
		self.assertEqual(by_item["Turmeric"]["rate"], 20)
		self.assertEqual(by_item["Chilli"]["opening_qty"], 0)
		self.assertEqual(by_item["Chilli"]["closing_qty"], 3)

	def test_one_statement_per_distributor_company_and_month(self):
		start, end = statement_period("2026-11-26")
		self.assertEqual((start, end), (date(2026, 11, 1), date(2026, 11, 30)))
		rows = [{"name": "DSS-1", "distributor": "AJ Traders", "company": "Foods", "from_date": start}]
		self.assertEqual(find_duplicate_statement(rows, "AJ Traders", "Foods", "2026-11-02")["name"], "DSS-1")
		self.assertIsNone(find_duplicate_statement(rows, "AJ Traders", "Foods", start, current_name="DSS-1"))
		self.assertIsNone(find_duplicate_statement(rows, "AJ Traders", "Beverages", start))
		with self.assertRaises(DistributorError):
			normalize_lines(
				[{"item": "Turmeric", "secondary_qty": 1}, {"item": "Turmeric", "secondary_qty": 2}],
				{},
				{},
			)

	def test_visit_stock_rejects_a_missing_item_and_a_negative_quantity(self):
		cleaned = clean_visit(
			{"distributor": "AJ Traders", "visit_date": "2026-11-27", "order_amount": 500},
			[{"item": "Turmeric", "qty": 2, "uom": "Kg", "batch_no": ""}],
		)
		self.assertEqual(cleaned[0]["batch_no"], None)
		with self.assertRaises(DistributorError):
			clean_visit({"distributor": "AJ Traders", "visit_date": "2026-11-27"}, [{"item": "", "qty": 1}])
		with self.assertRaises(DistributorError):
			clean_visit({"distributor": "AJ Traders", "visit_date": "2026-11-27"}, [{"item": "Turmeric", "qty": -1}])


class TestComplaint(unittest.TestCase):
	def test_credit_note_has_to_be_a_return_for_the_same_customer(self):
		clean_complaint(
			{
				"distributor": "AJ Traders",
				"complaint_date": "2026-11-27",
				"complaint_type": "Damage",
				"description": "Torn pack",
				"credit_note": "SINV-1",
			},
			{"name": "SINV-1", "is_return": 1, "customer": "AJ Traders"},
		)
		with self.assertRaises(DistributorError):
			clean_complaint(
				{
					"distributor": "AJ Traders",
					"complaint_date": "2026-11-27",
					"complaint_type": "Damage",
					"description": "Torn pack",
					"credit_note": "SINV-2",
				},
				{"is_return": 0, "customer": "AJ Traders"},
			)
		with self.assertRaises(DistributorError):
			clean_complaint(
				{
					"distributor": "AJ Traders",
					"complaint_date": "2026-11-27",
					"complaint_type": "Pricing",
					"description": "",
				}
			)


class TestDashboard(unittest.TestCase):
	def bundle(self):
		return {
			"customer": "AJ Traders",
			"customer_name": "AJ Traders",
			"company": "Foods",
			"currency": "INR",
			"profile": profile(visit_frequency="Monthly", counters=40),
			"outstanding": 1500,
			"overdue_amount": 400,
			"open_complaints": 2,
			"invoices": [
				{"name": "SI-NOV-A", "posting_date": "2026-11-10", "amount": 10000, "is_return": 0, "company": "Foods"},
				{"name": "SI-NOV-B", "posting_date": "2026-11-20", "amount": 5000, "is_return": 0, "company": "Foods"},
				{"name": "CN-NOV", "posting_date": "2026-11-25", "amount": 1000, "is_return": 1, "company": "Foods"},
				{"name": "SI-OCT", "posting_date": "2026-10-05", "amount": 30000, "is_return": 0, "company": "Foods"},
				{"name": "SI-SEP", "posting_date": "2026-09-01", "amount": 20000, "is_return": 0, "company": "Foods"},
				{"name": "SI-DEC", "posting_date": "2025-12-01", "amount": 1000, "is_return": 0, "company": "Foods"},
				{"name": "SI-OLD", "posting_date": "2025-11-01", "amount": 99999, "is_return": 0, "company": "Foods"},
				{"name": "SI-OTHER", "posting_date": "2026-11-15", "amount": 80000, "is_return": 0, "company": "Beverages"},
			],
			"lines": [
				{"item": "Turmeric", "item_name": "Turmeric Powder", "posting_date": "2026-11-10", "amount": 8000, "qty": 10, "is_return": 0, "company": "Foods"},
				{"item": "Chilli", "item_name": "Chilli Powder", "posting_date": "2026-10-05", "amount": 2000, "qty": 4, "is_return": 0, "company": "Foods"},
			],
			"statements": [
				{
					"name": "DSS-OCT",
					"from_date": "2026-10-01",
					"company": "Foods",
					"total_secondary_qty": 6,
					"total_secondary_value": 8000,
					"total_closing_qty": 12,
					"total_closing_value": 9000,
				}
			],
			"visits": [{"name": "DV-1", "visit_date": "2026-11-18", "salesman": "ravi@example.com", "order_amount": 500, "company": "Foods"}],
			"complaints": [],
			"payments": [{"name": "PE-1", "posting_date": "2026-11-21", "amount": 4000, "company": "Foods"}],
		}

	def test_kpis_chart_and_suggested_target(self):
		built = build_dashboard(self.bundle(), TODAY, 10)
		self.assertEqual(built["last_billing"]["name"], "SI-NOV-B")
		self.assertEqual(built["last_billing"]["amount"], 5000)
		self.assertEqual(built["days_since_order"], 7)
		self.assertEqual(built["primary_mtd"], 14000)
		self.assertEqual(built["primary_3m"], 64000)
		self.assertEqual(built["primary_12m"], 65000)
		self.assertNotEqual(built["chart"][0]["primary"], 99999)
		self.assertEqual(built["secondary_sales"], 8000)
		self.assertEqual(built["closing_qty"], 12)
		self.assertEqual(built["closing_value"], 9000)
		self.assertEqual(built["statement_month"], date(2026, 10, 1))
		self.assertIsNone(built["chart"][-1]["secondary"])
		self.assertEqual(built["chart"][-2]["secondary"], 8000)
		self.assertEqual(built["counters"], 40)
		self.assertEqual(built["last_visit"], date(2026, 11, 18))
		self.assertEqual(built["open_complaints"], 2)
		self.assertEqual(built["outstanding"], 1500)
		self.assertEqual(built["overdue_amount"], 400)
		suggestion = built["suggestion"]
		self.assertEqual(suggestion["from_date"], date(2026, 12, 1))
		self.assertEqual(suggestion["to_date"], date(2026, 12, 31))
		self.assertEqual(suggestion["period_label"], "Dec 2026")
		self.assertEqual(suggestion["average"], round(64000 / 3, 2))
		self.assertEqual(suggestion["amount"], round(suggestion["average"] * 1.1, 2))
		self.assertEqual(built["products"][0]["item"], "Turmeric")
		self.assertEqual(built["products"][0]["share"], 80)
		self.assertEqual(built["products"][0]["pace"], "fast")
		self.assertTrue(built["signals"]["no_submitted_invoices"] is False)
		self.assertEqual(built["signals"]["billing_tone"], "green")
		self.assertEqual(built["signals"]["cover_days"], 60.0)
		self.assertEqual(built["signals"]["cover_tone"], "red")
		self.assertEqual(built["buying"]["order_count"], 5)
		self.assertEqual(built["tabs"]["credit_notes"][0]["name"], "CN-NOV")
		self.assertEqual(built["tabs"]["credit_notes"][0]["amount"], -1000)
		self.assertEqual(built["tabs"]["payments"][0]["doctype"], "Payment Entry")
		self.assertEqual(len(built["chart"]), 12)

	def test_colour_bands_for_the_page_and_the_follow_up_report(self):
		self.assertEqual(achievement_tone(100), "green")
		self.assertEqual(achievement_tone(70), "amber")
		self.assertEqual(achievement_tone(69.99), "red")
		self.assertEqual(achievement_tone(None), "neutral")
		self.assertEqual(cover_tone(0), "red")
		self.assertEqual(cover_tone(6), "amber")
		self.assertEqual(cover_tone(7), "green")
		self.assertEqual(cover_tone(30), "green")
		self.assertEqual(cover_tone(45), "amber")
		self.assertEqual(cover_tone(46), "red")
		self.assertEqual(days_of_cover(12, 6, 30), 60.0)
		self.assertIsNone(days_of_cover(None, 6, 30))
		self.assertEqual(billing_tone(None), "red")
		self.assertEqual(billing_tone(7), "green")
		self.assertEqual(billing_tone(8), "amber")
		self.assertEqual(billing_tone(16), "red")
		self.assertEqual(visit_tone("2026-11-26", TODAY), "red")
		self.assertEqual(visit_tone(TODAY, TODAY), "amber")
		self.assertEqual(visit_tone("2026-12-01", TODAY), "green")
		self.assertEqual(product_pace(0, 10), "no-movement")
		self.assertEqual(product_pace(12, 10), "fast")
		self.assertEqual(product_pace(4, 10), "slow")
		built = build_dashboard(
			{"customer": "New", "company": "Foods", "currency": "INR", "invoices": [], "lines": []},
			TODAY,
		)
		self.assertTrue(built["signals"]["no_submitted_invoices"])
		self.assertEqual(built["primary_mtd"], 0)
		with_target = build_dashboard(
			{
				"customer": "AJ Traders",
				"company": "Foods",
				"current_target": {"name": "CPT-1", "target_amount": 20000},
				"invoices": [{"name": "SI-1", "posting_date": "2026-11-10", "amount": 10000, "is_return": 0, "company": "Foods"}],
			},
			TODAY,
		)
		self.assertEqual(with_target["signals"]["achievement_pct"], 50)
		self.assertEqual(with_target["signals"]["primary_tone"], "red")

	def test_quotations_sales_orders_and_draft_invoices(self):
		self.assertEqual(quote_tone("Draft", 0), "grey")
		self.assertEqual(quote_tone("Open", 1), "blue")
		self.assertEqual(quote_tone("Ordered", 1), "green")
		self.assertEqual(quote_tone("Lost", 1), "red")
		self.assertEqual(quote_tone("Expired", 1), "red")
		built = build_dashboard(
			{
				"customer": "AJ Traders",
				"company": "Foods",
				"currency": "INR",
				"invoices": [
					{"name": "SI-1", "posting_date": "2026-11-02", "amount": 1000, "is_return": 0, "company": "Foods", "docstatus": 1}
				],
				"draft_invoices": [
					{"name": "SI-D", "posting_date": "2026-11-20", "amount": 9000, "is_return": 0, "company": "Foods", "docstatus": 0}
				],
				"quotations": [
					{"name": "QTN-D", "transaction_date": "2026-11-01", "amount": 500, "status": "Draft", "docstatus": 0, "company": "Foods"},
					{"name": "QTN-O", "transaction_date": "2026-11-05", "amount": 1500, "status": "Open", "docstatus": 1, "company": "Foods"},
					{"name": "QTN-L", "transaction_date": "2026-10-01", "amount": 200, "status": "Lost", "docstatus": 1, "company": "Foods"},
					{"name": "QTN-X", "transaction_date": "2026-09-01", "amount": 999, "status": "Cancelled", "docstatus": 2, "company": "Foods"},
				],
				"sales_orders": [
					{"name": "SO-1", "transaction_date": "2026-11-08", "amount": 1500, "status": "To Deliver and Bill", "docstatus": 1, "company": "Foods"}
				],
				"payments": [
					{"name": "PE-9", "posting_date": "2026-11-09", "amount": 400, "docstatus": 1, "company": "Foods"}
				],
			},
			TODAY,
		)
		self.assertEqual(built["primary_mtd"], 1000)
		quotes = built["quotations"]
		self.assertEqual(quotes["draft_count"], 1)
		self.assertEqual(quotes["submitted_count"], 2)
		self.assertEqual(quotes["total_value"], 2200)
		tones = {row["status"]: row["tone"] for row in quotes["pills"]}
		self.assertEqual(tones["Draft"], "grey")
		self.assertEqual(tones["Open"], "blue")
		self.assertEqual(tones["Lost"], "red")
		self.assertEqual(built["tabs"]["draft_invoices"][0]["text"], "Draft — not counted")
		self.assertEqual(built["tabs"]["quotations"][0]["doctype"], "Quotation")
		self.assertEqual(built["tabs"]["sales_orders"][0]["doctype"], "Sales Order")
		self.assertEqual(built["tabs"]["payments"][0]["name"], "PE-9")
		self.assertNotIn("SI-D", [row["name"] for row in built["tabs"]["invoices"]])
		summary = summarize_quotations([])
		self.assertEqual(summary["count"], 0)
		self.assertEqual(summary["total_value"], 0)

	def test_growth_changes_only_the_suggestion(self):
		chart = [{"label": "Sep", "year": 2026, "primary": 100}, {"label": "Oct", "year": 2026, "primary": 100}, {"label": "Nov", "year": 2026, "primary": 100}]
		base = target_suggestion(chart, TODAY, None)
		higher = target_suggestion(chart, TODAY, 20)
		self.assertEqual(base["growth_pct"], 10)
		self.assertEqual(base["amount"], 110)
		self.assertEqual(higher["amount"], 120)
		with self.assertRaises(DistributorError):
			clean_growth(250)
		self.assertEqual(clean_days(""), 30)
		self.assertEqual(clean_days(0), 30)
		with self.assertRaises(DistributorError):
			clean_days(4000)


class TestFollowUp(unittest.TestCase):
	def facts(self, **overrides):
		row = {"last_order_date": TODAY, "achievement_pct": 80, "open_complaints": 0, "overdue_amount": 0}
		row.update(overrides)
		return row

	def test_each_reason_and_the_boundaries(self):
		rows = follow_up_rows(
			[
				profile(customer="Never", customer_name="Never Visited"),
				profile(customer="Due", customer_name="Due", last_visit_date="2026-11-01", next_visit_due="2026-11-26"),
				profile(customer="Today", customer_name="Due Today", last_visit_date="2026-11-20", next_visit_due=TODAY),
				profile(customer="Quiet", customer_name="Quiet", last_visit_date="2026-11-20", next_visit_due="2026-12-20"),
				profile(customer="Short", customer_name="Short", last_visit_date="2026-11-20", next_visit_due="2026-12-20"),
				profile(customer="Exact", customer_name="Exact", last_visit_date="2026-11-20", next_visit_due="2026-12-20"),
				profile(customer="Open", customer_name="Open", last_visit_date="2026-11-20", next_visit_due="2026-12-20"),
				profile(customer="Owes", customer_name="Owes", last_visit_date="2026-11-20", next_visit_due="2026-12-20"),
				profile(customer="Fine", customer_name="Fine", last_visit_date="2026-11-26", next_visit_due="2026-12-03"),
				profile(customer="Asleep", customer_name="Asleep", is_active=0, last_visit_date=None),
			],
			{
				"Never": self.facts(last_order_date=None, achievement_pct=None),
				"Due": self.facts(),
				"Today": self.facts(),
				"Quiet": self.facts(last_order_date="2026-10-27"),
				"Short": self.facts(achievement_pct=69.99),
				"Exact": self.facts(achievement_pct=70),
				"Open": self.facts(open_complaints=2),
				"Owes": self.facts(overdue_amount=250),
				"Fine": self.facts(),
				"Asleep": self.facts(last_order_date=None, achievement_pct=10, open_complaints=1),
			},
			{"no_order_days": 30},
			MANAGER,
			TODAY,
		)
		by_name = {row["distributor"]: row for row in rows["rows"]}
		self.assertIn("No visit yet", by_name["Never"]["reasons"])
		self.assertIn("No order yet", by_name["Never"]["reasons"])
		self.assertIn("Overdue visit", by_name["Due"]["reasons"])
		self.assertNotIn("Today", by_name)
		self.assertIn("No order in 31 days", by_name["Quiet"]["reasons"])
		self.assertIn("Target below 70%", by_name["Short"]["reasons"])
		self.assertNotIn("Exact", by_name)
		self.assertIn("2 open complaints", by_name["Open"]["reasons"])
		self.assertIn("Overdue receivable", by_name["Owes"]["reasons"])
		self.assertEqual(by_name["Owes"]["overdue_amount"], 250)
		self.assertNotIn("Fine", by_name)
		self.assertNotIn("Asleep", by_name)
		asleep = follow_up_rows(
			[profile(customer="Asleep", customer_name="Asleep", is_active=0)],
			{"Asleep": self.facts(open_complaints=1)},
			{"include_inactive": 1},
			MANAGER,
			TODAY,
		)
		self.assertIn("Open complaint", asleep["rows"][0]["reasons"])
		self.assertNotIn("No visit yet", asleep["rows"][0]["reasons"])

	def test_account_manager_filter_and_sales_user_scope(self):
		built = follow_up_rows(
			[
				profile(customer="Mine", customer_name="Mine"),
				profile(customer="Theirs", customer_name="Theirs", account_manager="other@example.com", sales_person="Asha", salesman="asha@example.com"),
			],
			{"Mine": self.facts(last_order_date=None, achievement_pct=None), "Theirs": self.facts(last_order_date=None, achievement_pct=None)},
			{"account_manager": "priya@example.com"},
			SALES,
			TODAY,
		)
		self.assertEqual([row["distributor"] for row in built["rows"]], ["Mine"])
		everyone = follow_up_rows(
			[profile(customer="Theirs", customer_name="Theirs", account_manager="other@example.com", sales_person="", salesman="")],
			{"Theirs": self.facts(last_order_date=None, achievement_pct=None)},
			{},
			SALES,
			TODAY,
		)
		self.assertEqual(everyone["rows"], [])
		self.assertTrue(can_see_profile(SALES, profile()))
		self.assertTrue(can_see_profile(MANAGER, profile(account_manager="other@example.com", sales_person="", salesman="")))
		self.assertFalse(
			can_file(SALES, profile(account_manager="other@example.com", sales_person="", salesman=""), is_new=True, owner="priya@example.com", distributor="AJ Traders")
		)
		self.assertTrue(
			can_file(
				SALES,
				profile(account_manager="other@example.com", sales_person="", salesman=""),
				is_new=False,
				owner="priya@example.com",
				distributor="AJ Traders",
				previous_distributor="AJ Traders",
			)
		)

	def test_current_month_target_uses_the_whole_customer_row(self):
		pct = achievement_for_month(
			[
				{"period_type": "Monthly", "from_date": "2026-11-01", "company": "Foods", "item_group": "Spices", "brand": "", "achievement_pct": 10},
				{"period_type": "Monthly", "from_date": "2026-11-01", "company": "Foods", "item_group": "", "brand": "", "achievement_pct": 55},
				{"period_type": "Monthly", "from_date": "2026-10-01", "company": "Foods", "achievement_pct": 1},
			],
			TODAY,
			"Foods",
		)
		self.assertEqual(pct, 55)
		self.assertIsNone(achievement_for_month([], TODAY, "Foods"))


class TestDesk(unittest.TestCase):
	def test_workspace_merge_keeps_team_files_and_appends_once(self):
		merged = merge_distributor_workspace(
			[{"label": "Team Chat"}, {"label": "Team Files"}],
			[{"id": "qa5", "type": "shortcut", "data": {"shortcut_name": "Team Chat"}}],
			[{"label": "Team Files", "link_to": "team-files"}],
		)
		self.assertTrue(merged["changed"])
		self.assertEqual(merged["shortcuts"][0]["label"], "Team Chat")
		self.assertEqual(merged["shortcuts"][1]["label"], "Team Files")
		self.assertEqual(
			[row["label"] for row in merged["shortcuts"][2:]],
			[link["label"] for link in DISTRIBUTOR_LINKS],
		)
		again = merge_distributor_workspace(merged["shortcuts"], merged["content"], merged["links"])
		self.assertFalse(again["changed"])
		self.assertEqual(len(again["shortcuts"]), 2 + len(DISTRIBUTOR_LINKS))
		report = next(row for row in merged["shortcuts"] if row["label"] == "Distributor Follow-up")
		self.assertEqual(report["report_ref_doctype"], "Distributor Profile")
		page = next(row for row in merged["shortcuts"] if row["label"] == "Distributor 360")
		self.assertEqual(page["type"], "Page")
		self.assertEqual(page["link_to"], "distributor-360")

	def test_sidebar_rows(self):
		missing = missing_sidebar_links([("Page", "team-files")])
		self.assertEqual([row["link_to"] for row in missing], [link["link_to"] for link in DISTRIBUTOR_LINKS])
		self.assertEqual(
			missing_sidebar_links((link["link_type"], link["link_to"]) for link in DISTRIBUTOR_LINKS),
			[],
		)

	def test_shipped_files_leave_the_existing_desk_alone(self):
		for name, fields in (
			("distributor_profile", {"customer", "company", "account_manager", "sales_person", "salesman", "territory", "area", "counters", "visit_frequency", "next_visit_due", "is_active", "notes"}),
			("distributor_visit", {"distributor", "visit_date", "salesman", "stock_lines", "order_amount", "sales_order", "counters_visited", "next_follow_up"}),
			("distributor_stock_statement", {"distributor", "company", "statement_month", "items", "period_key"}),
			("distributor_complaint", {"distributor", "complaint_type", "status", "item", "batch_no", "description", "attachments", "credit_note", "assigned_to"}),
		):
			payload = json.loads((PACKAGE / "melliflous_branding" / "doctype" / name / f"{name}.json").read_text())
			have = {row["fieldname"] for row in payload["fields"]}
			self.assertTrue(fields <= have, fields - have)
			roles = {row["role"]: row for row in payload["permissions"]}
			self.assertEqual(roles["Sales Manager"]["write"], 1)
			self.assertEqual(roles["Sales Manager"]["create"], 1)
			self.assertEqual(roles["System Manager"]["delete"], 1)
			self.assertEqual(roles["Sales User"]["read"], 1)
			self.assertEqual(roles["Sales User"]["delete"], 0)

		profile = json.loads((PACKAGE / "melliflous_branding" / "doctype" / "distributor_profile" / "distributor_profile.json").read_text())
		self.assertEqual(profile["autoname"], "field:customer")
		self.assertEqual({row["role"]: row["write"] for row in profile["permissions"]}["Sales User"], 0)
		visit = json.loads((PACKAGE / "melliflous_branding" / "doctype" / "distributor_visit" / "distributor_visit.json").read_text())
		self.assertEqual({row["role"]: row["create"] for row in visit["permissions"]}["Sales User"], 1)
		stock = json.loads(
			(PACKAGE / "melliflous_branding" / "doctype" / "distributor_visit_stock" / "distributor_visit_stock.json").read_text()
		)
		self.assertEqual(stock["istable"], 1)
		self.assertIn("batch_no", {row["fieldname"] for row in stock["fields"]})

		report = json.loads(
			(PACKAGE / "melliflous_branding" / "report" / "distributor_follow_up" / "distributor_follow_up.json").read_text()
		)
		self.assertEqual(report["report_type"], "Script Report")
		self.assertEqual(report["ref_doctype"], "Distributor Profile")
		self.assertEqual({row["role"] for row in report["roles"]}, {"System Manager", "Sales Manager", "Sales User"})

		page = json.loads((PACKAGE / "melliflous_branding" / "page" / "distributor_360" / "distributor_360.json").read_text())
		self.assertEqual(page["name"], "distributor-360")
		self.assertEqual(page["system_page"], 1)
		script = (PACKAGE / "melliflous_branding" / "page" / "distributor_360" / "distributor_360.js").read_text()
		self.assertIn('frappe.pages["distributor-360"].on_page_load', script)
		self.assertIn("The distributor could not be loaded.", script)
		self.assertIn("Set Target", script)
		self.assertIn("is-error", script)
		self.assertIn("₹0 — no submitted invoices yet", script)
		self.assertIn("New Quotation", script)
		self.assertIn('frappe.new_doc("Quotation")', script)
		self.assertIn("frappe.dom.set_style", script)
		self.assertIn("melliflous-distributor-360", script)
		self.assertIn(".melliflous-360 .band", script)
		self.assertIn('width="18" height="18"', script)
		stylesheet = (PACKAGE / "public" / "css" / "melliflous_branding.css").read_text()
		self.assertIn("tone-green", stylesheet)
		self.assertIn(".melliflous-360 .band", stylesheet)

		self.assertFalse((PACKAGE / "melliflous_branding" / "workspace" / "quick_actions" / "quick_actions.json").exists())

		sidebar = json.loads(
			(PACKAGE / "melliflous_branding" / "sidebar" / "melliflous_branding" / "melliflous_branding.json").read_text()
		)
		items = {row["label"]: row for row in sidebar["items"]}
		self.assertEqual(items["Team Files"]["link_to"], "team-files")
		self.assertEqual(items["Customer Targets"]["link_to"], "Customer Primary Target")
		self.assertEqual(items["Distributor 360"]["link_to"], "distributor-360")
		self.assertEqual(items["Distributor Follow-up"]["link_type"], "Report")
		self.assertNotIn("Quick Actions", items)

		team = (PACKAGE / "melliflous_branding" / "page" / "team_files" / "team_files.js").read_text()
		self.assertIn('frappe.pages["team-files"].on_page_load', team)
		tiles = (PACKAGE / "public" / "js" / "desk_tiles.js").read_text()
		self.assertIn('"Team Chat": true', tiles)
		self.assertIn('"Team Files": true', tiles)
		self.assertNotIn("Distributor 360", tiles)

		self.assertIn("Distributor Profile", hooks.permission_query_conditions)
		tiles = {row["name"]: row for row in hooks.add_to_apps_screen}
		self.assertNotIn("melliflous_branding", tiles)
		self.assertNotIn("Quick Actions", [row.get("title") for row in hooks.add_to_apps_screen])
		tile = tiles["distributor_360"]
		self.assertEqual(tile["title"], "Distributor 360")
		self.assertEqual(tile["route"], "/desk/distributor-360")
		self.assertEqual(tile["has_permission"], "melliflous_branding.access.can_show_distributor_360")
		self.assertEqual(tile["logo"], "/assets/melliflous_branding/images/distributor_360.png")
		logo = PACKAGE / "public" / "images" / "distributor_360.png"
		self.assertTrue(logo.is_file())
		self.assertTrue(logo.read_bytes().startswith(b"\x89PNG"))
		self.assertIn("Customer Primary Target", hooks.permission_query_conditions)
		self.assertIn("melliflous_branding.target_records.refresh_primary_targets", hooks.scheduler_events["daily"])
		self.assertIn("melliflous_branding.patches.v0_6.ensure_distributors", (PACKAGE / "patches.txt").read_text())
		self.assertIn("melliflous_branding.patches.v0_5.ensure_customer_targets", (PACKAGE / "patches.txt").read_text())
		self.assertIn("ensure_distributor_places", (PACKAGE / "install.py").read_text())
		self.assertIn("ensure_team_folders", (PACKAGE / "install.py").read_text())

	def test_apps_screen_tile_is_limited_to_sales_roles(self):
		self.assertTrue(can_open_distributor_360("Administrator", []))
		self.assertTrue(can_open_distributor_360("boss@example.com", ["Sales Manager"]))
		self.assertTrue(can_open_distributor_360("boss@example.com", ["System Manager"]))
		self.assertTrue(can_open_distributor_360("priya@example.com", ["Sales User", "Employee"]))
		self.assertFalse(can_open_distributor_360("accounts@example.com", ["Accounts User"]))
		self.assertFalse(can_open_distributor_360("Guest", ["Guest"]))
		self.assertFalse(can_open_distributor_360("", ["Sales User"]))

	def test_boot_adds_one_grid_row_beside_quick_actions(self):
		quick_actions = {
			"on_apps_screen": True,
			"sequence_id": 12,
			"app_name": "melliflous_branding",
			"app_title": "Quick Actions",
			"app_route": "/desk/quick-actions",
			"app_logo_url": "/assets/melliflous_branding/images/melliflous_icon_512.png",
			"dock": [],
		}
		placed = place_distributor_360_app([quick_actions], "priya@example.com", ["Sales User"])
		self.assertEqual([row["app_title"] for row in placed], ["Distributor 360"])
		tile = placed[0]
		self.assertEqual(tile["app_name"], "distributor_360")
		self.assertEqual(tile["app_title"], "Distributor 360")
		self.assertEqual(tile["app_route"], "/desk/distributor-360")
		self.assertEqual(tile["app_logo_url"], "/assets/melliflous_branding/images/distributor_360.png")
		self.assertTrue(tile["on_apps_screen"])
		self.assertEqual(tile["dock"], [])
		again = place_distributor_360_app(placed, "priya@example.com", ["Sales User"])
		self.assertEqual(len(again), 1)
		hidden = place_distributor_360_app(placed, "accounts@example.com", ["Accounts User"])
		self.assertEqual(hidden, [])
		self.assertIn("place_distributor_360_app", (PACKAGE / "boot.py").read_text())


class TestDistributorBook(unittest.TestCase):
	def test_activity_uses_the_profile_then_the_customer_then_ninety_days(self):
		self.assertEqual(distributor_activity(1, 1, None, TODAY), {"active": 1, "rule": "Distributor profile is active."})
		self.assertEqual(distributor_activity(0, 0, TODAY, TODAY)["active"], 0)
		self.assertIn("inactive", distributor_activity(0, 0, TODAY, TODAY)["rule"])
		disabled = distributor_activity(None, 1, TODAY, TODAY)
		self.assertEqual(disabled["active"], 0)
		self.assertEqual(disabled["rule"], "Customer is disabled.")
		enabled = distributor_activity(None, 0, None, TODAY)
		self.assertEqual(enabled["active"], 1)
		self.assertEqual(enabled["rule"], "Customer is not disabled.")
		quiet = distributor_activity(None, None, date(2026, 8, 1), TODAY)
		self.assertEqual(quiet["active"], 0)
		self.assertEqual(quiet["rule"], "No submitted invoice in 90 days.")
		self.assertEqual(distributor_activity(None, None, date(2026, 11, 1), TODAY)["active"], 1)
		self.assertEqual(distributor_activity(None, None, TODAY - timedelta(days=90), TODAY)["active"], 1)
		self.assertEqual(distributor_activity(None, None, TODAY - timedelta(days=91), TODAY)["active"], 0)

	def test_book_rag_is_separate_from_the_single_distributor_page(self):
		self.assertEqual(mis_rag(90), "green")
		self.assertEqual(mis_rag(89.99), "amber")
		self.assertEqual(mis_rag(60), "amber")
		self.assertEqual(mis_rag(59.99), "red")
		self.assertEqual(mis_rag(None), "neutral")
		self.assertEqual(achievement_tone(90), "amber")
		self.assertEqual(achievement_tone(100), "green")

	def test_recommendation_uses_the_higher_average_and_a_default(self):
		built = recommended_monthly_target([0, 0, 10000, 20000, 30000, 60000], 1.1, 5000)
		self.assertEqual(built["avg_3"], 36666.67)
		self.assertEqual(built["avg_6"], 20000.0)
		self.assertEqual(built["amount"], 40333.34)
		self.assertFalse(built["used_default"])
		self.assertIn("Draft invoices are not included.", built["basis"])
		self.assertIn("1.1", built["basis"])
		fresh = recommended_monthly_target([0, 0, 0, 0, 0, 0], None, 25000)
		self.assertTrue(fresh["used_default"])
		self.assertEqual(fresh["amount"], 25000)
		self.assertEqual(fresh["growth_factor"], 1.1)
		self.assertIn("No submitted invoice in the last 6 months", fresh["basis"])
		with self.assertRaises(DistributorError):
			recommended_monthly_target([1000], 0, 0)
		manual = plan_target_save("Manual", 15000, 40333.34, "agreed on the visit")
		self.assertEqual(manual["target_amount"], 15000)
		self.assertEqual(manual["source"], "Manual")
		self.assertEqual(manual["note"], "agreed on the visit")
		recommended = plan_target_save("Recommended", 1, 40333.34, None)
		self.assertEqual(recommended["target_amount"], 40333.34)
		self.assertIsNone(recommended["note"])
		with self.assertRaises(DistributorError):
			plan_target_save("Recommended", 1, 0, None)

	def test_the_book_totals_follow_the_filters_and_the_active_toggle(self):
		north = profile(customer="AJ Traders", customer_name="AJ Traders", territory="North", is_active=1)
		south = profile(
			customer="South Shop",
			customer_name="South Shop",
			territory="South",
			area="Colaba",
			is_active=0,
			account_manager="boss@example.com",
			salesman="boss@example.com",
			sales_person="Asha",
		)
		unmarked = profile(customer="Quiet Mart", customer_name="Quiet Mart", territory="North")
		unmarked.pop("is_active")
		months = {
			(2026, 6): 0,
			(2026, 7): 0,
			(2026, 8): 0,
			(2026, 9): 0,
			(2026, 10): 0,
			(2026, 11): 9000,
		}
		metrics = {
			"AJ Traders": {
				"primary_mtd": 9000,
				"target_amount": 10000,
				"target_source": "Recommended",
				"outstanding": 1000,
				"overdue": 0,
				"last_billing": date(2026, 11, 20),
				"open_quotations": 500,
				"collections_mtd": 400,
				"visits_mtd": 2,
				"months": months,
				"disabled": 0,
			},
			"South Shop": {
				"primary_mtd": 1000,
				"target_amount": 10000,
				"target_source": "Manual",
				"outstanding": 200,
				"overdue": 50,
				"last_billing": date(2026, 11, 2),
				"open_quotations": 0,
				"collections_mtd": 0,
				"visits_mtd": 0,
				"months": {(2026, 11): 1000},
				"disabled": 0,
			},
			"Quiet Mart": {
				"primary_mtd": 0,
				"target_amount": None,
				"outstanding": 0,
				"overdue": 0,
				"last_billing": date(2026, 8, 1),
				"open_quotations": 0,
				"collections_mtd": 0,
				"visits_mtd": 1,
				"months": {},
				"disabled": None,
			},
		}
		built = build_distributor_mis([north, south, unmarked], metrics, {}, TODAY, settings={"default_amount": 8000})
		by_name = {row["distributor"]: row for row in built["rows"]}
		self.assertEqual(by_name["AJ Traders"]["rag"], "green")
		self.assertEqual(by_name["AJ Traders"]["achievement_pct"], 90)
		self.assertEqual(by_name["AJ Traders"]["rule"], "Distributor profile is active.")
		self.assertFalse(by_name["AJ Traders"]["billing_stale"])
		self.assertEqual(by_name["South Shop"]["rag"], "red")
		self.assertEqual(by_name["South Shop"]["status"], "Inactive")
		self.assertEqual(by_name["Quiet Mart"]["status"], "Inactive")
		self.assertEqual(by_name["Quiet Mart"]["rule"], "No submitted invoice in 90 days.")
		self.assertEqual(by_name["Quiet Mart"]["rag"], "neutral")
		self.assertTrue(by_name["Quiet Mart"]["billing_stale"])
		self.assertEqual(by_name["Quiet Mart"]["recommended"], 8000)
		self.assertEqual(built["summary"]["active"], 1)
		self.assertEqual(built["summary"]["inactive"], 2)
		self.assertEqual(built["summary"]["primary_mtd"], 10000)
		self.assertEqual(built["summary"]["target"], 20000)
		self.assertEqual(built["summary"]["achievement_pct"], 50)
		self.assertEqual(built["summary"]["achievement_tone"], "red")
		self.assertEqual(built["summary"]["not_billed_30"], 1)
		self.assertEqual(built["summary"]["visits_mtd"], 3)
		self.assertEqual(built["summary"]["collections_mtd"], 400)
		self.assertEqual(built["summary"]["open_quotations"], 500)
		self.assertEqual(len(by_name["AJ Traders"]["sparkline"]), 6)
		self.assertEqual(by_name["AJ Traders"]["sparkline"][-1], 9000)
		active = build_distributor_mis(
			[north, south, unmarked], metrics, {"activity": "Active"}, TODAY, settings={"default_amount": 8000}
		)
		self.assertEqual([row["distributor"] for row in active["rows"]], ["AJ Traders"])
		self.assertEqual(active["summary"]["active"], 1)
		self.assertEqual(active["summary"]["inactive"], 2)
		self.assertEqual(active["summary"]["primary_mtd"], 9000)
		self.assertEqual(active["summary"]["not_billed_30"], 0)
		territory = build_distributor_mis([north, south], metrics, {"territory": "South"}, TODAY)
		self.assertEqual([row["distributor"] for row in territory["rows"]], ["South Shop"])
		owner = build_distributor_mis([north, south], metrics, {"account_manager": "boss@example.com"}, TODAY)
		self.assertEqual([row["distributor"] for row in owner["rows"]], ["South Shop"])
		reds = build_distributor_mis([north, south, unmarked], metrics, {"rag": "red"}, TODAY)
		self.assertEqual([row["distributor"] for row in reds["rows"]], ["South Shop"])
		found = build_distributor_mis([north, south], metrics, {"search": "andheri"}, TODAY)
		self.assertEqual([row["distributor"] for row in found["rows"]], ["AJ Traders"])

	def test_a_quiet_distributor_uses_the_settings_default_on_the_page(self):
		quiet = build_dashboard(
			{"customer": "New", "company": "Foods", "invoices": [], "lines": []},
			TODAY,
			settings={"growth_factor": 1.1, "default_amount": 8000},
		)
		self.assertTrue(quiet["recommendation"]["used_default"])
		self.assertEqual(quiet["signals"]["recommended_amount"], 8000)
		self.assertIn("default of 8000.00", quiet["recommendation"]["basis"])
		with_source = build_dashboard(
			{
				"customer": "AJ Traders",
				"company": "Foods",
				"current_target": {"name": "CPT-1", "target_amount": 20000, "target_source": "Manual"},
				"invoices": [{"name": "SI-1", "posting_date": "2026-11-10", "amount": 10000, "is_return": 0, "company": "Foods"}],
			},
			TODAY,
		)
		self.assertEqual(with_source["signals"]["target_source"], "Manual")
		self.assertEqual(with_source["signals"]["target_source_tone"], "blue")
		self.assertEqual(with_source["signals"]["primary_tone"], "red")

	def test_the_page_opens_the_book_and_can_export_it(self):
		script = (PACKAGE / "melliflous_branding" / "page" / "distributor_360" / "distributor_360.js").read_text()
		self.assertIn("distributor_mis", script)
		self.assertIn('get("view") === "all"', script)
		self.assertIn("Use recommended", script)
		self.assertIn("Enter manually", script)
		self.assertIn("Apply recommended to selected", script)
		self.assertIn("distributors.csv", script)
		self.assertIn("set_distributor_target", script)
		self.assertIn(".mis-filters", script)
		self.assertIn(".mini-spark", script)
		self.assertIn('width="18" height="18"', script)
		stylesheet = (PACKAGE / "public" / "css" / "melliflous_branding.css").read_text()
		self.assertIn(".mis-filters", stylesheet)
		self.assertIn(".mini-spark", stylesheet)
		records = (PACKAGE / "distributor_records.py").read_text()
		self.assertIn("def distributor_mis", records)
		self.assertIn("docstatus = 1", records)
		self.assertIn("def apply_recommended_targets", records)
		target = json.loads(
			(PACKAGE / "melliflous_branding" / "doctype" / "customer_primary_target" / "customer_primary_target.json").read_text()
		)
		fields = {row["fieldname"] for row in target["fields"]}
		self.assertTrue({"target_source", "recommended_amount", "set_by", "set_on", "recommendation_basis"} <= fields)
		settings = json.loads(
			(PACKAGE / "melliflous_branding" / "doctype" / "distributor_settings" / "distributor_settings.json").read_text()
		)
		self.assertEqual(settings["issingle"], 1)
		self.assertEqual(settings["fields"][0]["fieldname"], "growth_factor")
		self.assertIn("melliflous_branding.patches.v0_7.ensure_target_source", (PACKAGE / "patches.txt").read_text())


if __name__ == "__main__":
	unittest.main()
