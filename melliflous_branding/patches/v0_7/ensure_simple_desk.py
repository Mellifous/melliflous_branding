# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Import Quick Invoice, Melliflous Settings, and apply simple mode once.

`bench migrate` also syncs these JSON files. This patch imports them again so a
site that already had the app picks them up, then hides the extra workspaces.
Running it twice does not add a second page or forget a workspace someone hid
before simple mode was turned on.
"""

import os

import frappe
from frappe.modules.import_file import import_file_by_path

from melliflous_branding.simple_records import ensure_simple_desk


def execute():
	module = os.path.join(frappe.get_app_path("melliflous_branding"), "melliflous_branding")
	for relative in (
		"doctype/melliflous_settings/melliflous_settings.json",
		"page/quick_invoice/quick_invoice.json",
	):
		path = os.path.join(module, relative)
		if os.path.exists(path):
			import_file_by_path(path, force=True, ignore_version=True)
	ensure_simple_desk()
