# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Save a recipe as a BOM, and convert stock with a Manufacture or Repack entry."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import today

from melliflous_branding.access import require_desk_user
from melliflous_branding.recipes import (
	RecipeError,
	allocate,
	batch_action,
	bom_document,
	build_conversion,
	default_bom_flag,
	missing_sidebar_links,
	prepare_recipe,
	register_columns,
	register_rows,
	report_filters,
	restrict_filters,
	should_revise_bom,
	shortfall_message,
	stock_entry_fields,
)


def prepare_doc(doc):
	"""Fill calculated quantities, then refuse a recipe that cannot become a BOM."""
	if not doc.get("company"):
		doc.company = frappe.defaults.get_user_default("company")
	raw = _raw_from_doc(doc)
	context = _recipe_context(raw)
	try:
		prepared = prepare_recipe(raw, context)
	except RecipeError as exc:
		frappe.throw(str(exc))
	_write_back(doc, prepared)
	doc.flags.recipe_prepared = prepared
	doc.flags.recipe_context = context


def sync_bom(doc):
	"""Create or revise the BOM behind this recipe. Old BOMs stay, so past stock entries still point at them."""
	if not frappe.db.exists("DocType", "BOM"):
		frappe.throw(_("ERPNext is not installed, so a recipe cannot create a BOM."))
	prepared = getattr(doc.flags, "recipe_prepared", None)
	context = getattr(doc.flags, "recipe_context", None)
	if not prepared:
		prepare_doc(doc)
		prepared = doc.flags.recipe_prepared
		context = doc.flags.recipe_context
	try:
		desired = bom_document(prepared, (context or {}).get("sub_boms"))
	except RecipeError as exc:
		frappe.throw(str(exc))
	current = _current_bom(doc.get("bom"))
	if current and current.docstatus == 0:
		_fill_bom(current, desired)
		current.is_default = default_bom_flag(0, _other_default(desired["item"], current.name))
		current.flags.ignore_permissions = True
		current.save(ignore_permissions=True)
		current.submit()
		_remember(doc, current.name)
		return
	if current and current.docstatus == 1 and not should_revise_bom(_bom_view(current), desired):
		_flag_bom(current, desired)
		_remember(doc, current.name)
		return
	previous_default = bool(current and current.is_default)
	exclude = current.name if current else None
	desired["is_default"] = default_bom_flag(previous_default, _other_default(desired["item"], exclude))
	if not desired.get("is_active", 1):
		desired["is_default"] = 0
	new = _insert_bom(desired)
	if current and current.docstatus == 1:
		frappe.db.set_value(
			"BOM", current.name, {"is_active": 0, "is_default": 0}, update_modified=False
		)
	_remember(doc, new.name)


def guard_recipe_stock(doc, method=None):
	"""Block submit when a recipe conversion is short, unless a manager has confirmed."""
	if not doc or not doc.get("recipe") or int(doc.docstatus or 0) != 1:
		return
	if not frappe.db.exists("DocType", "Bin"):
		return
	lines = []
	warehouses = []
	for row in doc.get("items") or []:
		if row.get("is_finished_item") or not row.get("s_warehouse"):
			continue
		lines.append(
			{
				"item_code": row.item_code,
				"qty": row.qty,
				"required": row.qty,
				"uom": row.uom,
				"line_type": row.get("recipe_line_type") or "Ingredient",
			}
		)
		if row.s_warehouse not in warehouses:
			warehouses.append(row.s_warehouse)
	if not lines or not warehouses:
		return
	rows = allocate(lines, _bins([line["item_code"] for line in lines], warehouses), warehouses)
	message = shortfall_message(
		any(row["shortfall"] > 0 for row in rows),
		frappe.get_roles(),
		doc.get("confirm_shortfall"),
		True,
		rows,
	)
	if message:
		frappe.throw(message, title=_("Not enough stock"))


def ensure_recipe_places():
	"""Custom fields and sidebar links. No recipe and no quantity is created here."""
	_ensure_fields()
	_ensure_sidebar()


