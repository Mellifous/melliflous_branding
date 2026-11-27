# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import json
import unittest
from datetime import date
from pathlib import Path

from melliflous_branding import hooks
from melliflous_branding.distributors import (
	DISTRIBUTOR_LINKS,
	DistributorError,
	achievement_for_month,
	add_months,
	apply_statement_line,
	build_dashboard,
	can_file,
	can_open_distributor_360,
	can_see_profile,
	clean_complaint,
	clean_days,
	clean_growth,
	clean_visit,
	find_duplicate_statement,
	follow_up_rows,
	merge_distributor_workspace,
	missing_sidebar_links,
	next_visit_due,
	normalize_lines,
	prefill_rows,
	prepare_profile_values,
	received_by_item,
	statement_period,
	target_suggestion,
	trailing_months,
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
		self.assertEqual(built["buying"]["order_count"], 5)
		self.assertEqual(built["tabs"]["credit_notes"][0]["name"], "CN-NOV")
		self.assertEqual(built["tabs"]["credit_notes"][0]["amount"], -1000)
		self.assertEqual(built["tabs"]["payments"][0]["doctype"], "Payment Entry")
		self.assertEqual(len(built["chart"]), 12)

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
		self.assertIn("Create Target", script)
		self.assertIn("is-error", script)

		workspace = json.loads((PACKAGE / "melliflous_branding" / "workspace" / "quick_actions" / "quick_actions.json").read_text())
		labels = [row["label"] for row in workspace["shortcuts"]]
		self.assertEqual(labels[:2], ["Team Chat", "Team Files"])
		self.assertIn("Customer Targets", labels)
		self.assertIn("Distributor 360", labels)
		self.assertIn("Distributor Follow-up", labels)
		content = [block["data"]["shortcut_name"] for block in json.loads(workspace["content"])]
		self.assertEqual(content[:2], ["Team Chat", "Team Files"])

		sidebar = json.loads(
			(PACKAGE / "melliflous_branding" / "sidebar" / "melliflous_branding" / "melliflous_branding.json").read_text()
		)
		items = {row["label"]: row for row in sidebar["items"]}
		self.assertEqual(items["Team Files"]["link_to"], "team-files")
		self.assertEqual(items["Customer Targets"]["link_to"], "Customer Primary Target")
		self.assertEqual(items["Distributor 360"]["link_to"], "distributor-360")
		self.assertEqual(items["Distributor Follow-up"]["link_type"], "Report")

		team = (PACKAGE / "melliflous_branding" / "page" / "team_files" / "team_files.js").read_text()
		self.assertIn('frappe.pages["team-files"].on_page_load', team)
		tiles = (PACKAGE / "public" / "js" / "desk_tiles.js").read_text()
		self.assertIn('"Team Chat": true', tiles)
		self.assertIn('"Team Files": true', tiles)
		self.assertNotIn("Distributor 360", tiles)

		self.assertIn("Distributor Profile", hooks.permission_query_conditions)
		tiles = {row["name"]: row for row in hooks.add_to_apps_screen}
		self.assertEqual(tiles["melliflous_branding"]["title"], "Quick Actions")
		self.assertEqual(tiles["melliflous_branding"]["route"], "/desk/quick-actions")
		tile = tiles["distributor_360"]
		self.assertEqual(tile["title"], "Distributor 360")
		self.assertEqual(tile["route"], "/desk/distributor-360")
		self.assertEqual(tile["has_permission"], "melliflous_branding.access.can_show_distributor_360")
		self.assertEqual(tile["logo"], "/assets/melliflous_branding/images/distributor_360.svg")
		logo = PACKAGE / "public" / "images" / "distributor_360.svg"
		self.assertTrue(logo.is_file())
		self.assertIn("<svg", logo.read_text())
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


if __name__ == "__main__":
	unittest.main()
