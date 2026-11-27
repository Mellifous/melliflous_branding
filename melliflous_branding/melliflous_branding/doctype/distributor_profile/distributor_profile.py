# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

from frappe.model.document import Document

from melliflous_branding.distributor_records import link_existing_activity, prepare_profile


class DistributorProfile(Document):
	def before_validate(self):
		prepare_profile(self)

	def on_update(self):
		link_existing_activity(self)
