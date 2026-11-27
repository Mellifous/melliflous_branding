# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import json
import unittest
from pathlib import Path

from melliflous_branding import hooks
from melliflous_branding.branding import BRAND_MAROON, BRAND_RED, STATUS_COLOURS, status_colour
from melliflous_branding.desk import (
	HIDDEN_WORKSPACES,
	filter_app_rows,
	filter_desktop_icons,
	filter_dock,
	filter_sidebars,
	plan_workspace_visibility,
	shortcut_kept,
)
from melliflous_branding.invoices import (
	ITEM_TAX_5,
	OUTPUT_GST_5,
	STANDARD_PRICE_LIST,
	InvoiceError,
	choose_price_list,
	choose_taxes_template,
	exclusive_rate,
	invoice_totals,
	price_list_choices,
	validate_draft,
)

PACKAGE = Path(__file__).resolve().parents[1]
PUBLIC = PACKAGE / "public"


class TestStatusColours(unittest.TestCase):
	def test_the_colour_key(self):
		expect = {
			"Draft": "grey",
			"Submitted": "blue",
			"To Deliver": "blue",
			"Open": "blue",
			"Unpaid": "orange",
			"Pending": "orange",
			"To Bill": "orange",
			"To Deliver and Bill": "orange",
			"Overdue": "red",
			"Cancelled": "red",
			"Lost": "red",
			"Expired": "red",
			"Rejected": "red",
			"Paid": "green",
			"Completed": "green",
			"Ordered": "green",
			"Delivered": "green",
			"Active": "green",
			"Return": "purple",
			"Credit Note Issued": "purple",
		}
		for status, colour in expect.items():
			self.assertEqual(status_colour(status), colour, status)
			self.assertEqual(status_colour("  " + status.lower() + "  "), colour, status)

	def test_unknown_status_is_left_alone(self):
		self.assertIsNone(status_colour("Internal Transfer"))
		self.assertIsNone(status_colour(""))
		self.assertIsNone(status_colour(None))
		self.assertIn("Draft", STATUS_COLOURS)


class TestSimpleDesk(unittest.TestCase):
	def test_apps_grid_keeps_the_daily_apps_and_drops_hidden_docks(self):
		original = [
			{
				"app_title": "ERPNext",
				"on_apps_screen": True,
				"sequence_id": 1,
				"dock": [
					{"link_to": "Selling"},
					{"link_to": "Manufacturing"},
					{"link_to": "HR"},
				],
			},
			{"app_title": "Frappe Framework", "on_apps_screen": True, "dock": [{"link_to": "Build"}]},
			{"app_title": "Raven", "on_apps_screen": True, "dock": []},
			{"app_title": "Frappe Drive", "on_apps_screen": True, "dock": []},
			{"app_title": "CRM", "on_apps_screen": True, "dock": []},
			{"app_title": "Frappe HR", "on_apps_screen": True, "sequence_id": 3, "dock": []},
			{"app_title": "Distributor 360", "on_apps_screen": True, "dock": []},
			{"app_title": "Quick Actions", "on_apps_screen": True, "dock": []},
		]
		result = filter_app_rows(original)
		self.assertEqual(len(original[0]["dock"]), 3)
		titles = [row["app_title"] for row in result]
		self.assertEqual(
			titles,
			["ERPNext", "Frappe Framework", "Raven", "Frappe Drive", "CRM", "Frappe HR", "Distributor 360", "Quick Actions"],
		)
		erpnext = result[0]
		self.assertEqual([row["link_to"] for row in erpnext["dock"]], ["Selling", "HR"])
		self.assertTrue(erpnext["on_apps_screen"])
		self.assertFalse(result[1]["on_apps_screen"])
		self.assertEqual(result[1]["dock"], [])
		self.assertTrue(result[2]["on_apps_screen"])
		self.assertEqual(result[5]["sequence_id"], 80)
		again = filter_app_rows(result)
		self.assertEqual([row["link_to"] for row in again[0]["dock"]], ["Selling", "HR"])

	def test_sidebar_hides_shells_and_lowers_hr(self):
		payload = {
			"Manufacturing": {
				"name": "Manufacturing",
				"label": "Manufacturing",
				"items": [{"type": "Link", "label": "Work Order", "link_to": "Work Order"}],
			},
			"Selling": {
				"name": "Selling",
				"label": "Selling",
				"items": [
					{"type": "Section Break", "label": "Sales"},
					{"type": "Link", "label": "Customer", "link_to": "Customer"},
					{"type": "Link", "label": "BOM", "link_to": "Manufacturing"},
					{"type": "Section Break", "label": "Tools"},
				],
			},
			"HR": {
				"name": "HR",
				"label": "HR",
				"items": [
					{"type": "Link", "label": "Attendance", "link_to": "Attendance"},
					{"type": "Link", "label": "Salary Slip", "link_to": "Salary Slip"},
					{"type": "Link", "label": "Employee", "link_to": "Employee"},
				],
			},
		}
		result = filter_sidebars(payload)
		self.assertNotIn("Manufacturing", result)
		labels = [row["label"] for row in result["Selling"]["items"]]
		self.assertEqual(labels, ["Sales", "Customer"])
		hr = [row["link_to"] for row in result["HR"]["items"]]
		self.assertEqual(hr, ["Employee", "Attendance"])
		self.assertEqual(len(payload["Selling"]["items"]), 4)

	def test_dock_and_desktop_icons(self):
		dock = filter_dock({"erpnext": [{"link_to": "Projects"}, {"link_to": "Stock"}, {"link_to": "Leaves"}]})
		self.assertEqual([row["link_to"] for row in dock["erpnext"]], ["Stock", "Leaves"])
		icons = filter_desktop_icons(
			[{"label": "Website"}, {"label": "Selling", "module_name": "Selling"}, "keep"]
		)
		self.assertEqual(icons, [{"label": "Selling", "module_name": "Selling"}, "keep"])

	def test_workspace_hide_is_reversible(self):
		rows = [
			{"name": "Manufacturing", "label": "Manufacturing", "is_hidden": 0},
			{"name": "Selling", "label": "Selling", "is_hidden": 0},
			{"name": "Tools", "label": "Tools", "is_hidden": 1},
		]
		updates, memory = plan_workspace_visibility(rows, True, {})
		self.assertEqual(updates, [{"name": "Manufacturing", "is_hidden": 1}])
		self.assertEqual(memory["Manufacturing"], 0)
		self.assertEqual(memory["Tools"], 1)
		self.assertNotIn("Selling", memory)
		hidden = [
			{"name": "Manufacturing", "label": "Manufacturing", "is_hidden": 1},
			{"name": "Tools", "label": "Tools", "is_hidden": 1},
		]
		restored, forgotten = plan_workspace_visibility(hidden, False, memory)
		self.assertEqual(restored, [{"name": "Manufacturing", "is_hidden": 0}])
		self.assertEqual(forgotten, {})
		again, still = plan_workspace_visibility(rows, True, memory)
		self.assertEqual(again, [{"name": "Manufacturing", "is_hidden": 1}])
		self.assertEqual(still["Tools"], 1)

	def test_shortcut_trim_keeps_the_named_lists(self):
		self.assertTrue(shortcut_kept("Selling", "Quick Invoice"))
		self.assertTrue(shortcut_kept("Selling", "Distributor 360"))
		self.assertFalse(shortcut_kept("Selling", "Sales Partner"))
		self.assertTrue(shortcut_kept("Stock", "Stock Balance"))
		self.assertFalse(shortcut_kept("Buying", "Request for Quotation"))
		self.assertTrue(shortcut_kept("Accounting", "General Ledger"))
		self.assertTrue(shortcut_kept("CRM", "Lead"))
		self.assertIn("Manufacturing", HIDDEN_WORKSPACES)
		self.assertIn("Payroll", HIDDEN_WORKSPACES)


