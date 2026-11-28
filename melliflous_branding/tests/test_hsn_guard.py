# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import json
import unittest
from datetime import date
from pathlib import Path

from melliflous_branding.gst_checks import (
	EWAY_BIHAR_INTRA,
	EWAY_INTER_STATE,
	check_gstin,
	format_issues,
	gstin_check_digit,
	issue_fingerprint,
	review_document,
	review_item,
	state_code_from_text,
)
from melliflous_branding.hsn_catalog import (
	CATEGORIES,
	MIN_HSN_DIGITS,
	clean_hsn,
	find_rate_rule,
	fixture_records,
	hsn_fits,
	match_categories,
	rate_conflict,
)

PACKAGE = Path(__file__).resolve().parents[1]
TODAY = date(2026, 11, 27)
BIHAR = "10AAAAA0000A1Z" + gstin_check_digit("10AAAAA0000A1Z")
MAHARASHTRA = "27AAPFU0939F1ZV"


def _line(**overrides):
	row = {
		"item_code": "JEERA",
		"item_name": "Cumin Whole",
		"item_group": "Whole Spices",
		"hsn": "09093129",
		"qty": 2,
		"rate": 100,
		"price_list_rate": 100,
		"valuation_rate": 80,
		"uom": "Kg",
		"stock_uom": "Kg",
		"conversion_factor": 1,
		"item_tax_template": "GST 5% - MIMT",
		"tax_rate": 5,
	}
	row.update(overrides)
	return row


def _invoice(**overrides):
	row = {
		"doctype": "Sales Invoice",
		"posting_date": "2026-11-27",
		"today": TODAY,
		"company_gstin": BIHAR,
		"party_gstin": BIHAR,
		"gst_category": "Registered Regular",
		"party_type": "Company",
		"place_of_supply": "10-Bihar",
		"billing_state": "Bihar",
		"has_address": True,
		"grand_total": 210,
		"items": [_line()],
		"tax_heads": ["CGST", "SGST"],
		"known_hsn": {"09093129", "09041130", "19021900", "21061000", "11061090"},
	}
	row.update(overrides)
	return row


def _codes(result):
	return [issue["code"] for issue in result["issues"]]


class TestCatalogue(unittest.TestCase):
	def test_codes_are_six_or_eight_digits_and_cite_the_notification(self):
		self.assertGreaterEqual(MIN_HSN_DIGITS, 6)
		for category in CATEGORIES:
			digits = clean_hsn(category["hsn"])
			self.assertIn(len(digits), {6, 8}, category["name"])
			self.assertTrue(category["source"])
			self.assertTrue(category["rates"] == () or set(category["rates"]) <= {0, 5})
		self.assertIn("9/2025", find_rate_rule("09093129")["source"])
		self.assertEqual(find_rate_rule("09093129")["rates"], (5,))
		self.assertEqual(find_rate_rule("09093121")["rates"], (0,))
		self.assertEqual(find_rate_rule("09101110")["rates"], (0,))
		self.assertEqual(find_rate_rule("09103030")["rates"], (5,))
		self.assertEqual(find_rate_rule("11061010")["rates"], (0,))
		self.assertEqual(find_rate_rule("11061090")["kind"], "packing")
		self.assertEqual(find_rate_rule("19021900")["rates"], (5,))
		self.assertEqual(find_rate_rule("21039040")["rates"], (5,))
		self.assertEqual(find_rate_rule("21061000")["rates"], (5,))
		self.assertEqual(find_rate_rule("12081000")["rates"], (5,))
		self.assertEqual(find_rate_rule("21069020")["kind"], "excluded")
		self.assertTrue(rate_conflict("090931"))
		self.assertFalse(rate_conflict("09093129"))

	def test_names_land_on_the_tariff_item(self):
		def hsn(name):
			found = match_categories(name)
			self.assertEqual(len(found), 1, name)
			return found[0]["hsn"]

		self.assertEqual(hsn("Cumin Whole 500g"), "09093129")
		self.assertEqual(hsn("Jeera Powder"), "09093200")
		self.assertEqual(hsn("Black Pepper"), "09041130")
		self.assertNotEqual(hsn("Black Pepper"), "09041110")
		self.assertEqual(hsn("Long Pepper"), "09041110")
		self.assertEqual(hsn("Black Pepper Powder"), "09041200")
		self.assertEqual(hsn("Red Chilli"), "09042110")
		self.assertEqual(hsn("Chilli Powder"), "09042211")
		self.assertEqual(hsn("Coriander"), "09092190")
		self.assertEqual(hsn("Dhania Powder"), "09092200")
		self.assertEqual(hsn("Turmeric Powder"), "09103030")
		self.assertEqual(hsn("Fresh Turmeric"), "09103010")
		self.assertEqual(hsn("Dry Ginger"), "09101120")
		self.assertEqual(hsn("Ginger Powder"), "09101210")
		self.assertEqual(hsn("Soya Chunks"), "21061000")
		self.assertEqual(hsn("Soya Flour"), "12081000")
		self.assertEqual(hsn("Besan"), "11061090")
		self.assertEqual(hsn("Seviyan"), "19021900")
		self.assertEqual(len(match_categories("Soya")), 2)
		self.assertEqual(len(match_categories("Calcutta Special")), 0)
		pepper = match_categories("Black Pepper")[0]
		self.assertFalse(hsn_fits(pepper, "09041110"))
		self.assertTrue(hsn_fits(pepper, "09041140"))
		masala = match_categories("Garam Masala")[0]
		self.assertEqual(masala["hsn"], "09109100")
		self.assertFalse(masala["ambiguous"])
		self.assertTrue(hsn_fits(masala, "09109100"))
		self.assertFalse(hsn_fits(masala, "21039040"))
		suggested = review_item(item_name="Garam Masala", hsn="")
		self.assertEqual(suggested["suggestion"]["hsn"], "09109100")

	def test_fixture_matches_the_catalogue_and_does_not_touch_items(self):
		rows = fixture_records()
		self.assertEqual([row["category_name"] for row in rows], [row["name"] for row in CATEGORIES])
		blob = json.dumps(rows)
		self.assertNotIn("gst_hsn_code", blob)
		self.assertNotIn("Item", blob)


