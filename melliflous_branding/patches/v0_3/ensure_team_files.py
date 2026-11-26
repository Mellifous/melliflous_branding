# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Team Files page, the Home/Team Files folder, and the Raven User role.

`bench migrate` also imports the JSON files. This patch imports them once more
so a site that already had the app picks up the page, and creates the folder
and the Raven role grants even if the after_migrate hook is skipped.
"""

import os

import frappe
from frappe.modules.import_file import import_file_by_path

from melliflous_branding.install import after_migrate


def execute():
	module = os.path.join(frappe.get_app_path("melliflous_branding"), "melliflous_branding")
	for relative in (
		"page/team_files/team_files.json",
		"workspace/quick_actions/quick_actions.json",
		"sidebar/melliflous_branding/melliflous_branding.json",
	):
		path = os.path.join(module, relative)
		if os.path.exists(path):
			import_file_by_path(path, force=True, ignore_version=True)
	after_migrate()