class TestQuickInvoice(unittest.TestCase):
	def test_classic_five_percent_becomes_exclusive(self):
		self.assertEqual(exclusive_rate(100, "Classic Distributor", 5), 95.24)
		self.assertEqual(exclusive_rate("210", "Classic Retailer", "5"), 200.0)
		self.assertEqual(exclusive_rate(100, "Classic MRP", 5.0), 95.24)

	def test_other_rates_and_lists_stay(self):
		self.assertEqual(exclusive_rate(100, "Standard Selling", 5), 100.0)
		self.assertEqual(exclusive_rate(118, "Classic Distributor", 18), 118.0)
		self.assertEqual(exclusive_rate(100, "Classic Distributor", None), 100.0)
		with self.assertRaises(InvoiceError):
			exclusive_rate(-1, "Classic Distributor", 5)

	def test_tax_template_choice(self):
		self.assertEqual(choose_taxes_template([ITEM_TAX_5, ITEM_TAX_5], "Company Default"), OUTPUT_GST_5)
		self.assertEqual(choose_taxes_template([ITEM_TAX_5, "GST 12% - MIMT"], "Company Default"), "Company Default")
		self.assertEqual(choose_taxes_template([ITEM_TAX_5, ""], "Company Default"), "Company Default")
		self.assertEqual(choose_taxes_template([], "Company Default"), "Company Default")
		self.assertIsNone(choose_taxes_template(["Other"], None))

	def test_totals_split_cgst_and_sgst(self):
		totals = invoice_totals([{"qty": 2, "rate": 95.24, "tax_percent": 5}])
		self.assertEqual(totals["taxable"], 190.48)
		self.assertEqual(totals["cgst"], 4.76)
		self.assertEqual(totals["sgst"], 4.76)
		self.assertEqual(totals["grand_total"], 200.0)

	def test_validation_messages(self):
		self.assertEqual(validate_draft({})[0], "Choose a customer first.")
		self.assertIn("Choose a price list.", validate_draft({"customer": "Spice House"}))
		self.assertIn("Add at least one item.", validate_draft({"customer": "Spice House", "price_list": "Classic Distributor"}))
		errors = validate_draft(
			{
				"customer": "Spice House",
				"price_list": "Classic Distributor",
				"items": [{"item_code": "", "qty": 1}, {"item_code": "Chilli", "qty": 0}],
			}
		)
		self.assertIn("Pick an item on row 1.", errors)
		self.assertIn("Enter a quantity greater than zero for Chilli.", errors)
		self.assertEqual(
			validate_draft(
				{
					"customer": "Spice House",
					"price_list": "Classic Distributor",
					"items": [{"item_code": "Chilli", "qty": 2}],
				}
			),
			[],
		)

	def test_price_list_defaults_to_the_customer(self):
		self.assertEqual(choose_price_list("Hotel Rate", []), "Hotel Rate")
		self.assertEqual(choose_price_list("", ["Classic MRP", STANDARD_PRICE_LIST]), STANDARD_PRICE_LIST)
		self.assertEqual(choose_price_list(None, []), STANDARD_PRICE_LIST)
		choices = price_list_choices("Hotel Rate")
		self.assertEqual(choices[0], "Classic Distributor")
		self.assertIn(STANDARD_PRICE_LIST, choices)
		self.assertIn("Hotel Rate", choices)


