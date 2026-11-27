# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import json
import unittest
from pathlib import Path

from melliflous_branding.desk import HIDDEN_WORKSPACES
from melliflous_branding.recipes import (
	MANUFACTURE,
	REPACK,
	RecipeError,
	batch_action,
	bom_document,
	build_conversion,
	default_bom_flag,
	entry_purpose,
	may_undo,
	missing_sidebar_links,
	prepare_recipe,
	register_rows,
	report_filters,
	restrict_filters,
	should_revise_bom,
	stock_entry_fields,
)

PACKAGE = Path(__file__).resolve().parents[1]
COMPANY = "Test Company"
DIVISION = "Test Division"
DIVISIONS = [{"name": DIVISION, "company": COMPANY, "is_active": 1}]
EXAMPLE = "EXAMPLE — do not use (test only)"


def blend(**overrides):
	raw = {
		"recipe_name": EXAMPLE,
		"company": COMPANY,
		"division": DIVISION,
		"item": "EXAMPLE Finished Kg",
		"qty": 1,
		"uom": "Kg",
		"process_loss_percentage": 2,
		"ingredients": [
			{"item_code": "EXAMPLE Spice A", "percentage": 40, "uom": "Kg"},
			{"item_code": "EXAMPLE Spice B", "percentage": 35, "uom": "Kg"},
			{"item_code": "EXAMPLE Spice C", "percentage": 25, "uom": "Kg"},
		],
		"packaging": [{"item_code": "EXAMPLE Pouch Pack", "qty": 1, "uom": "Nos"}],
	}
	raw.update(overrides)
	return prepare_recipe(raw, {"division_rows": DIVISIONS})


def packed(bulk):
	return prepare_recipe(
		{
			"recipe_name": "EXAMPLE — packed, test only",
			"company": COMPANY,
			"division": DIVISION,
			"item": "EXAMPLE Pouch",
			"qty": 1,
			"uom": "Nos",
			"sub_assemblies": [{"sub_recipe": bulk["recipe_name"], "qty": 0.1, "uom": "Kg"}],
			"packaging": [
				{"item_code": "EXAMPLE Pouch Pack", "qty": 1, "uom": "Nos"},
				{"item_code": "EXAMPLE Label", "qty": 1, "uom": "Nos"},
			],
		},
		{
			"division_rows": DIVISIONS,
			"sub_items": {bulk["recipe_name"]: bulk["item"]},
			"sub_boms": {bulk["recipe_name"]: "BOM-EXAMPLE-001"},
			"sub_children": {},
		},
	)


