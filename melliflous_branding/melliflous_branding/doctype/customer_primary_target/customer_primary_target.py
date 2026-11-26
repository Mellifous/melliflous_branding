# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""One customer's primary sell-in target for a month or a quarter."""

from __future__ import annotations

from frappe.model.document import Document

from melliflous_branding.target_records import prepare_target, refresh_achievement


class CustomerPrimaryTarget(Document):
	def before_validate(self):
		prepare_target(self)

	def onload(self):
		if self.is_new():
			return
		refresh_achievement(self, persist=True)
