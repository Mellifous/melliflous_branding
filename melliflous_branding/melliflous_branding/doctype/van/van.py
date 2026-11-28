# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from melliflous_branding.vans import FORBIDDEN_CODES, clean


class Van(Document):
	def validate(self):
		code = clean(self.code).upper()
		if code in FORBIDDEN_CODES:
			frappe.throw(_("{0} must not be created.").format(code))
		self.code = code
