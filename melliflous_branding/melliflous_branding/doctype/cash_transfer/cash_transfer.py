# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CashTransfer(Document):
	def validate(self):
		if not (self.to_holder or self.to_bank):
			frappe.throw(_("Choose who receives the cash, or the bank."))
