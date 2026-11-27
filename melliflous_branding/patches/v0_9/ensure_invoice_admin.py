# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Invoice Admin, rename, delete rights, and manual e-invoice.

The owner's user is added only when a System Manager with the email
akash@skgourmetspices.com already exists. Otherwise only Administrator is seeded.
Add further users on Melliflous Settings, Invoice Admin Users.
"""

import os

import frappe
from frappe.modules.import_file import import_file_by_path

from melliflous_branding.invoice_admin_records import ensure_invoice_admin


def execute():
	module = os.path.join(frappe.get_app_path("melliflous_branding"), "melliflous_branding")
	for relative in (
		"doctype/invoice_admin_user/invoice_admin_user.json",
		"doctype/invoice_audit_log/invoice_audit_log.json",
		"doctype/melliflous_settings/melliflous_settings.json",
	):
		path = os.path.join(module, relative)
		if os.path.exists(path):
			import_file_by_path(path, force=True, ignore_version=True)
	ensure_invoice_admin()