@frappe.whitelist()
def list_recipes(company=None, division=None):
	require_desk_user()
	frappe.has_permission("Recipe", "read", throw=True)
	filters = {}
	if company:
		filters["company"] = company
	if division:
		filters["division"] = division
	rows = frappe.get_list(
		"Recipe",
		filters=filters,
		fields=[
			"name",
			"recipe_name",
			"item",
			"item_name",
			"qty",
			"uom",
			"process_loss_percentage",
			"is_active",
			"company",
			"division",
			"bom",
		],
		order_by="recipe_name asc",
		limit_page_length=200,
	)
	return {
		"can_write": bool(frappe.has_permission("Recipe", "write") or frappe.has_permission("Recipe", "create")),
		"recipes": rows,
	}


@frappe.whitelist()
def recipe_detail(name):
	require_desk_user()
	if not name or not frappe.db.exists("Recipe", name):
		frappe.throw(_("That recipe was not found."))
	doc = frappe.get_doc("Recipe", name)
	doc.check_permission("read")
	return _public_recipe(doc)


@frappe.whitelist()
def save_recipe(payload=None):
	require_desk_user()
	data = _object(payload)
	for table in ("ingredients", "packaging", "sub_assemblies"):
		if table in data:
			data[table] = _list(data.get(table))
	name = " ".join(str(data.get("recipe_name") or data.get("name") or "").split())
	if name and frappe.db.exists("Recipe", name):
		doc = frappe.get_doc("Recipe", name)
		doc.check_permission("write")
	else:
		frappe.has_permission("Recipe", "create", throw=True)
		doc = frappe.new_doc("Recipe")
	_apply_payload(doc, data)
	doc.save()
	return _public_recipe(doc)


@frappe.whitelist()
def preview_conversion(
	recipe=None,
	company=None,
	division=None,
	qty=None,
	source_warehouses=None,
	target_warehouse=None,
	actual_output=None,
	lines=None,
	batch_no=None,
	manufacturing_date=None,
	expiry_date=None,
	confirm_shortfall=None,
):
	require_desk_user()
	preview = _build(
		recipe=recipe,
		company=company,
		division=division,
		qty=qty,
		source_warehouses=source_warehouses,
		target_warehouse=target_warehouse,
		actual_output=actual_output,
		lines=lines,
		batch_no=batch_no,
		manufacturing_date=manufacturing_date,
		expiry_date=expiry_date,
		confirm_shortfall=confirm_shortfall,
		submitting=False,
	)["preview"]
	preview.update(_stock_rights())
	return preview


@frappe.whitelist()
def convert_stock(
	recipe=None,
	company=None,
	division=None,
	qty=None,
	source_warehouses=None,
	target_warehouse=None,
	actual_output=None,
	lines=None,
	batch_no=None,
	manufacturing_date=None,
	expiry_date=None,
	confirm_shortfall=None,
	submit=1,
):
	"""Insert a Stock Entry. Submit moves the stock. Save as draft leaves it at docstatus 0."""
	require_desk_user()
	submitting = submit in (1, True, "1", "true", "True")
	built = _build(
		recipe=recipe,
		company=company,
		division=division,
		qty=qty,
		source_warehouses=source_warehouses,
		target_warehouse=target_warehouse,
		actual_output=actual_output,
		lines=lines,
		batch_no=batch_no,
		manufacturing_date=manufacturing_date,
		expiry_date=expiry_date,
		confirm_shortfall=confirm_shortfall,
		submitting=submitting,
	)
	if built["preview"]["block"]:
		frappe.throw(built["preview"]["block"], title=_("Not enough stock"))
	_require_stock_permission(submitting)
	_require_recipe_fields()
	_check_material_batches(built["document"])
	_ensure_finished_batch(built)
	doc = frappe.get_doc(_stock_payload(built["document"]))
	doc.posting_date = today()
	doc.insert()
	if submitting:
		doc.submit()
	preview = built["preview"]
	preview.update(_stock_rights())
	return {"name": doc.name, "docstatus": doc.docstatus, "preview": preview}


