# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Recipe pages, the register, and the stock-entry fields. No recipe is seeded."""

import os

import frappe
from frappe.modules.import_file import import_file_by_path

from melliflous_branding.recipe_records import ensure_recipe_places


def execute():
	module = os.path.join(frappe.get_app_path("melliflous_branding"), "melliflous_branding")
	for relative in (
		"doctype/recipe/recipe.json",
		"doctype/recipe_ingredient/recipe_ingredient.json",
		"doctype/recipe_packaging/recipe_packaging.json",
		"doctype/recipe_sub_assembly/recipe_sub_assembly.json",
		"page/recipes/recipes.json",
		"page/convert_stock/convert_stock.json",
		"report/production_conversion_register/production_conversion_register.json",
		"workspace/recipes/recipes.json",
	):
		path = os.path.join(module, relative)
		if os.path.exists(path):
			import_file_by_path(path, force=True, ignore_version=True)
	ensure_recipe_places()
