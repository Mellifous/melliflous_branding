# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import unittest
from datetime import date

from melliflous_branding.quick import (
	ROLE_CHOICES,
	choose_lead_doctype,
	clean_companies,
	clean_priority,
	clean_source,
	guess_role,
	is_overdue,
	is_protected_user,
	next_day,
	phone_links,
	raven_role_targets,
	role_label,
	roles_to_assign,
	safe_role_profile,
	split_name,
)


class TestTeamRules(unittest.TestCase):
	def test_protected_accounts_are_blocked(self):
		self.assertTrue(is_protected_user("Administrator"))
		self.assertTrue(is_protected_user("guest"))
		self.assertFalse(is_protected_user("aj@example.com"))

	def test_split_name(self):
		self.assertEqual(split_name("AJ"), ("AJ", ""))
		self.assertEqual(split_name("Priya Sharma"), ("Priya", "Sharma"))
		self.assertEqual(split_name("A B C"), ("A", "B C"))

	def test_at_least_one_company(self):
		with self.assertRaises(ValueError):
			clean_companies([], "Anything")
		names, default = clean_companies(
			[" Melliflous Beverages ", "Melliflous Beverages", "AJ Enterprises"],
			"AJ Enterprises",
		)
		self.assertEqual(names, ["Melliflous Beverages", "AJ Enterprises"])
		self.assertEqual(default, "AJ Enterprises")

	def test_default_company_must_be_ticked(self):
		names, default = clean_companies(["AJ Enterprises"], "Somewhere else")
		self.assertEqual(names, ["AJ Enterprises"])
		self.assertEqual(default, "AJ Enterprises")

	def test_friendly_jobs(self):
		labels = [choice["label"] for choice in ROLE_CHOICES]
		self.assertEqual(
			labels,
			[
				"Owner / Admin",
				"Accounts",
				"HR",
				"Sales Manager",
				"Sales Rep / Van",
				"Plant / Stock",
				"CRM Sales",
			],
		)
		self.assertEqual(roles_to_assign("owner", {"System Manager", "Sales User"}), ["System Manager"])
		self.assertEqual(roles_to_assign("hr", {"Sales User"}), [])
		self.assertEqual(role_label("plant"), "Plant / Stock")

	def test_profile_cannot_grant_extra_roles(self):
		self.assertIsNone(safe_role_profile("sales_rep", {"Sales": {"Sales User", "System Manager"}}))
		self.assertEqual(safe_role_profile("sales_rep", {"Sales": {"Sales User"}}), "Sales")

	def test_guess_role_prefers_owner(self):
		self.assertEqual(guess_role({"System Manager", "Accounts User"}), "owner")
		self.assertEqual(guess_role({"HR User"}), "hr")
		self.assertEqual(guess_role({"Sales User"}), "sales_rep")
		self.assertIsNone(guess_role({"Employee"}))


class TestRavenRole(unittest.TestCase):
	def test_missing_role_does_nothing(self):
		users = [
			{"name": "aj@example.com", "enabled": 1, "user_type": "System User", "roles": set()},
		]
		self.assertEqual(raven_role_targets(users, role_exists=False), [])

	def test_enabled_desk_users_without_the_role_are_chosen(self):
		users = [
			{"name": "Administrator", "enabled": 1, "user_type": "System User", "roles": set()},
			{"name": "Guest", "enabled": 1, "user_type": "Website User", "roles": set()},
			{"name": "off@example.com", "enabled": 0, "user_type": "System User", "roles": set()},
			{"name": "web@example.com", "enabled": 1, "user_type": "Website User", "roles": set()},
			{
				"name": "has@example.com",
				"enabled": 1,
				"user_type": "System User",
				"roles": {"Raven User", "Sales User"},
			},
			{"name": "new@example.com", "enabled": 1, "user_type": "System User", "roles": {"Sales User"}},
			{"name": "new@example.com", "enabled": 1, "user_type": "System User", "roles": set()},
		]
		self.assertEqual(raven_role_targets(users, role_exists=True), ["new@example.com"])


class TestTaskAndLeadRules(unittest.TestCase):
	def test_priority_and_source_defaults(self):
		self.assertEqual(clean_priority(""), "Medium")
		self.assertEqual(clean_priority("high"), "High")
		with self.assertRaises(ValueError):
			clean_priority("Urgent")
		self.assertEqual(clean_source(None), "Field Visit")
		self.assertEqual(clean_source("phone"), "Phone")

	def test_due_tomorrow(self):
		self.assertEqual(next_day(date(2026, 11, 26)), "2026-11-27")
		self.assertTrue(is_overdue("2026-11-25", "2026-11-26"))
		self.assertFalse(is_overdue("2026-11-26", "2026-11-26"))

	def test_lead_doctype_prefers_crm(self):
		self.assertEqual(choose_lead_doctype({"CRM Lead", "Lead"}), "CRM Lead")
		self.assertEqual(choose_lead_doctype({"Lead"}), "Lead")
		self.assertEqual(choose_lead_doctype(set()), "")

	def test_phone_links(self):
		links = phone_links("98765 43210")
		self.assertEqual(links["tel"], "tel:+919876543210")
		self.assertEqual(links["whatsapp"], "https://wa.me/919876543210")
		already = phone_links("+91 98765 43210")
		self.assertEqual(already["whatsapp"], "https://wa.me/919876543210")
		self.assertEqual(phone_links(""), {"tel": "", "whatsapp": ""})
