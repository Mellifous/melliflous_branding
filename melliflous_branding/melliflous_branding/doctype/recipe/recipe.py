# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

from frappe.model.document import Document

from melliflous_branding.recipe_records import prepare_doc, sync_bom


class Recipe(Document):
	def validate(self):
		prepare_doc(self)

	def on_update(self):
		sync_bom(self)
