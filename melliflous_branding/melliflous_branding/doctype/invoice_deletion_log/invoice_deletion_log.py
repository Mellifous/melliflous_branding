# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from melliflous_branding.invoice_admin import deletion_log_block


class InvoiceDeletionLog(Document):
	def validate(self):
		message = deletion_log_block(getattr(frappe.session, "user", None), is_new=self.is_new(), deleting=False)
		if message:
			frappe.throw(_(message), frappe.PermissionError)

	def on_trash(self):
		message = deletion_log_block(getattr(frappe.session, "user", None), is_new=False, deleting=True)
		if message:
			frappe.throw(_(message), frappe.PermissionError)
