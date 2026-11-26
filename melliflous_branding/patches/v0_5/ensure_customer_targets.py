# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Import the customer target DocType, report, and Quick Actions links.

`bench migrate` also syncs these JSON files. This patch imports them once more
so a site that already had the app picks them up, then adds the same links to
Selling and CRM when those modules are installed.
"""

import os

import frappe
from frappe.modules.import_file import import_file_by_path

from melliflous_branding.install import after_migrate


def execute():
	module = os.path.join(frappe.get_app_path("melliflous_branding"), "melliflous_branding")
	for relative in (
		"doctype/customer_primary_target/customer_primary_target.json",
		"report/customer_target_vs_achievement/customer_target_vs_achievement.json",
		"workspace/quick_actions/quick_actions.json",
		"sidebar/melliflous_branding/melliflous_branding.json",
	):
		path = os.path.join(module, relative)
		if os.path.exists(path):
			import_file_by_path(path, force=True, ignore_version=True)
	after_migrate()