@frappe.whitelist()
def cancel_conversion(name):
	"""Undo a conversion by cancelling its Stock Entry. This does not delete it."""
	require_desk_user()
	if not name or not frappe.db.exists("Stock Entry", name):
		frappe.throw(_("That stock entry was not found."))
	doc = frappe.get_doc("Stock Entry", name)
	if not doc.get("recipe"):
		frappe.throw(_("This stock entry was not made from a recipe."))
	doc.check_permission("cancel")
	if int(doc.docstatus or 0) != 1:
		frappe.throw(_("Only a submitted conversion can be undone."))
	doc.cancel()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def recent_conversions(company=None, division=None):
	require_desk_user()
	frappe.has_permission("Stock Entry", "read", throw=True)
	if not frappe.get_meta("Stock Entry").has_field("recipe"):
		return {"can_cancel": False, "rows": []}
	filters = {"recipe": ["!=", ""], "docstatus": ["!=", 2]}
	if company:
		filters["company"] = company
	if division and frappe.get_meta("Stock Entry").has_field("division"):
		filters["division"] = division
	fields = ["name", "posting_date", "recipe", "company", "docstatus", "purpose"]
	meta = frappe.get_meta("Stock Entry")
	for field in ("division", "planned_qty"):
		if meta.has_field(field):
			fields.append(field)
	rows = frappe.get_list(
		"Stock Entry",
		filters=filters,
		fields=fields,
		order_by="modified desc",
		limit_page_length=8,
	)
	return {"can_cancel": bool(frappe.has_permission("Stock Entry", "cancel")), "rows": rows}


def run_register(filters=None):
	require_desk_user()
	columns = register_columns()
	if not frappe.db.exists("DocType", "Stock Entry"):
		return columns, []
	meta = frappe.get_meta("Stock Entry")
	if not meta.has_field("recipe"):
		return columns, []
	frappe.has_permission("Stock Entry", "read", throw=True)
	try:
		filters = restrict_filters(
			filters or {},
			_allowed("Company"),
			_allowed("Division") if meta.has_field("division") else [],
		)
	except RecipeError as exc:
		frappe.throw(str(exc))
	names = frappe.get_all(
		"Stock Entry",
		filters=report_filters(filters),
		pluck="name",
		order_by="posting_date asc, name asc",
		limit_page_length=5000,
	)
	if not names:
		return columns, []
	parent_fields = ["name", "posting_date", "recipe", "company", "purpose", "docstatus"]
	for field in ("division", "planned_qty", "expected_loss_pct", "loss_free_qty"):
		if meta.has_field(field):
			parent_fields.append(field)
	parents = frappe.get_all("Stock Entry", filters={"name": ["in", names]}, fields=parent_fields, limit_page_length=5000)
	item_fields = [
		"parent",
		"item_code",
		"qty",
		"uom",
		"s_warehouse",
		"t_warehouse",
		"is_finished_item",
		"basic_amount",
		"basic_rate",
	]
	detail = frappe.get_meta("Stock Entry Detail")
	if detail.has_field("recipe_line_type"):
		item_fields.append("recipe_line_type")
	children = frappe.get_all(
		"Stock Entry Detail",
		filters={"parent": ["in", names]},
		fields=item_fields,
		limit_page_length=50000,
	)
	grouped = {}
	for row in children:
		item = dict(row)
		item["rate"] = item.get("basic_rate")
		grouped.setdefault(row.parent, []).append(item)
	entries = []
	for parent in parents:
		entry = dict(parent)
		entry["items"] = grouped.get(parent.name, [])
		entries.append(entry)
	return columns, register_rows(entries, filters)


