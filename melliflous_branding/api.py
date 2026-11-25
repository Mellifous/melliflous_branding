# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Set the user's default company the same way Session Defaults does."""

from __future__ import annotations

import frappe
from frappe import _

from melliflous_branding.branding import display_title
from melliflous_branding.companies import get_permitted_companies


@frappe.whitelist(methods=["POST"])
def set_default_company(company: str) -> dict:
	"""Store `company` as this user's default company.

	Session Defaults writes the same DefaultValue key (`company`) via
	`frappe.defaults.set_user_default`. New documents and reports read it back
	through `get_user_default`. The company must be one this user is allowed to
	use.
	"""
	company = (company or "").strip()
	if not company:
		frappe.throw(_("Select a company"))

	allowed = get_permitted_companies()
	if company not in allowed:
		frappe.throw(
			_("You cannot use company {0}").format(company),
			frappe.PermissionError,
		)

	frappe.defaults.set_user_default("company", company)
	# The desk boot cache copies user defaults. Drop it so the next full load
	# reads the value just saved. The open page updates its own boot in the browser.
	frappe.cache.hdel("bootinfo", frappe.session.user)
	return {"company": company, "title": display_title(company)}