class TestGstin(unittest.TestCase):
	def test_published_example_and_bihar_state(self):
		self.assertEqual(gstin_check_digit("27AAPFU0939F1Z"), "V")
		self.assertIsNone(check_gstin(MAHARASHTRA))
		self.assertIsNone(check_gstin(BIHAR))
		self.assertEqual(BIHAR[:2], "10")
		self.assertIsNotNone(check_gstin(BIHAR[:-1] + "A"))
		self.assertIsNotNone(check_gstin("10AAAAA0000A1Z"))
		self.assertEqual(state_code_from_text("10-Bihar"), "10")
		self.assertEqual(state_code_from_text("Goalpara"), "")


class TestItemReview(unittest.TestCase):
	def test_clean_cumin_is_quiet(self):
		result = review_item(
			item_name="Cumin Whole",
			item_code="JEERA",
			hsn="09093129",
			templates=[{"name": "GST 5% - MIMT", "rate": 5}],
			known_hsn={"09093129"},
		)
		self.assertEqual(result["issues"], [])

	def test_missing_short_and_old_rate_are_warnings_with_a_suggestion(self):
		missing = review_item(item_name="Cumin Whole", hsn="", templates=[{"rate": 5}])
		self.assertIn("hsn_missing", _codes(missing))
		self.assertEqual(missing["suggestion"]["hsn"], "09093129")
		self.assertEqual(missing["issues"][0]["severity"], "warning")
		short = review_item(item_name="Cumin Whole", hsn="0909", templates=[{"rate": 5}])
		self.assertIn("hsn_short", _codes(short))
		self.assertNotIn("error", {issue["severity"] for issue in short["issues"]})
		old = review_item(
			item_name="Pasta",
			hsn="19021900",
			templates=[{"name": "GST 12% - MIMT", "rate": 12}],
			known_hsn={"1902"},
		)
		self.assertIn("tax_mismatch", _codes(old))
		self.assertIn("5%", old["issues"][0]["suggestion"])
		seed = review_item(item_name="Cumin", hsn="09093121", templates=[{"rate": 0}])
		self.assertIn("hsn_mismatch", _codes(seed))
		pepper = review_item(item_name="Black Pepper", hsn="09041110", templates=[{"rate": 5}])
		self.assertIn("hsn_mismatch", _codes(pepper))
		self.assertEqual(pepper["suggestion"]["hsn"], "09041130")
		besan = review_item(item_name="Besan", hsn="11061010", templates=[{"rate": 0}])
		self.assertEqual(besan["suggestion"]["hsn"], "11061090")
		loose = review_item(item_name="Besan", hsn="11061090", templates=[{"rate": 0}], known_hsn={"11061090"})
		self.assertEqual(loose["issues"], [])
		labelled = review_item(item_name="Besan", hsn="11061090", templates=[{"rate": 5}], known_hsn={"11061090"})
		self.assertEqual(labelled["issues"], [])
		letters = review_item(item_name="Cumin", hsn="09AB", templates=[{"rate": 5}])
		self.assertEqual(letters["issues"][0]["severity"], "warning")
		strict = review_item(item_name="Cumin", hsn="09AB", templates=[{"rate": 5}], strict=True)
		self.assertEqual(strict["issues"][0]["severity"], "error")

	def test_soya_and_wellness_stay_ambiguous(self):
		soya = review_item(item_name="Soya", hsn="")
		self.assertIsNone(soya["suggestion"]["hsn"])
		self.assertEqual(len(soya["suggestion"]["choices"]), 2)
		chunks = review_item(item_name="Soya Chunks", hsn="12081000", templates=[{"rate": 5}])
		self.assertIn("hsn_mismatch", _codes(chunks))
		self.assertEqual(chunks["suggestion"]["hsn"], "21061000")
		flour = review_item(item_name="Soya Flour", hsn="12081000", templates=[{"rate": 5}], known_hsn={"12081000"})
		self.assertEqual(flour["issues"], [])
		wellness = match_categories("Sunkeera Daily")[0]
		self.assertEqual(wellness["hsn"], "21069099")
		self.assertFalse(wellness["ambiguous"])
		self.assertTrue(hsn_fits(wellness, "21069099"))
		self.assertFalse(hsn_fits(wellness, "30049011"))
		self.assertFalse(hsn_fits(wellness, "21069020"))
		other = match_categories("Ayurvedic tonic")[0]
		self.assertTrue(other["ambiguous"])
		pan = review_item(item_name="Sunkeera", hsn="21069020", templates=[{"rate": 5}])
		self.assertIn("hsn_mismatch", _codes(pan))
		self.assertEqual(pan["suggestion"]["hsn"], "21069099")