class TestDeskFiles(unittest.TestCase):
	def test_theme_js_embeds_the_stylesheet(self):
		css = (PUBLIC / "css" / "desk_theme.css").read_text()
		script = (PUBLIC / "js" / "desk_theme.js").read_text()
		marker = "const THEME_CSS = "
		start = script.index(marker) + len(marker)
		end = script.index(";\n", start)
		self.assertEqual(json.loads(script[start:end]), css)
		self.assertIn('const THEME_STYLE_ID = "melliflous-desk-theme"', script)
		self.assertIn("frappe.dom.set_style(THEME_CSS, THEME_STYLE_ID)", script)
		self.assertIn("frappe.dom.set_style", script)
		self.assertIn("page-change.melliflous-desk", script)
		for status in STATUS_COLOURS:
			quoted = json.dumps(status) + ":"
			bare = status + ":"
			self.assertTrue(quoted in script or bare in script, status)
		for name in (
			"Sales Invoice",
			"Quotation",
			"Sales Order",
			"Payment Entry",
			"Delivery Note",
			"Purchase Invoice",
			"Purchase Order",
			"Customer",
			"Lead",
			"Opportunity",
			"Item",
			"Stock Entry",
		):
			self.assertIn(name, script)
		self.assertIn("Good morning", script)
		self.assertIn("New Quick Invoice", script)
		self.assertIn("melliflousClamped", script)
		self.assertIn(".awesomplete > ul", css)
		self.assertIn("min-height: 44px", css)
		self.assertIn("Payment Received", script)
		self.assertIn("Stock Balance", script)

	def test_hooks_bust_the_cache_and_load_the_theme(self):
		joined = "\n".join(hooks.app_include_js)
		self.assertIn("/assets/melliflous_branding/js/desk_theme.js?v=", joined)
		css = "\n".join(hooks.app_include_css)
		self.assertIn("desk_theme.css?v=", css)
		self.assertIn("melliflous_branding.css?v=", css)
		self.assertIn("apply_simple_boot", (PACKAGE / "boot.py").read_text())
		self.assertIn("melliflous_branding.patches.v0_7.ensure_simple_desk", (PACKAGE / "patches.txt").read_text())
		self.assertIn("ensure_simple_desk", (PACKAGE / "install.py").read_text())

	def test_quick_invoice_page_and_settings(self):
		page = json.loads((PACKAGE / "melliflous_branding" / "page" / "quick_invoice" / "quick_invoice.json").read_text())
		self.assertEqual(page["name"], "quick-invoice")
		script = (PACKAGE / "melliflous_branding" / "page" / "quick_invoice" / "quick_invoice.js").read_text()
		self.assertIn('frappe.pages["quick-invoice"].on_page_load', script)
		self.assertIn("Save as Draft", script)
		self.assertIn("Save as Draft Quotation", script)
		self.assertIn("Choose a customer first.", script)
		records = (PACKAGE / "invoice_records.py").read_text()
		self.assertIn("doc.insert()", records)
		self.assertNotIn(".submit(", records)
		settings = json.loads(
			(PACKAGE / "melliflous_branding" / "doctype" / "melliflous_settings" / "melliflous_settings.json").read_text()
		)
		self.assertEqual(settings["issingle"], 1)
		simple = next(row for row in settings["fields"] if row["fieldname"] == "simple_mode")
		self.assertEqual(simple["default"], "1")
		self.assertEqual(simple["label"], "Melliflous Simple Mode")

	def test_distributor_header_uses_the_shared_palette(self):
		stylesheet = (PUBLIC / "css" / "melliflous_branding.css").read_text()
		script = (PACKAGE / "melliflous_branding" / "page" / "distributor_360" / "distributor_360.js").read_text()
		self.assertIn(BRAND_RED, stylesheet)
		self.assertIn(BRAND_MAROON, stylesheet)
		self.assertIn("#C8102E", script)
		self.assertIn("#7A0019", script)
		self.assertIn("frappe.dom.set_style", script)


if __name__ == "__main__":
	unittest.main()