def _build(**kwargs):
	recipe_name = " ".join(str(kwargs.get("recipe") or "").split())
	if not recipe_name or not frappe.db.exists("Recipe", recipe_name):
		frappe.throw(_("Choose a recipe."))
	doc = frappe.get_doc("Recipe", recipe_name)
	doc.check_permission("read")
	recipe = _recipe_dict(doc)
	company = " ".join(str(kwargs.get("company") or recipe.get("company") or "").split())
	_check_warehouses(
		_list(kwargs.get("source_warehouses")) + [kwargs.get("target_warehouse")],
		company,
	)
	lines = _list(kwargs.get("lines"))
	items = [recipe["item"], *[line["item_code"] for line in _flat(recipe)]]
	batch_items = _batch_items(items)
	request = {
		"company": company,
		"division": kwargs.get("division"),
		"qty": kwargs.get("qty"),
		"source_warehouses": _list(kwargs.get("source_warehouses")),
		"target_warehouse": kwargs.get("target_warehouse"),
		"actual_output": kwargs.get("actual_output"),
		"lines": lines,
		"batch_no": kwargs.get("batch_no"),
		"manufacturing_date": kwargs.get("manufacturing_date"),
		"expiry_date": kwargs.get("expiry_date"),
		"confirm_shortfall": kwargs.get("confirm_shortfall"),
		"submitting": kwargs.get("submitting"),
		"roles": frappe.get_roles(),
		"division_rows": _division_rows(company),
		"allowed_companies": _allowed("Company"),
		"allowed_divisions": _allowed("Division"),
		"batch_items": batch_items,
	}
	try:
		return build_conversion(recipe, request, _bins(items, request["source_warehouses"]))
	except RecipeError as exc:
		frappe.throw(str(exc))


def _require_stock_permission(submitting):
	frappe.has_permission("Stock Entry", "create", throw=True)
	if submitting:
		frappe.has_permission("Stock Entry", "submit", throw=True)


def _require_recipe_fields():
	meta = frappe.get_meta("Stock Entry")
	missing = [
		field
		for field in ("recipe", "division", "planned_qty", "expected_loss_pct", "confirm_shortfall")
		if not meta.has_field(field)
	]
	if missing:
		frappe.throw(_("Recipe fields are not on Stock Entry yet. Open the site and press Update Now."))


def _stock_rights():
	return {
		"can_submit": bool(frappe.has_permission("Stock Entry", "submit")),
		"can_create": bool(frappe.has_permission("Stock Entry", "create")),
		"can_cancel": bool(frappe.has_permission("Stock Entry", "cancel")),
	}


def _check_material_batches(document):
	if not frappe.db.exists("DocType", "Batch"):
		return
	for row in document.get("items") or []:
		if row.get("is_finished_item") or not row.get("batch_no"):
			continue
		existing = _find_batch(row["batch_no"])
		if not existing:
			frappe.throw(_("Batch {0} was not found for {1}.").format(row["batch_no"], row["item_code"]))
		if existing.get("item") and existing.get("item") != row["item_code"]:
			frappe.throw(_("Batch {0} belongs to {1}.").format(existing.get("name"), existing.get("item")))
		row["batch_no"] = existing.get("name")


def _ensure_finished_batch(built):
	document = built["document"]
	preview = built["preview"]
	batch_no = preview.get("batch_no")
	if not batch_no:
		return
	if not frappe.db.exists("DocType", "Batch"):
		frappe.throw(_("Batches are not installed, so this finished item cannot take a batch no."))
	finished = next(row for row in document["items"] if row.get("is_finished_item"))
	existing = _find_batch(batch_no)
	try:
		action = batch_action(
			existing,
			finished["item_code"],
			preview.get("manufacturing_date"),
			preview.get("expiry_date"),
		)
	except RecipeError as exc:
		frappe.throw(str(exc))
	if action == "create":
		created = frappe.get_doc(
			{
				"doctype": "Batch",
				"batch_id": batch_no,
				"item": finished["item_code"],
				"manufacturing_date": preview.get("manufacturing_date") or None,
				"expiry_date": preview.get("expiry_date") or None,
			}
		)
		created.flags.ignore_permissions = True
		created.insert(ignore_permissions=True)
		finished["batch_no"] = created.name
		return
	if action == "update":
		updates = {}
		if preview.get("manufacturing_date") and not existing.get("manufacturing_date"):
			updates["manufacturing_date"] = preview["manufacturing_date"]
		if preview.get("expiry_date") and not existing.get("expiry_date"):
			updates["expiry_date"] = preview["expiry_date"]
		if updates:
			frappe.db.set_value("Batch", existing["name"], updates)
	finished["batch_no"] = existing["name"]


def _find_batch(batch_no):
	name = batch_no if frappe.db.exists("Batch", batch_no) else frappe.db.get_value("Batch", {"batch_id": batch_no}, "name")
	if not name:
		return None
	return frappe.db.get_value(
		"Batch",
		name,
		["name", "item", "batch_id", "manufacturing_date", "expiry_date"],
		as_dict=True,
	)