class TestRecipeSheet(unittest.TestCase):
	def test_percentages_add_loss_and_packs_do_not(self):
		recipe = blend()
		quantities = {row["item_code"]: row["qty"] for row in recipe["ingredients"]}
		self.assertAlmostEqual(quantities["EXAMPLE Spice A"], 0.408)
		self.assertAlmostEqual(quantities["EXAMPLE Spice B"], 0.357)
		self.assertAlmostEqual(quantities["EXAMPLE Spice C"], 0.255)
		self.assertAlmostEqual(sum(quantities.values()), 1.02)
		self.assertAlmostEqual(recipe["loss_free_qty"], 1)
		self.assertEqual(recipe["packaging"][0]["qty"], 1)
		self.assertEqual(recipe["company"], COMPANY)
		self.assertEqual(recipe["division"], DIVISION)
		bom = bom_document(recipe)
		self.assertEqual(bom["process_loss_percentage"], 0)
		self.assertEqual(bom["set_qty_based_on_percentage"], 0)
		self.assertEqual(bom["company"], COMPANY)
		self.assertEqual(bom["division"], DIVISION)
		self.assertEqual(entry_purpose(recipe), MANUFACTURE)

	def test_a_sub_recipe_keeps_its_bom_and_is_not_exploded(self):
		bulk = blend(packaging=[])
		pouch = packed(bulk)
		self.assertEqual(entry_purpose(pouch), REPACK)
		bom = bom_document(pouch, {bulk["recipe_name"]: "BOM-EXAMPLE-001"})
		sub = next(row for row in bom["items"] if row["item_code"] == "EXAMPLE Finished Kg")
		self.assertEqual(sub["bom_no"], "BOM-EXAMPLE-001")
		self.assertEqual(sub["do_not_explode"], 1)
		self.assertEqual(sub["qty"], 0.1)
		label = next(row for row in bom["items"] if row["item_code"] == "EXAMPLE Label")
		self.assertEqual(label["qty"], 1)
		self.assertEqual(label["bom_no"], "")

	def test_bad_sheets_are_refused(self):
		with self.assertRaises(RecipeError):
			blend(ingredients=[
				{"item_code": "EXAMPLE Spice A", "percentage": 40, "uom": "Kg"},
				{"item_code": "EXAMPLE Spice B", "percentage": 30, "uom": "Kg"},
			])
		with self.assertRaises(RecipeError):
			blend(ingredients=[
				{"item_code": "EXAMPLE Spice A", "percentage": 100, "uom": "Kg"},
				{"item_code": "EXAMPLE Spice B", "qty": 1, "uom": "Kg"},
			])
		with self.assertRaises(RecipeError):
			blend(ingredients=[{"item_code": "EXAMPLE Finished Kg", "percentage": 100, "uom": "Kg"}])
		with self.assertRaises(RecipeError):
			blend(ingredients=[], packaging=[])
		with self.assertRaises(RecipeError):
			blend(division="")
		with self.assertRaises(RecipeError):
			blend(division="Other Division")
		with self.assertRaises(RecipeError):
			prepare_recipe(
				{
					"recipe_name": EXAMPLE,
					"company": COMPANY,
					"division": DIVISION,
					"item": "EXAMPLE Finished Kg",
					"qty": 1,
					"uom": "Kg",
					"ingredients": [{"item_code": "EXAMPLE Spice A", "percentage": 100, "uom": "Kg"}],
				},
				{"division_rows": DIVISIONS, "stock_uoms": {"EXAMPLE Finished Kg": "Nos"}},
			)
		with self.assertRaises(RecipeError):
			prepare_recipe(
				{
					"recipe_name": EXAMPLE,
					"company": COMPANY,
					"division": DIVISION,
					"item": "EXAMPLE Pouch",
					"qty": 1,
					"uom": "Nos",
					"sub_assemblies": [{"sub_recipe": "Child", "qty": 1, "uom": "Kg"}],
				},
				{
					"division_rows": DIVISIONS,
					"sub_items": {"Child": "EXAMPLE Bulk"},
					"sub_boms": {"Child": "BOM-1"},
					"sub_children": {"Child": [EXAMPLE]},
				},
			)

	def test_a_new_bom_is_only_the_default_when_the_item_has_none(self):
		first = bom_document(blend())
		changed = bom_document(blend(process_loss_percentage=5))
		self.assertTrue(should_revise_bom(first, changed))
		self.assertFalse(should_revise_bom(first, bom_document(blend())))
		self.assertEqual(default_bom_flag(False, True), 0)
		self.assertEqual(default_bom_flag(False, False), 1)
		self.assertEqual(default_bom_flag(True, True), 1)


