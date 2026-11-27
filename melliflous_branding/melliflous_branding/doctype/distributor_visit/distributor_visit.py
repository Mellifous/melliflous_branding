# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

from frappe.model.document import Document

from melliflous_branding.distributor_records import prepare_visit, sync_profile_visits


class DistributorVisit(Document):
	def before_validate(self):
		prepare_visit(self)

	def on_update(self):
		sync_profile_visits(self.distributor)
		before = self.get_doc_before_save()
		if before and before.distributor and before.distributor != self.distributor:
			sync_profile_visits(before.distributor)

	def on_trash(self):
		sync_profile_visits(self.distributor, exclude=self.name)