def _stock_payload(document):
	meta = frappe.get_meta("Stock Entry")
	payload = {"doctype": "Stock Entry", "items": []}
	for key, value in document.items():
		if key in ("doctype", "items"):
			continue
		if meta.has_field(key):
			payload[key] = value
	child_meta = frappe.get_meta("Stock Entry Detail")
	for row in document.get("items") or []:
		child = {}
		for key, value in row.items():
			if child_meta.has_field(key):
				child[key] = value
		payload["items"].append(child)
	return payload


def _check_warehouses(names, company):
	wanted = []
	for name in names:
		cleaned = " ".join(str(name or "").split())
		if cleaned and cleaned not in wanted:
			wanted.append(cleaned)
	if not wanted or not frappe.db.exists("DocType", "Warehouse"):
		return
	rows = frappe.get_all("Warehouse", filters={"name": ["in", wanted]}, fields=["name", "company"])
	found = {row.name: row.company for row in rows}
	for name in wanted:
		if name not in found:
			frappe.throw(_("Warehouse {0} was not found.").format(name))
		if found[name] and found[name] != company:
			frappe.throw(_("Warehouse {0} belongs to {1}, not {2}.").format(name, found[name], company))


def _bins(items, warehouses):
	names = [item for item in dict.fromkeys(items) if item]
	places = [" ".join(str(warehouse or "").split()) for warehouse in warehouses or []]
	places = [warehouse for warehouse in places if warehouse]
	if not names or not places or not frappe.db.exists("DocType", "Bin"):
		return []
	return frappe.get_all(
		"Bin",
		filters={"item_code": ["in", names], "warehouse": ["in", places]},
		fields=["item_code", "warehouse", "actual_qty", "valuation_rate"],
		limit_page_length=2000,
	)


def _batch_items(items):
	names = [item for item in dict.fromkeys(items) if item]
	if not names or not frappe.db.exists("DocType", "Item"):
		return []
	meta = frappe.get_meta("Item")
	if not meta.has_field("has_batch_no"):
		return []
	return frappe.get_all(
		"Item",
		filters={"name": ["in", names], "has_batch_no": 1},
		pluck="name",
	)


def _division_rows(company):
	if not company or not frappe.db.exists("DocType", "Division"):
		return []
	return frappe.get_all(
		"Division",
		filters={"company": company},
		fields=["name", "division_name", "company", "is_active"],
		limit_page_length=200,
	)


def _allowed(doctype):
	if not frappe.db.exists("DocType", "User Permission"):
		return []
	return frappe.get_all(
		"User Permission",
		filters={"user": frappe.session.user, "allow": doctype},
		pluck="for_value",
	)


def _raw_from_doc(doc) -> dict:
	return {
		"recipe_name": doc.get("recipe_name") or doc.get("name"),
		"company": doc.get("company"),
		"division": doc.get("division"),
		"item": doc.get("item"),
		"item_name": doc.get("item_name"),
		"qty": doc.get("qty"),
		"uom": doc.get("uom"),
		"process_loss_percentage": doc.get("process_loss_percentage"),
		"is_active": doc.get("is_active"),
		"bom": doc.get("bom"),
		"notes": doc.get("notes"),
		"ingredients": [_row_dict(row) for row in doc.get("ingredients") or []],
		"packaging": [_row_dict(row) for row in doc.get("packaging") or []],
		"sub_assemblies": [_row_dict(row) for row in doc.get("sub_assemblies") or []],
	}


def _recipe_dict(doc) -> dict:
	raw = _raw_from_doc(doc)
	try:
		return prepare_recipe(raw, _recipe_context(raw))
	except RecipeError as exc:
		frappe.throw(str(exc))


def _recipe_context(raw) -> dict:
	mapped = _sub_map(raw)
	return {
		"division_rows": _division_rows(raw.get("company")),
		"sub_items": mapped.get("items") or {},
		"sub_boms": mapped.get("boms") or {},
		"sub_children": mapped.get("children") or {},
		"stock_uoms": _stock_uoms([*_item_codes(raw), *(mapped.get("items") or {}).values()]),
	}


