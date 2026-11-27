# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Add the Customer documents table and the billing-status fields once."""

import os

import frappe
from frappe.modules.import_file import import_file_by_path

from melliflous_branding.customer_records import ensure_customer_fields


def execute():
	module = os.path.join(frappe.get_app_path("melliflous_branding"), "melliflous_branding")
	for relative in (
		"doctype/customer_document/customer_document.json",
		"doctype/distributor_benefit/distributor_benefit.json",
	):
		path = os.path.join(module, relative)
		if os.path.exists(path):
			import_file_by_path(path, force=True, ignore_version=True)
	ensure_customer_fields()
