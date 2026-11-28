# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

from frappe.model.document import Document

from melliflous_branding.van_records import post_report_stock, prepare_report


class VanDailyReport(Document):
	def validate(self):
		prepare_report(self)

	def on_submit(self):
		post_report_stock(self)
