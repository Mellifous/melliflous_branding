# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import unittest

from melliflous_branding.branding import (
	FALLBACK_TITLE,
	HOME_SCREEN_NAME,
	PWA_MARKER,
	TILE_TONES,
	choose_company,
	companies_for_user,
	display_title,
	inject_head_markup,
	picker_visible,
	tone_for,
)

COMPANIES = [
	"AJ Enterprises",
	"Melliflous Beverages",
	"Melliflous Foods (OPC) Pvt Ltd",
	"Melliflous International Multi Trade Pvt Ltd",
]


class TestCompanyTitle(unittest.TestCase):
	def test_blank_company_uses_the_group_name(self):
		self.assertEqual(display_title(None), FALLBACK_TITLE)
		self.assertEqual(display_title("  "), FALLBACK_TITLE)
		self.assertEqual(FALLBACK_TITLE, "Melliflous Group")

	def test_saved_company_is_the_title(self):
		self.assertEqual(display_title(COMPANIES[2]), COMPANIES[2])

	def test_picker_needs_more_than_one_company(self):
		self.assertFalse(picker_visible([]))
		self.assertFalse(picker_visible([COMPANIES[0]]))
		self.assertTrue(picker_visible(COMPANIES))

	def test_choose_keeps_a_saved_default_that_is_still_allowed(self):
		self.assertEqual(choose_company(COMPANIES[3], COMPANIES), COMPANIES[3])

	def test_choose_drops_a_default_the_user_cannot_use(self):
		self.assertIsNone(choose_company("Some Other Co", COMPANIES))

	def test_single_company_is_shown_even_without_a_saved_default(self):
		self.assertEqual(choose_company(None, [COMPANIES[0]]), COMPANIES[0])

	def test_several_companies_and_no_default_stay_unset(self):
		self.assertIsNone(choose_company("", COMPANIES))
		self.assertEqual(display_title(choose_company("", COMPANIES)), FALLBACK_TITLE)


class TestPermittedCompanies(unittest.TestCase):
	def test_no_user_permission_lists_every_readable_company(self):
		self.assertEqual(
			companies_for_user([], list(reversed(COMPANIES))),
			sorted(COMPANIES, key=str.casefold),
		)

	def test_user_permissions_restrict_the_list(self):
		allowed = [COMPANIES[0], COMPANIES[2]]
		self.assertEqual(companies_for_user(allowed, COMPANIES), sorted(allowed, key=str.casefold))

	def test_permissions_are_kept_when_company_cannot_be_listed(self):
		# No read on Company still leaves the User Permission documents.
		self.assertEqual(companies_for_user([COMPANIES[1], COMPANIES[1]], []), [COMPANIES[1]])

	def test_blank_and_duplicate_names_are_dropped(self):
		self.assertEqual(companies_for_user(["", COMPANIES[0], COMPANIES[0]], COMPANIES), [COMPANIES[0]])


class TestTileTones(unittest.TestCase):
	def test_department_colours(self):
		expected = {
			"Accounts": "green",
			"Selling": "orange",
			"Field Sales": "orange",
			"CRM": "purple",
			"Stock": "blue",
			"Buying": "teal",
			"Manufacturing": "brown",
			"HR": "pink",
			"Payroll": "yellow",
			"India Compliance": "red",
			"GST": "red",
		}
		for label, tone in expected.items():
			self.assertEqual(tone_for(label), tone, label)

	def test_app_tiles_on_the_v16_home(self):
		self.assertEqual(tone_for("ERPNext"), "brand")
		self.assertEqual(tone_for("Frappe HR"), "pink")
		self.assertEqual(tone_for("Frappe CRM"), "purple")
		self.assertEqual(tone_for("Distributor 360"), "brand")
		self.assertEqual(tone_for("  india compliance "), "red")

	def test_framework_tile_stays_neutral(self):
		self.assertIsNone(tone_for("Frappe Framework"))
		self.assertIsNone(tone_for(""))
		self.assertIn("ERPNext", TILE_TONES)


class TestPwaHead(unittest.TestCase):
	def test_injects_icon_manifest_and_home_screen_title(self):
		html = "<html><head><title>Frappe</title></head><body></body></html>"
		updated = inject_head_markup(html, COMPANIES[1])
		self.assertIn(f"<title>{COMPANIES[1]}</title>", updated)
		self.assertIn('rel="apple-touch-icon"', updated)
		self.assertIn('href="/files/melliflous_icon_512.png"', updated)
		self.assertIn('rel="manifest"', updated)
		self.assertIn('href="/assets/melliflous_branding/manifest.json"', updated)
		self.assertIn(f'name="apple-mobile-web-app-title" content="{HOME_SCREEN_NAME}"', updated)
		self.assertIn(PWA_MARKER, updated)

	def test_blank_company_titles_the_shell_with_the_group_name(self):
		html = "<html><head><title>Frappe</title></head></html>"
		updated = inject_head_markup(html, "  ")
		self.assertIn(f"<title>{FALLBACK_TITLE}</title>", updated)

	def test_escapes_a_company_name(self):
		html = "<html><head><title>Frappe</title></head></html>"
		updated = inject_head_markup(html, "A & B <Co>")
		self.assertIn("<title>A &amp; B &lt;Co&gt;</title>", updated)
		self.assertNotIn("<title>A & B", updated)

	def test_does_not_inject_twice(self):
		once = inject_head_markup("<html><head><title>Frappe</title></head></html>", COMPANIES[0])
		twice = inject_head_markup(once, "Other")
		self.assertEqual(once, twice)
		self.assertEqual(twice.count("apple-touch-icon"), 2)


if __name__ == "__main__":
	unittest.main()
