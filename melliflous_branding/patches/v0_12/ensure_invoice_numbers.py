# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Per-company invoice prefix, and the Invoice No field on Sales Invoice.

The number the user types becomes the Sales Invoice name. Set the prefix and
the optional starting number on Melliflous Settings, Invoice numbers.
"""

import os

import frappe
from frappe.modules.import_file import import_file_by_path

from melliflous_branding.invoice_number_records import ensure_invoice_numbers


def execute():
	module = os.path.join(frappe.get_app_path("melliflous_branding"), "melliflous_branding")
	for relative in (
		"doctype/sales_invoice_series/sales_invoice_series.json",
		"doctype/melliflous_settings/melliflous_settings.json",
	):
		path = os.path.join(module, relative)
		if os.path.exists(path):
			import_file_by_path(path, force=True, ignore_version=True)
	ensure_invoice_numbers()