class TestDocumentReview(unittest.TestCase):
	def test_a_bihar_invoice_with_the_right_tax_is_quiet(self):
		result = review_document(_invoice())
		self.assertEqual(result["issues"], [])
		self.assertTrue(result["can_save"])

	def test_igst_inside_bihar_and_cgst_outside_are_warnings(self):
		intra = review_document(_invoice(tax_heads=["IGST"]))
		self.assertIn("tax_type", _codes(intra))
		self.assertIn("Bihar", intra["issues"][0]["title"] + intra["issues"][0]["detail"])
		self.assertTrue(intra["can_save"])
		bare = review_document(_invoice(tax_heads=[]))
		self.assertIn("tax_type", _codes(bare))
		inter = review_document(
			_invoice(
				place_of_supply="27-Maharashtra",
				billing_state="Maharashtra",
				party_gstin=MAHARASHTRA,
				tax_heads=["CGST", "SGST"],
				grand_total=40000,
			)
		)
		self.assertIn("tax_type", _codes(inter))
		self.assertNotIn("eway_missing", _codes(inter))

	def test_eway_uses_the_bihar_limit_inside_the_state(self):
		self.assertEqual(EWAY_BIHAR_INTRA, 100000)
		self.assertEqual(EWAY_INTER_STATE, 50000)
		under = review_document(_invoice(grand_total=100000))
		self.assertNotIn("eway_missing", _codes(under))
		over = review_document(_invoice(grand_total=100001))
		self.assertIn("eway_missing", _codes(over))
		self.assertIn("will not generate", over["issues"][0]["suggestion"])
		interstate = review_document(
			_invoice(
				place_of_supply="27-Maharashtra",
				billing_state="Maharashtra",
				party_gstin=MAHARASHTRA,
				tax_heads=["IGST"],
				grand_total=50001,
			)
		)
		self.assertIn("eway_missing", _codes(interstate))
		exact = review_document(
			_invoice(
				place_of_supply="27-Maharashtra",
				billing_state="Maharashtra",
				party_gstin=MAHARASHTRA,
				tax_heads=["IGST"],
				grand_total=50000,
			)
		)
		self.assertNotIn("eway_missing", _codes(exact))
		quoted = review_document(_invoice(doctype="Quotation", grand_total=200000))
		self.assertNotIn("eway_missing", _codes(quoted))

	def test_blocks_only_a_broken_value(self):
		result = review_document(
			_invoice(
				items=[
					_line(qty=-1, rate=-5, hsn="AB12", item_code="JEERA"),
					_line(item_code="JEERA", qty=0, rate=0),
				],
				party_gstin="10AAAAA0000A1ZA",
				posting_date="2026-12-01",
				has_address=False,
				place_of_supply="",
			)
		)
		self.assertFalse(result["can_save"])
		self.assertIn("qty_negative", _codes(result))
		self.assertIn("rate_negative", _codes(result))
		self.assertIn("hsn_format", _codes(result))
		self.assertIn("gstin_format", _codes(result))
		self.assertTrue(all(issue["severity"] == "error" for issue in result["errors"]))
		self.assertIn("qty_zero", _codes(result))
		self.assertIn("rate_zero", _codes(result))
		self.assertIn("duplicate_item", _codes(result))
		self.assertIn("date_future", _codes(result))
		self.assertIn("address_missing", _codes(result))
		self.assertIn("place_missing", _codes(result))
		text = format_issues(result["issues"])
		self.assertIn("JEERA", text)
		self.assertEqual(issue_fingerprint(result["warnings"]), issue_fingerprint(list(result["warnings"])))

	def test_price_date_uom_and_b2b_gstin(self):
		cheap = review_document(_invoice(items=[_line(rate=70, valuation_rate=100, price_list_rate=100)]))
		self.assertIn("rate_below_valuation", _codes(cheap))
		self.assertIn("rate_below_price_list", _codes(cheap))
		close = review_document(_invoice(items=[_line(rate=90, price_list_rate=100, valuation_rate=80)]))
		self.assertNotIn("rate_below_price_list", _codes(close))
		uom = review_document(_invoice(items=[_line(uom="Box", stock_uom="Kg", conversion_factor=1)]))
		self.assertIn("uom_mismatch", _codes(uom))
		converted = review_document(_invoice(items=[_line(uom="Box", stock_uom="Kg", conversion_factor=10)]))
		self.assertNotIn("uom_mismatch", _codes(converted))
		old_month = review_document(_invoice(posting_date="2026-10-15"))
		self.assertIn("date_previous_gst", _codes(old_month))
		self.assertIn("passed", old_month["issues"][0]["detail"])
		early = review_document(_invoice(posting_date="2026-10-15", today=date(2026, 11, 5)))
		self.assertIn("11th", early["issues"][0]["detail"])
		missing_gstin = review_document(_invoice(party_gstin="", gst_category="Registered Regular"))
		self.assertIn("gstin_missing", _codes(missing_gstin))
		unregistered = review_document(_invoice(party_gstin="", gst_category="Unregistered", party_type="Individual"))
		self.assertNotIn("gstin_missing", _codes(unregistered))
		mismatch = review_document(_invoice(party_gstin=MAHARASHTRA, billing_state="Bihar", place_of_supply="10-Bihar"))
		self.assertIn("gstin_state", _codes(mismatch))
		lead = review_document(
			_invoice(doctype="Quotation", quotation_to="Lead", party_gstin="", gst_category="", party_type="")
		)
		self.assertNotIn("gstin_missing", _codes(lead))


