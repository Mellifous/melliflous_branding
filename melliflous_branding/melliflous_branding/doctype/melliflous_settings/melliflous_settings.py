# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MelliflousSettings(Document):
	def validate(self):
		from melliflous_branding.invoice_number import validate_series_settings

		errors = validate_series_settings(self.get("sales_invoice_series") or [])
		if errors:
			frappe.throw(_(errors[0]))

	def on_update(self):
		if getattr(frappe.flags, "melliflous_settings_sync", None):
			return
		from melliflous_branding.invoice_admin_records import keep_einvoice_manual, sync_invoice_admin_roles
		from melliflous_branding.simple_records import sync_simple_desk

		sync_simple_desk()
		sync_invoice_admin_roles()
		keep_einvoice_manual()
