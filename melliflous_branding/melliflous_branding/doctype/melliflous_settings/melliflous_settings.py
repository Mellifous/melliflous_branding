# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import frappe
from frappe.model.document import Document


class MelliflousSettings(Document):
	def on_update(self):
		if getattr(frappe.flags, "melliflous_settings_sync", None):
			return
		from melliflous_branding.simple_records import sync_simple_desk

		sync_simple_desk()