class TestWiring(unittest.TestCase):
	def test_hooks_add_the_guard_without_removing_invoice_admin(self):
		hooks = (PACKAGE / "hooks.py").read_text()
		self.assertIn("invoice_admin_records.guard_rename", hooks)
		self.assertIn("invoice_number_records.validate_invoice_number", hooks)
		self.assertIn("recipe_records.guard_recipe_stock", hooks)
		self.assertIn("20261127e", hooks)
		self.assertIn("20261127hsn", hooks)
		self.assertIn("hsn_records.validate_item", hooks)
		self.assertIn("hsn_records.validate_document", hooks)
		self.assertIn("hsn_guard.js", hooks)
		self.assertNotIn("hsn_guard.css", hooks)
		patch = (PACKAGE / "patches" / "v0_12" / "ensure_hsn_catalog.py").read_text()
		self.assertNotIn("gst_hsn_code", patch)
		self.assertIn("ensure_hsn_catalog", patch)
		records = (PACKAGE / "hsn_records.py").read_text()
		self.assertIn("only_for", records)
		self.assertIn("ignore_hsn_guard", records)
		self.assertNotIn("auto_generate_e_invoice", records)
		self.assertNotIn("auto_generate_e_waybill", records)
		script = (PACKAGE / "public" / "js" / "hsn_guard.js").read_text()
		self.assertIn("Save anyway", script)
		self.assertIn("Apply and save", script)
		self.assertIn("min-height: 44px", script)
		self.assertIn("font-size: 16px", script)
		page = (PACKAGE / "melliflous_branding" / "page" / "hsn_audit" / "hsn_audit.js").read_text()
		self.assertIn("hsn-audit", page)
		self.assertIn("apply_selected", script)
		self.assertIn("System Manager", script)
		fixture = json.loads((PACKAGE / "fixtures" / "hsn_category_map.json").read_text())
		self.assertEqual(fixture, fixture_records())
		self.assertEqual((PACKAGE / "__init__.py").read_text().strip(), '__version__ = "0.8.2"')