def _sub_map(raw) -> dict:
	cached = raw.get("_sub_map")
	if cached:
		return cached
	items, boms, children = {}, {}, {}
	names = [
		" ".join(str(row.get("sub_recipe") or "").split())
		for row in raw.get("sub_assemblies") or []
		if " ".join(str(row.get("sub_recipe") or "").split())
	]
	_load_subs(names, items, boms, children, set())
	mapped = {"items": items, "boms": boms, "children": children}
	raw["_sub_map"] = mapped
	return mapped


def _load_subs(names, items, boms, children, seen):
	if not names or not frappe.db.exists("DocType", "Recipe"):
		return
	pending = [name for name in names if name and name not in seen and frappe.db.exists("Recipe", name)]
	if not pending:
		return
	seen.update(pending)
	for row in frappe.get_all("Recipe", filters={"name": ["in", pending]}, fields=["name", "item", "bom"]):
		items[row.name] = row.item
		boms[row.name] = row.bom
	if not frappe.db.table_exists("Recipe Sub Assembly"):
		return
	next_names = []
	for row in frappe.get_all(
		"Recipe Sub Assembly",
		filters={"parent": ["in", pending], "parenttype": "Recipe"},
		fields=["parent", "sub_recipe"],
		limit_page_length=2000,
	):
		children.setdefault(row.parent, [])
		if row.sub_recipe and row.sub_recipe not in children[row.parent]:
			children[row.parent].append(row.sub_recipe)
			next_names.append(row.sub_recipe)
	_load_subs(next_names, items, boms, children, seen)


def _item_codes(raw) -> list:
	codes = [raw.get("item")]
	for table in ("ingredients", "packaging", "sub_assemblies"):
		for row in raw.get(table) or []:
			codes.append(row.get("item_code"))
	return codes


def _stock_uoms(items) -> dict:
	names = [" ".join(str(item or "").split()) for item in items if " ".join(str(item or "").split())]
	if not names or not frappe.db.exists("DocType", "Item"):
		return {}
	rows = frappe.get_all("Item", filters={"name": ["in", names]}, fields=["name", "stock_uom"])
	return {row.name: row.stock_uom for row in rows}


def _write_back(doc, prepared):
	for field in (
		"recipe_name",
		"company",
		"division",
		"item",
		"qty",
		"uom",
		"process_loss_percentage",
		"is_active",
	):
		doc.set(field, prepared[field])
	for table in ("ingredients", "packaging", "sub_assemblies"):
		for child in list(doc.get(table) or []):
			if _blank_child(child, table):
				doc.remove(child)
		live = doc.get(table) or []
		if len(live) != len(prepared[table]):
			frappe.throw(_("Could not write the {0} lines back onto the recipe.").format(table))
		for child, row in zip(live, prepared[table]):
			for field, value in row.items():
				if value is not None and child.meta.has_field(field):
					child.set(field, value)


def _blank_child(row, table) -> bool:
	if table == "sub_assemblies":
		return not (row.get("sub_recipe") or row.get("item_code") or row.get("qty"))
	return not (row.get("item_code") or row.get("percentage") or row.get("qty"))


def _apply_payload(doc, data):
	for field in (
		"recipe_name",
		"company",
		"division",
		"item",
		"qty",
		"uom",
		"process_loss_percentage",
		"is_active",
		"notes",
	):
		if field in data:
			doc.set(field, data.get(field))
	for table in ("ingredients", "packaging", "sub_assemblies"):
		if table not in data:
			continue
		doc.set(table, [])
		for row in data.get(table) or []:
			if isinstance(row, dict):
				doc.append(table, row)


def _public_recipe(doc) -> dict:
	recipe = _recipe_dict(doc)
	recipe["name"] = doc.name
	recipe["can_write"] = bool(doc.has_permission("write"))
	return recipe


def _row_dict(row) -> dict:
	if hasattr(row, "as_dict"):
		return row.as_dict()
	return dict(row)


