# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Division records, the division link, and a fresh pass over the GST auto flags."""

import os

import frappe
from frappe.modules.import_file import import_file_by_path

from melliflous_branding.division_records import ensure_divisions
from melliflous_branding.invoice_admin_records import keep_einvoice_manual


def execute():
	module = os.path.join(frappe.get_app_path("melliflous_branding"), "melliflous_branding")
	path = os.path.join(module, "doctype/division/division.json")
	if os.path.exists(path):
		import_file_by_path(path, force=True, ignore_version=True)
	ensure_divisions()
	keep_einvoice_manual()
