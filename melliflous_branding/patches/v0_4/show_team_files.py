# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Reload Team Files as a system page so /desk/team-files stays on that page.

v16 writes a module shell in front of an ordinary page, which turned the
address into /desk/melliflous-branding/team-files and left the body empty when
that segment was not a page the desk could open. A system page keeps the bare
desk address. The JSON is imported again because the earlier patch already ran.
"""

import os

import frappe
from frappe.modules.import_file import import_file_by_path


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