class TestConvertStock(unittest.TestCase):
	def setUp(self):
		self.recipe = blend()
		self.recipe["bom"] = "BOM-EXAMPLE-001"

	def convert(self, **overrides):
		request = {
			"company": COMPANY,
			"division": DIVISION,
			"qty": 10,
			"source_warehouses": ["Store A", "Store B"],
			"target_warehouse": "Finished",
			"division_rows": DIVISIONS,
			"roles": ["Stock User"],
			"submitting": True,
		}
		request.update(overrides)
		bins = overrides.pop("bins", None)
		if "bins" in request:
			bins = request.pop("bins")
		if bins is None:
			bins = [
				{"item_code": "EXAMPLE Spice A", "warehouse": "Store A", "actual_qty": 1, "valuation_rate": 10},
				{"item_code": "EXAMPLE Spice A", "warehouse": "Store B", "actual_qty": 1, "valuation_rate": 20},
				{"item_code": "EXAMPLE Spice B", "warehouse": "Store A", "actual_qty": 100, "valuation_rate": 5},
				{"item_code": "EXAMPLE Spice C", "warehouse": "Store A", "actual_qty": 100, "valuation_rate": 8},
				{"item_code": "EXAMPLE Pouch Pack", "warehouse": "Store A", "actual_qty": 100, "valuation_rate": 1},
			]
		return build_conversion(self.recipe, request, bins)

	def test_short_stock_is_blocked_unless_a_manager_confirms(self):
		blocked = self.convert()
		spice = next(row for row in blocked["preview"]["lines"] if row["item_code"] == "EXAMPLE Spice A")
		self.assertAlmostEqual(spice["required"], 4.08)
		self.assertAlmostEqual(spice["available"], 2)
		self.assertAlmostEqual(spice["shortfall"], 2.08)
		self.assertIn("EXAMPLE Spice A", blocked["preview"]["block"])
		self.assertFalse(blocked["preview"]["can_override"])
		self.assertEqual(blocked["document"]["confirm_shortfall"], 0)
		draft = self.convert(submitting=False)
		self.assertEqual(draft["preview"]["block"], "")
		self.assertTrue(draft["preview"]["has_shortfall"])
		manager = self.convert(roles=["Manufacturing Manager"], confirm_shortfall=1)
		self.assertEqual(manager["preview"]["block"], "")
		self.assertEqual(manager["document"]["confirm_shortfall"], 1)
		unconfirmed = self.convert(roles=["System Manager"])
		self.assertIn("Tick convert despite short stock", unconfirmed["preview"]["block"])
		covered = self.convert(lines=[{"item_code": "EXAMPLE Spice A", "actual_qty": 2}])
		self.assertEqual(covered["preview"]["block"], "")
		self.assertFalse(covered["preview"]["has_shortfall"])

	def test_the_stock_entry_is_a_manufacture_for_the_company_and_division(self):
		result = self.convert(
			roles=["Manufacturing Manager"],
			confirm_shortfall=1,
			actual_output=9,
			batch_no="BATCH-1",
			manufacturing_date="2026-11-01",
			expiry_date="2027-11-01",
		)
		document = result["document"]
		self.assertEqual(document["doctype"], "Stock Entry")
		self.assertEqual(document["purpose"], MANUFACTURE)
		self.assertEqual(document["company"], COMPANY)
		self.assertEqual(document["division"], DIVISION)
		self.assertEqual(document["recipe"], EXAMPLE)
		self.assertEqual(document["from_bom"], 1)
		self.assertEqual(document["use_multi_level_bom"], 0)
		self.assertEqual(document["bom_no"], "BOM-EXAMPLE-001")
		self.assertEqual(document["planned_qty"], 10)
		self.assertEqual(document["fg_completed_qty"], 10)
		self.assertEqual(document["process_loss_qty"], 1)
		self.assertEqual(document["expected_loss_pct"], 2)
		finished = next(row for row in document["items"] if row["is_finished_item"])
		self.assertEqual(finished["item_code"], "EXAMPLE Finished Kg")
		self.assertEqual(finished["qty"], 9)
		self.assertEqual(finished["t_warehouse"], "Finished")
		self.assertIsNone(finished["s_warehouse"])
		self.assertEqual(finished["batch_no"], "BATCH-1")
		self.assertEqual(finished["use_serial_batch_fields"], 1)
		consumed = [row for row in document["items"] if row["item_code"] == "EXAMPLE Spice A"]
		self.assertAlmostEqual(sum(row["qty"] for row in consumed), 4.08)
		self.assertEqual(consumed[0]["s_warehouse"], "Store A")
		self.assertEqual(consumed[0]["qty"], 1)
		self.assertEqual(consumed[1]["s_warehouse"], "Store B")
		self.assertIsNone(consumed[0]["t_warehouse"])
		better = self.convert(actual_output=12, roles=["Manufacturing Manager"], confirm_shortfall=1)
		self.assertEqual(better["document"]["fg_completed_qty"], 12)
		self.assertEqual(better["document"]["process_loss_qty"], 0)
		with self.assertRaises(RecipeError):
			self.convert(company="Other Company")
		inactive = dict(self.recipe)
		inactive["is_active"] = 0
		with self.assertRaises(RecipeError):
			build_conversion(inactive, {"qty": 1, "company": COMPANY}, [])
		missing = dict(self.recipe)
		missing["bom"] = ""
		with self.assertRaises(RecipeError):
			build_conversion(missing, {"qty": 1, "company": COMPANY, "division": DIVISION, "division_rows": DIVISIONS}, [])

	def test_batches_and_undo(self):
		with self.assertRaises(RecipeError):
			self.convert(manufacturing_date="2026-11-02", expiry_date="2026-11-01", batch_no="B")
		with self.assertRaises(RecipeError):
			self.convert(expiry_date="2027-01-01")
		self.assertEqual(batch_action(None, "EXAMPLE Finished Kg", "2026-11-01", ""), "create")
		self.assertEqual(
			batch_action({"item": "EXAMPLE Finished Kg", "name": "B"}, "EXAMPLE Finished Kg", "", ""),
			"use",
		)
		self.assertEqual(
			batch_action(
				{"item": "EXAMPLE Finished Kg", "name": "B", "expiry_date": ""},
				"EXAMPLE Finished Kg",
				"",
				"2027-01-01",
			),
			"update",
		)
		with self.assertRaises(RecipeError):
			batch_action({"item": "Other", "name": "B"}, "EXAMPLE Finished Kg", "", "")
		self.assertTrue(may_undo({"cancel": 1, "delete": 0}))
		self.assertFalse(may_undo({"cancel": 0, "delete": 1}))
		with self.assertRaises(RecipeError):
			self.convert(batch_items=["EXAMPLE Finished Kg"])
		refused = self.convert(roles=["Stock User"], confirm_shortfall=1)
		self.assertIn("Only a Manufacturing Manager", refused["preview"]["block"])
		self.assertEqual(refused["document"]["confirm_shortfall"], 0)


