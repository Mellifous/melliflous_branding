# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

from frappe.model.document import Document

from melliflous_branding.distributor_records import prepare_complaint


class DistributorComplaint(Document):
	def before_validate(self):
		prepare_complaint(self)
