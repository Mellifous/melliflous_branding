# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import json
import unittest
from datetime import date
from pathlib import Path

from melliflous_branding import hooks
from melliflous_branding.targets import (
	TARGET_LINKS,
	TargetError,
	achievement_figures,
	achievement_for_targets,
	build_report,
	can_edit_targets,
	can_see_target,
	clean_bulk_rows,
	find_overlap,
	indicator_colour,
	line_qty,
	merge_workspace,
	missing_sidebar_links,
	month_bounds,
	plan_bulk,
	quarter_bounds,
	saved_period,
	signed_amount,
)

PACKAGE = Path(__file__).resolve().parents[1]


def target(**overrides):
	row = {
		"name": "CPT-2026-00001",
		"customer": "AJ Traders",
		"customer_name": "AJ Traders",
		"company": "Melliflous Foods (OPC) Pvt Ltd",
		"territory": "North",
		"period_type": "Monthly",
		"from_date": "2026-11-01",
		"to_date": "2026-11-30",
		"target_amount": 100000,
		"item_group": "",
		"brand": "",
		"uom": "",
		"sales_person": "Priya",
		"sales_user": "priya@example.com",
		"owner": "priya@example.com",
	}
	row.update(overrides)
	return row


def line(**overrides):
	row = {
		"customer": "AJ Traders",
		"company": "Melliflous Foods (OPC) Pvt Ltd",
		"posting_date": "2026-11-10",
		"is_return": 0,
		"amount": 40000,
		"qty": 10,
		"stock_qty": 10,
		"uom": "Kg",
		"stock_uom": "Kg",
		"item_group": "Whole Spices",
		"brand": "SK Gourmet",
	}
	row.update(overrides)
	return row


class TestPeriods(unittest.TestCase):
	def test_month_bounds_include_leap_day_and_december(self):
		self.assertEqual(month_bounds("2026-11-26"), (date(2026, 11, 1), date(2026, 11, 30)))
		self.assertEqual(month_bounds(date(2024, 2, 15)), (date(2024, 2, 1), date(2024, 2, 29)))
		self.assertEqual(month_bounds("2026-02-01"), (date(2026, 2, 1), date(2026, 2, 28)))
		self.assertEqual(month_bounds("2026-12-31"), (date(2026, 12, 1), date(2026, 12, 31)))

	def test_indian_fiscal_quarters(self):
		self.assertEqual(quarter_bounds("2026-04-01"), (date(2026, 4, 1), date(2026, 6, 30)))
		self.assertEqual(quarter_bounds("2026-11-26"), (date(2026, 10, 1), date(2026, 12, 31)))
		self.assertEqual(quarter_bounds("2026-01-15"), (date(2026, 1, 1), date(2026, 3, 31)))
		self.assertEqual(quarter_bounds("2026-03-31"), (date(2026, 1, 1), date(2026, 3, 31)))

	def test_quarter_can_cross_the_calendar_year(self):
		self.assertEqual(
			quarter_bounds("2026-01-15", fiscal_start_month=11),
			(date(2025, 11, 1), date(2026, 1, 31)),
		)

	def test_saved_period_snaps_and_clears_the_other_picker(self):
		monthly = saved_period("Monthly", "2026-11-26", "2026-01-01", None)
		self.assertEqual(monthly["from_date"], date(2026, 11, 1))
		self.assertEqual(monthly["to_date"], date(2026, 11, 30))
		self.assertIsNone(monthly["target_quarter"])
		quarter = saved_period("Quarterly", "2026-11-01", None, "2026-05-02")
		self.assertEqual(quarter["from_date"], date(2026, 4, 1))
		self.assertIsNone(quarter["target_month"])
		with self.assertRaises(TargetError):
			saved_period("Monthly", None, None, None)