class TestRegister(unittest.TestCase):
	def entry(self, **overrides):
		row = {
			"name": "STE-0001",
			"posting_date": "2026-11-10",
			"purpose": MANUFACTURE,
			"recipe": EXAMPLE,
			"company": COMPANY,
			"division": DIVISION,
			"docstatus": 1,
			"planned_qty": 10,
			"expected_loss_pct": 2,
			"loss_free_qty": 10,
			"items": [
				{"item_code": "EXAMPLE Spice A", "qty": 10.2, "uom": "Kg", "s_warehouse": "Store A", "basic_amount": 102, "recipe_line_type": "Ingredient"},
				{"item_code": "EXAMPLE Finished Kg", "qty": 10, "uom": "Kg", "t_warehouse": "Finished", "is_finished_item": 1, "recipe_line_type": "Finished"},
			],
		}
		row.update(overrides)
		return row

	def test_yield_loss_and_cost(self):
		rows = register_rows([self.entry()])
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["yield_pct"], 100)
		self.assertEqual(rows[0]["actual_loss_pct"], 2)
		self.assertEqual(rows[0]["loss_vs_expected"], 0)
		self.assertEqual(rows[0]["total_cost"], 102)
		self.assertEqual(rows[0]["cost_per_unit"], 10.2)
		self.assertEqual(rows[0]["company"], COMPANY)
		self.assertEqual(rows[0]["division"], DIVISION)
		short = register_rows([
			self.entry(
				items=[
					{"item_code": "EXAMPLE Spice A", "qty": 11, "s_warehouse": "Store A", "basic_amount": 110, "recipe_line_type": "Ingredient"},
					{"item_code": "EXAMPLE Finished Kg", "qty": 9, "uom": "Kg", "t_warehouse": "Finished", "is_finished_item": 1},
				]
			)
		])
		self.assertEqual(short[0]["yield_pct"], 90)
		self.assertEqual(short[0]["actual_loss_pct"], 10)
		self.assertEqual(short[0]["loss_vs_expected"], 8)
		self.assertAlmostEqual(short[0]["cost_per_unit"], 12.22)

	def test_filters_keep_cancelled_rows_out_until_asked(self):
		rows = [
			self.entry(),
			self.entry(name="STE-OLD", posting_date="2026-10-01", division="Other"),
			self.entry(name="STE-CANCEL", docstatus=2),
		]
		self.assertEqual([row["stock_entry"] for row in register_rows(rows, {"division": DIVISION})], ["STE-0001"])
		self.assertEqual(
			[row["stock_entry"] for row in register_rows(rows, {"from_date": "2026-11-01", "to_date": "2026-11-30"})],
			["STE-0001"],
		)
		self.assertEqual(len(register_rows(rows, {"include_cancelled": 1, "division": DIVISION})), 2)
		filters = report_filters({"company": COMPANY, "recipe": EXAMPLE, "from_date": "2026-11-01"})
		self.assertIn(["docstatus", "!=", 2], filters)
		self.assertIn(["recipe", "=", EXAMPLE], filters)
		narrowed = restrict_filters({}, [COMPANY], [DIVISION])
		self.assertEqual(narrowed["company"], COMPANY)
		self.assertEqual(narrowed["division"], DIVISION)
		with self.assertRaises(RecipeError):
			restrict_filters({"company": "Other"}, [COMPANY], [])


