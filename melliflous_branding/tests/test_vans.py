# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import unittest
from datetime import date

from melliflous_branding.vans import (
	FORBIDDEN_CODES,
	add_secondary_qty,
	beat_status,
	cash_balances,
	exceptions,
	fleet_overview,
	map_fa_lines,
	material_issue_payload,
	may_delete,
	parse_fa_csv,
	period_bounds,
	place_vans_360_app,
	report_figures,
	report_name,
	report_table,
	reported_vs_invoiced,
	rows_to_csv,
	seed_vans,
	sees_division,
	stock_action,
	transfer_payload,
	validate_report,
	van_access,
)


class TestVans(unittest.TestCase):
	def test_seed_is_the_seven_named_vans_and_never_v04_to_v09(self):
		rows = seed_vans()
		codes = [row["code"] for row in rows]
		self.assertEqual(codes, ["V01", "V02", "V03", "V10", "V11", "V12", "V13"])
		self.assertEqual(rows[0]["area"], "Motihari")
		self.assertEqual(rows[0]["daily_target"], 6500)
		self.assertEqual(rows[3]["daily_target"], 8000)
		self.assertEqual(rows[4]["daily_target"], 10000)
		self.assertEqual(rows[2]["daily_target"], 0)
		self.assertEqual(rows[2]["status"], "Pipeline")
		self.assertFalse(set(codes) & FORBIDDEN_CODES)

	def test_permissions(self):
		self.assertEqual(van_access("Administrator", "", []), "delete")
		self.assertTrue(may_delete("akash@skgourmetspices.com", "akash@skgourmetspices.com", ["System Manager"]))
		self.assertEqual(van_access("Priti Sharma", "priti@skgourmetspices.com", []), "edit")
		self.assertFalse(may_delete("Priti Sharma", "priti@skgourmetspices.com", ["System Manager"]))
		self.assertEqual(van_access("Sasank", "sasank@skgourmetspices.com", []), "read")
		self.assertTrue(sees_division("Sasank", "sasank@skgourmetspices.com", [], "SK Gourmet Spices", "Melliflous"))
		self.assertFalse(sees_division("Sasank", "sasank@skgourmetspices.com", [], "Sunkeera", "Melliflous"))
		self.assertEqual(van_access("accounts@example.com", "", ["Accounts User"]), "none")

	def test_mismatch_second_beat_and_stock_choice(self):
		figures = report_figures(1000, 400, 100, 450, 50)
		self.assertEqual(figures["total_collected"], 500)
		self.assertEqual(figures["mismatch"], 0)
		self.assertEqual(report_name("V01", "2026-11-28", 0), "V01-2026-11-28")
		self.assertEqual(report_name("V01", "2026-11-28", 1), "V01-2026-11-28-2")
		with self.assertRaises(Exception):
			report_name("V01", "2026-11-28", 2)
		validate_report({"van": "V01", "date": "2026-11-28", "worked": "No", "reason": "SR Absent", "entry_mode": "Amount only"}, 0)
		with self.assertRaises(Exception):
			validate_report({"van": "V01", "date": "2026-11-28", "worked": "No", "entry_mode": "Amount only"}, 0)
		self.assertEqual(stock_action("Company Van", "Amount only", [], 0), "pending")
		self.assertEqual(stock_action("Company Van", "Manual SKU", [{"item": "Chilli", "qty": 2}], 0), "material_issue")
		self.assertEqual(stock_action("Distributor Van", "FieldAssist upload", [{"item": "Chilli", "qty": 2}], 0), "secondary")
		self.assertEqual(stock_action("Company Van", "Manual SKU", [{"item": "Chilli", "qty": 2}], 1), "done")

	def test_stock_payloads_and_secondary_sales_do_not_touch_a_ledger(self):
		issue = material_issue_payload("Melliflous", "Van V01", [{"item": "Chilli", "qty": 3, "rate": 10}], "2026-11-28", "V01")
		self.assertEqual(issue["purpose"], "Material Issue")
		self.assertEqual(issue["items"][0]["s_warehouse"], "Van V01")
		move = transfer_payload("Melliflous", "Depot", "Van V01", [{"item": "Chilli", "qty": 5, "rate": 10}], "2026-11-28", "load")
		self.assertEqual(move["purpose"], "Material Transfer")
		self.assertEqual(move["to_warehouse"], "Van V01")
		updated = add_secondary_qty(
			[{"item": "Chilli", "opening_qty": 10, "primary_qty": 0, "secondary_qty": 1, "rate": 20}],
			{"Chilli": 4},
		)
		self.assertEqual(updated[0]["secondary_qty"], 5)
		self.assertEqual(updated[0]["closing_qty"], 5)

	def test_fieldassist_csv_uses_the_remembered_map(self):
		parsed = parse_fa_csv("SKU,Qty,Rate\nChilli Powder,2,50\nUnknown Masala,1,10\n")
		mapped = map_fa_lines(parsed, {"Chilli Powder": "CHILLI"})
		self.assertEqual(mapped["lines"][0]["item"], "CHILLI")
		self.assertEqual(mapped["lines"][0]["amount"], 100)
		self.assertEqual(mapped["missing"], ["Unknown Masala"])

	def test_dashboard_is_one_pass(self):
		vans = [
			{"code": "V01", "name": "V01", "status": "Live", "daily_target": 6500, "area": "Motihari"},
			{"code": "V02", "name": "V02", "status": "Idle", "daily_target": 0, "area": "Ara"},
		]
		reports = [
			{
				"date": "2026-11-02",
				"van": "V01",
				"worked": "Yes",
				"worked_by": "Raju",
				"sales": 1000,
				"target": 6500,
				"cash": 2000,
				"online": 0,
				"credit": 3000,
				"discount": 0,
				"mismatch": 0,
				"counters_visited": 10,
				"productive_counters": 8,
				"new_outlets": 1,
				"cash_held_by": "Raju",
				"beat": "Motihari East",
				"modified": "2026-11-02 18:00:00",
			},
			{
				"date": "2026-11-03",
				"van": "V01",
				"worked": "No",
				"reason": "SR Absent",
				"sales": 0,
				"target": 6500,
				"cash": 0,
				"online": 0,
				"credit": 0,
				"discount": 0,
				"mismatch": 0,
				"counters_visited": 0,
				"productive_counters": 0,
				"new_outlets": 0,
				"modified": "2026-11-03 09:00:00",
			},
		]
		start, end = period_bounds("Custom", date(2026, 11, 3), "2026-11-01", "2026-11-03")
		overview = fleet_overview(vans, reports, date(2026, 11, 3), start, end)
		self.assertEqual(overview["sales"], 1000)
		self.assertEqual(overview["new_outlets"], 1)
		self.assertEqual(overview["vans_logged_today"], 0)
		kinds = {row["kind"] for row in exceptions(vans, reports, start, end)}
		self.assertIn("idle", kinds)
		self.assertIn("absent", kinds)
		self.assertIn("<70% target", kinds)
		balances = cash_balances(reports, [{"from_holder": "Raju", "to_bank": "HDFC", "amount": 500}])
		self.assertEqual({row["holder"]: row["balance"] for row in balances}["Raju"], 1500)
		compared = reported_vs_invoiced(
			reports,
			[{"van": "V01", "posting_date": "2026-11-02", "grand_total": 4800, "docstatus": 1}],
			start,
			end,
		)
		billed = [row for row in compared if row["date"] == "2026-11-02"][0]
		self.assertEqual(billed["invoiced"], 4800)
		self.assertEqual(billed["unbilled"], 0)
		beats = beat_status(
			[{"beat_name": "Motihari East", "van": "V01", "planned_counters": 20, "every_n_days": 1, "active": 1}],
			reports,
			date(2026, 11, 10),
		)
		self.assertEqual(beats[0]["overdue"], 1)
		columns, data = report_table("Van summary", reports, vans, [], [], date(2026, 11, 3))
		self.assertIn("V01", rows_to_csv(columns, data))

	def test_tile_sits_once_beside_the_existing_apps(self):
		placed = place_vans_360_app(
			[{"app_name": "distributor_360", "app_title": "Distributor 360"}],
			"Priti",
			"priti@skgourmetspices.com",
			[],
		)
		self.assertEqual([row["app_title"] for row in placed], ["Distributor 360", "Vans 360"])
		again = place_vans_360_app(placed, "Priti", "priti@skgourmetspices.com", [])
		self.assertEqual(len(again), 2)
		hidden = place_vans_360_app(placed, "accounts@example.com", "", ["Accounts User"])
		self.assertEqual([row["app_title"] for row in hidden], ["Distributor 360"])
		from pathlib import Path

		package = Path(__file__).resolve().parents[1]
		script = (package / "melliflous_branding/page/vans_360/vans_360.js").read_text()
		self.assertIn("vans_dashboard", script)
		self.assertIn("Excel", script)
		self.assertIn("PDF", script)
		self.assertIn("custom_van", (package / "van_records.py").read_text())
		self.assertIn("v0_17.ensure_vans", (package / "patches.txt").read_text())
		self.assertIn("place_vans_boot", (package / "boot.py").read_text())
		self.assertIn("Vans 360", (package / "public/js/desk_theme.js").read_text())


if __name__ == "__main__":
	unittest.main()
