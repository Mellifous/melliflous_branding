# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Import distributor DocTypes, the 360 page, the follow-up report, and the desk links.

`bench migrate` also syncs these JSON files. This patch imports them once more
so a site that already had the app picks them up, then makes sure the Quick
Actions workspace and the Melliflous Branding sidebar list them.
"""

import os

import frappe
from frappe.modules.import_file import import_file_by_path

from melliflous_branding.install import after_migrate


def execute():
	module = os.path.join(frappe.get_app_path("melliflous_branding"), "melliflous_branding")
	for relative in (
		"doctype/distributor_visit_stock/distributor_visit_stock.json",
		"doctype/distributor_stock_statement_item/distributor_stock_statement_item.json",
		"doctype/distributor_complaint_attachment/distributor_complaint_attachment.json",
		"doctype/distributor_profile/distributor_profile.json",
		"doctype/distributor_visit/distributor_visit.json",
		"doctype/distributor_stock_statement/distributor_stock_statement.json",
		"doctype/distributor_complaint/distributor_complaint.json",
		"page/distributor_360/distributor_360.json",
		"report/distributor_follow_up/distributor_follow_up.json",
		"workspace/quick_actions/quick_actions.json",
		"sidebar/melliflous_branding/melliflous_branding.json",
	):
		path = os.path.join(module, relative)
		if os.path.exists(path):
			import_file_by_path(path, force=True, ignore_version=True)
	after_migrate()
