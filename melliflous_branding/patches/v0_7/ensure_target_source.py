# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Add target source fields and Distributor Settings on a site that already has the app."""

import os

import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	module = os.path.join(frappe.get_app_path("melliflous_branding"), "melliflous_branding")
	for relative in (
		"doctype/customer_primary_target/customer_primary_target.json",
		"doctype/distributor_settings/distributor_settings.json",
	):
		path = os.path.join(module, relative)
		if os.path.exists(path):
			import_file_by_path(path, force=True, ignore_version=True)