class TestAchievement(unittest.TestCase):
	def test_credit_notes_subtract_either_sign(self):
		total = (
			signed_amount(10000, 0)
			+ signed_amount(-1500, 1)
			+ signed_amount(200, 1)
		)
		self.assertEqual(total, 8300)

	def test_status_follows_the_period(self):
		self.assertEqual(
			achievement_figures(100, 100, "2026-11-01", "2026-11-30", "2026-11-15")["status"],
			"Achieved",
		)
		self.assertEqual(
			achievement_figures(100, 69.99, "2026-11-01", "2026-11-30", "2026-11-15")["status"],
			"In Progress",
		)
		self.assertEqual(
			achievement_figures(100, 40, "2026-10-01", "2026-10-31", "2026-11-01")["status"],
			"Not Achieved",
		)
		self.assertEqual(
			achievement_figures(100, 0, "2026-12-01", "2026-12-31", "2026-11-26")["status"],
			"In Progress",
		)
		gap = achievement_figures(100, 125, "2026-11-01", "2026-11-30", "2026-11-26")
		self.assertEqual(gap["gap"], -25)
		self.assertEqual(gap["achievement_pct"], 125)

	def test_colour_bands(self):
		self.assertEqual(indicator_colour(69.99), "red")
		self.assertEqual(indicator_colour(70), "orange")
		self.assertEqual(indicator_colour(99.99), "orange")
		self.assertEqual(indicator_colour(100), "green")
		self.assertEqual(indicator_colour(140), "green")

	def test_item_group_children_and_brand_filter_the_lines(self):
		rows = achievement_for_targets(
			[
				target(name="all"),
				target(name="group", item_group="Spices"),
				target(name="brand", brand="SK Gourmet"),
				target(name="other-company", company="AJ Enterprises"),
			],
			[
				line(amount=40000),
				line(amount=10000, item_group="Blended Spices", brand="Other", posting_date="2026-11-12"),
				line(amount=-5000, is_return=1, posting_date="2026-11-20"),
				line(amount=99999, company="AJ Enterprises"),
				line(amount=8000, posting_date="2026-12-01"),
			],
			{"Spices": {"Spices", "Whole Spices", "Blended Spices"}},
			"2026-11-26",
		)
		self.assertEqual(rows["all"]["achieved_amount"], 45000)
		self.assertEqual(rows["group"]["achieved_amount"], 45000)
		self.assertEqual(rows["brand"]["achieved_amount"], 35000)
		self.assertEqual(rows["other-company"]["achieved_amount"], 99999)
		self.assertEqual(rows["all"]["status"], "In Progress")

	def test_quantity_uses_stock_uom_and_subtracts_returns(self):
		self.assertEqual(line_qty(line(qty=2, stock_qty=10, uom="Box", stock_uom="Kg"), "Kg"), 10)
		self.assertEqual(line_qty(line(qty=2, stock_qty=10, uom="Box", stock_uom="Kg"), "Box"), 2)
		self.assertEqual(line_qty(line(qty=2, stock_qty=10, uom="Box", stock_uom="Kg"), "Nos"), 0)
		rows = achievement_for_targets(
			[target(target_qty=20, uom="Kg")],
			[line(qty=-4, stock_qty=-4, is_return=1)],
			{},
			"2026-11-26",
		)
		self.assertEqual(rows["CPT-2026-00001"]["achieved_qty"], -4)