def _flat(recipe) -> list:
	rows = []
	for key, line_type in (
		("ingredients", "Ingredient"),
		("sub_assemblies", "Sub Assembly"),
		("packaging", "Packaging"),
	):
		for line in recipe.get(key) or []:
			rows.append({**line, "line_type": line_type})
	return rows


def _object(value) -> dict:
	if value is None:
		return {}
	if isinstance(value, str):
		value = frappe.parse_json(value)
	if not isinstance(value, dict):
		frappe.throw(_("The form is missing."))
	return value


def _list(value):
	if value is None or value == "":
		return []
	if isinstance(value, str):
		value = frappe.parse_json(value)
	return list(value or [])


def _current_bom(name):
	if not name or not frappe.db.exists("BOM", name):
		return None
	doc = frappe.get_doc("BOM", name)
	if int(doc.docstatus or 0) == 2:
		return None
	return doc


def _bom_view(doc) -> dict:
	items = []
	for row in doc.get("items") or []:
		items.append(
			{
				"item_code": row.item_code,
				"qty": row.qty,
				"uom": row.uom,
				"bom_no": row.get("bom_no") or "",
				"do_not_explode": row.get("do_not_explode") or 0,
			}
		)
	return {
		"item": doc.item,
		"quantity": doc.quantity,
		"uom": doc.uom,
		"company": doc.company,
		"items": items,
	}


def _fill_bom(doc, desired):
	meta = frappe.get_meta("BOM")
	values = dict(desired)
	items = values.pop("items")
	values.pop("doctype", None)
	if meta.has_field("currency") and not values.get("currency"):
		values["currency"] = frappe.db.get_value("Company", desired.get("company"), "default_currency")
	if meta.has_field("conversion_rate"):
		values["conversion_rate"] = values.get("conversion_rate") or 1
	for key, value in values.items():
		if meta.has_field(key):
			doc.set(key, value)
	doc.set("items", [])
	child_meta = frappe.get_meta("BOM Item")
	for row in items:
		child = {key: value for key, value in row.items() if child_meta.has_field(key)}
		doc.append("items", child)


def _insert_bom(desired):
	doc = frappe.new_doc("BOM")
	_fill_bom(doc, desired)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc


def _flag_bom(doc, desired):
	values = {}
	if int(doc.is_active or 0) != int(desired.get("is_active") or 0):
		values["is_active"] = desired.get("is_active") or 0
	meta = frappe.get_meta("BOM")
	if meta.has_field("division") and (doc.get("division") or "") != (desired.get("division") or ""):
		values["division"] = desired.get("division") or ""
	if meta.has_field("recipe") and (doc.get("recipe") or "") != (desired.get("recipe") or ""):
		values["recipe"] = desired.get("recipe") or ""
	if values:
		frappe.db.set_value("BOM", doc.name, values, update_modified=False)


def _other_default(item, exclude) -> bool:
	filters = {"item": item, "docstatus": 1, "is_default": 1, "is_active": 1}
	if exclude:
		filters["name"] = ["!=", exclude]
	return bool(frappe.db.exists("BOM", filters))


def _remember(doc, bom_name):
	if doc.get("bom") == bom_name:
		return
	doc.bom = bom_name
	if doc.get("name") and not doc.get("__islocal") and frappe.db.exists("Recipe", doc.name):
		frappe.db.set_value("Recipe", doc.name, "bom", bom_name, update_modified=False)


def _ensure_fields():
	specs = {
		doctype: fields
		for doctype, fields in stock_entry_fields().items()
		if frappe.db.exists("DocType", doctype)
	}
	if not specs:
		return
	for fields in specs.values():
		for field in fields:
			field["module"] = "Melliflous Branding"
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(specs, update=True)


def _ensure_sidebar():
	if not frappe.db.table_exists("Sidebar") or not frappe.db.exists("Sidebar", "Melliflous Branding"):
		return
	sidebar = frappe.get_doc("Sidebar", "Melliflous Branding")
	missing = missing_sidebar_links((row.link_type, row.link_to) for row in (sidebar.items or []))
	if not missing:
		return
	for link in missing:
		sidebar.append("items", link)
	sidebar.flags.ignore_permissions = True
	sidebar.save(ignore_permissions=True)
