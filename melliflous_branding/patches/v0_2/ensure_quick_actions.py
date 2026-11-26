# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Import Quick Actions pages, workspace, and sidebar on the first migrate after this release.

`bench migrate` also syncs these JSON files on every run. This patch imports them
once more so a site that already had the app still receives them with this update.
"""

import os

import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	module = os.path.join(frappe.get_app_path("melliflous_branding"), "melliflous_branding")
	for relative in (
		"page/add_team_member/add_team_member.json",
		"page/give_task/give_task.json",
		"page/quick_lead/quick_lead.json",
		"page/my_tasks/my_tasks.json",
		"workspace/quick_actions/quick_actions.json",
		"sidebar/melliflous_branding/melliflous_branding.json",
	):
		path = os.path.join(module, relative)
		if os.path.exists(path):
			import_file_by_path(path, force=True, ignore_version=True)