class TestRecipeFiles(unittest.TestCase):
	def test_nothing_real_is_seeded_and_delete_is_not_granted(self):
		doctype = json.loads((PACKAGE / "melliflous_branding" / "doctype" / "recipe" / "recipe.json").read_text())
		by_role = {row["role"]: row for row in doctype["permissions"]}
		self.assertEqual(by_role["Stock User"]["delete"], 0)
		self.assertEqual(by_role["Manufacturing User"]["delete"], 0)
		self.assertEqual(by_role["Stock Manager"]["delete"], 0)
		self.assertEqual(by_role["System Manager"]["delete"], 1)
		self.assertEqual(by_role["Manufacturing User"]["create"], 0)
		records = (PACKAGE / "recipe_records.py").read_text()
		self.assertNotIn("EXAMPLE", records)
		ensure = records.split("def ensure_recipe_places", 1)[1].split("\ndef ", 1)[0]
		self.assertNotIn('"doctype": "Recipe"', ensure)
		self.assertNotIn("Garam", records)
		convert = records.split("def convert_stock", 1)[1].split("\ndef ", 1)[0]
		self.assertNotIn("ignore_permissions", convert)
		self.assertIn(".submit()", convert)
		cancel = records.split("def cancel_conversion", 1)[1].split("\ndef ", 1)[0]
		self.assertIn(".cancel()", cancel)
		self.assertNotIn(".delete(", cancel)
		self.assertNotIn("Recipe", (PACKAGE / "fixtures" / "custom_field.json").read_text())
		workspace = json.loads(
			(PACKAGE / "melliflous_branding" / "workspace" / "recipes" / "recipes.json").read_text()
		)
		targets = {row.get("link_to") for row in workspace["links"]}
		self.assertIn("recipes", targets)
		self.assertIn("convert-stock", targets)
		self.assertIn("Production Conversion Register", targets)
		self.assertNotIn("Recipes", HIDDEN_WORKSPACES)
		self.assertIn("melliflous_branding.patches.v0_12.ensure_recipes", (PACKAGE / "patches.txt").read_text())
		fields = stock_entry_fields()
		stock_names = {row["fieldname"] for row in fields["Stock Entry"]}
		self.assertIn("division", stock_names)
		self.assertIn("recipe", stock_names)
		self.assertIn("division", {row["fieldname"] for row in fields["BOM"]})
		self.assertEqual(len(missing_sidebar_links([])), 4)
		self.assertEqual(missing_sidebar_links([("Page", "recipes"), ("Page", "convert-stock"), ("DocType", "Recipe"), ("Report", "Production Conversion Register")]), [])
		page = (PACKAGE / "melliflous_branding" / "page" / "convert_stock" / "convert_stock.js").read_text()
		self.assertIn("Undo this conversion", page)
		self.assertIn("Save as draft", page)
		self.assertIn("is-short", (PACKAGE / "public" / "css" / "recipes.css").read_text())
		for path in PACKAGE.rglob("*"):
			if path.suffix not in {".py", ".json", ".js", ".md", ".css"}:
				continue
			if path.name == "test_recipes.py":
				continue
			text = path.read_text(errors="ignore")
			self.assertNotIn("EXAMPLE — do not use", text)


if __name__ == "__main__":
	unittest.main()