class TestDuplicatesAndBulk(unittest.TestCase):
	def test_overlap_is_the_same_customer_filter_and_dates(self):
		rows = [
			{"name": "A", "from_date": "2026-11-01", "to_date": "2026-11-30", "item_group": "", "brand": ""},
			{
				"name": "B",
				"from_date": "2026-10-01",
				"to_date": "2026-12-31",
				"item_group": "Spices",
				"brand": "",
			},
		]
		self.assertEqual(
			[row["name"] for row in find_overlap(rows, "2026-11-01", "2026-11-30", "", "", None)],
			["A"],
		)
		self.assertEqual(find_overlap(rows, "2026-11-01", "2026-11-30", "Spices", "", "B"), [])
		self.assertEqual(find_overlap(rows, "2026-12-01", "2026-12-31", "", "", None), [])

	def test_bulk_rows_skip_blanks_and_reject_duplicates(self):
		cleaned = clean_bulk_rows(
			[
				{"customer": "", "target_amount": ""},
				{"customer": "AJ Traders", "target_amount": "25000", "target_qty": "", "uom": ""},
				{"customer": "Blank Shop", "target_amount": 0},
				{"customer": "  ", "target_amount": None},
			]
		)
		self.assertEqual(cleaned, [
			{
				"customer": "AJ Traders",
				"target_amount": 25000.0,
				"target_qty": None,
				"uom": None,
				"sales_person": None,
			}
		])
		plan = plan_bulk(cleaned, {"AJ Traders": "CPT-2026-00008"})
		self.assertEqual(plan[0]["action"], "update")
		self.assertEqual(plan[0]["existing"], "CPT-2026-00008")
		with self.assertRaises(TargetError):
			clean_bulk_rows(
				[
					{"customer": "AJ Traders", "target_amount": 1},
					{"customer": "AJ Traders", "target_amount": 2},
				]
			)
		with self.assertRaises(TargetError):
			clean_bulk_rows([{"customer": "AJ Traders", "target_amount": 5, "target_qty": 3}])


class TestReport(unittest.TestCase):
	def test_total_is_the_sum_and_a_sales_user_sees_only_their_own(self):
		viewer = {"user": "priya@example.com", "roles": ["Sales User"], "sales_persons": ["Priya"]}
		built = build_report(
			[
				target(name="own", target_amount=100, sales_person="Priya"),
				target(
					name="other",
					customer="Other Shop",
					customer_name="Other Shop",
					target_amount=50,
					sales_person="Amit",
					sales_user="amit@example.com",
					owner="manager@example.com",
				),
			],
			[line(amount=80, customer="AJ Traders"), line(amount=50, customer="Other Shop")],
			{},
			{"company": "Melliflous Foods (OPC) Pvt Ltd", "from_date": "2026-11-01", "to_date": "2026-11-30"},
			viewer,
			"2026-11-26",
			"INR",
		)
		self.assertEqual([row["customer"] for row in built["rows"]], ["AJ Traders", "Total"])
		total = built["rows"][-1]
		self.assertEqual(total["target_amount"], 100)
		self.assertEqual(total["achieved_amount"], 80)
		self.assertEqual(total["achievement_pct"], 80)
		self.assertEqual(total["colour"], "orange")
		self.assertTrue(total["is_total"])
		self.assertEqual(built["chart"]["type"], "bar")
		self.assertEqual(built["chart"]["data"]["datasets"][0]["name"], "Target")
		self.assertEqual(built["chart"]["data"]["datasets"][1]["values"], [80])
		self.assertNotIn("Total", built["chart"]["data"]["labels"])
		labels = [column["label"] for column in built["columns"]]
		self.assertEqual(
			labels,
			["Customer", "Territory", "Sales Person", "Period", "Target", "Achieved", "Gap", "Achievement %", "Status"],
		)

	def test_manager_sees_every_row(self):
		built = build_report(
			[target(name="one", target_amount=10), target(name="two", customer="B", customer_name="B", target_amount=10)],
			[],
			{},
			{"company": "Melliflous Foods (OPC) Pvt Ltd"},
			{"user": "boss@example.com", "roles": ["Sales Manager"], "sales_persons": []},
			"2026-11-26",
		)
		self.assertEqual(len(built["rows"]), 3)
		self.assertTrue(can_edit_targets(["Sales Manager"]))
		self.assertFalse(can_edit_targets(["Sales User"], "priya@example.com"))
		self.assertTrue(can_edit_targets([], "Administrator"))


class TestDeskLinks(unittest.TestCase):
	def test_workspace_merge_appends_once(self):
		merged = merge_workspace(
			[{"label": "Team Files", "type": "Page"}],
			[{"id": "qa6", "type": "shortcut", "data": {"shortcut_name": "Team Files", "col": 12}}],
			[{"label": "Team Files", "link_to": "team-files"}],
			col=12,
		)
		self.assertTrue(merged["changed"])
		self.assertEqual(merged["shortcuts"][0]["label"], "Team Files")
		self.assertEqual(
			[row["label"] for row in merged["shortcuts"][1:]],
			["Customer Targets", "Target vs Achievement"],
		)
		again = merge_workspace(merged["shortcuts"], merged["content"], merged["links"])
		self.assertFalse(again["changed"])
		self.assertEqual(len(again["shortcuts"]), 3)

	def test_sidebar_links_are_added_rows(self):
		missing = missing_sidebar_links([("DocType", "Customer")])
		self.assertEqual([row["link_to"] for row in missing], [link["link_to"] for link in TARGET_LINKS])
		self.assertTrue(all(row["added"] == 1 for row in missing))
		self.assertEqual(missing_sidebar_links((row["link_type"], row["link_to"]) for row in TARGET_LINKS), [])

	def test_shipped_files_and_hooks(self):
		doctype = json.loads(
			(
				PACKAGE
				/ "melliflous_branding"
				/ "doctype"
				/ "customer_primary_target"
				/ "customer_primary_target.json"
			).read_text()
		)
		fields = {row["fieldname"] for row in doctype["fields"]}
		for name in (
			"customer",
			"company",
			"period_type",
			"target_month",
			"from_date",
			"to_date",
			"target_amount",
			"target_qty",
			"uom",
			"item_group",
			"brand",
			"sales_person",
			"sales_user",
			"remarks",
			"achieved_amount",
			"gap",
			"achievement_pct",
			"status",
		):
			self.assertIn(name, fields)
		self.assertNotIn("is_submittable", doctype)
		roles = {row["role"]: row for row in doctype["permissions"]}
		self.assertEqual(roles["Sales Manager"]["write"], 1)
		self.assertEqual(roles["Sales Manager"]["create"], 1)
		self.assertEqual(roles["Sales User"]["read"], 1)
		self.assertEqual(roles["Sales User"]["report"], 1)
		self.assertEqual(roles["Sales User"]["write"], 0)
		self.assertEqual(roles["System Manager"]["delete"], 1)

		report = json.loads(
			(
				PACKAGE
				/ "melliflous_branding"
				/ "report"
				/ "customer_target_vs_achievement"
				/ "customer_target_vs_achievement.json"
			).read_text()
		)
		self.assertEqual(report["report_type"], "Script Report")
		self.assertEqual(report["ref_doctype"], "Customer Primary Target")
		self.assertEqual(
			{row["role"] for row in report["roles"]},
			{"System Manager", "Sales Manager", "Sales User"},
		)

		self.assertFalse(
			(PACKAGE / "melliflous_branding" / "workspace" / "quick_actions" / "quick_actions.json").exists()
		)
		sidebar = json.loads(
			(PACKAGE / "melliflous_branding" / "sidebar" / "melliflous_branding" / "melliflous_branding.json").read_text()
		)
		items = {row["label"]: row for row in sidebar["items"]}
		self.assertEqual(items["Customer Targets"]["link_to"], "Customer Primary Target")
		self.assertEqual(items["Target vs Achievement"]["link_type"], "Report")
		self.assertEqual(items["Team Files"]["link_to"], "team-files")

		self.assertIn(
			"melliflous_branding.target_records.refresh_primary_targets",
			hooks.scheduler_events["daily"],
		)
		self.assertIn("Customer Primary Target", hooks.permission_query_conditions)
		self.assertIn("melliflous_branding.patches.v0_5.ensure_customer_targets", (PACKAGE / "patches.txt").read_text())
		self.assertIn("melliflous_branding.patches.v0_4.show_team_files", (PACKAGE / "patches.txt").read_text())


if __name__ == "__main__":
	unittest.main()
