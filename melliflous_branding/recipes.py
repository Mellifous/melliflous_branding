# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Recipe quantities, the BOM a recipe writes, and the manufacture stock entry.

No Frappe import. A recipe is the sheet the plant fills in. Saving it writes a
standard BOM. Convert Stock writes a Stock Entry of type Manufacture (a blend
of raw spices) or Repack (a packed pouch that consumes a sub-recipe and packs).

Process loss is extra raw material, not a second finished-good quantity.
A 2% loss on a 1 kg blend puts 1.02 kg of spices on the BOM and still receives
1 kg of finished goods, so the loss sits in the cost. The BOM's own process
loss stays 0, because ERPNext v16 applies that field differently from one
hotfix to the next and would book the loss twice.

Packaging and sub-recipes use the quantity that was typed. They are not
increased by the loss percent. A sub-recipe keeps its own BOM number and is
not exploded, so packing consumes the bulk blend that is already in stock.
"""

from __future__ import annotations

from melliflous_branding.divisions import DivisionError, clean, validate_division

OVERRIDE_ROLES = frozenset({"Manufacturing Manager", "System Manager", "Administrator"})
MANUFACTURE = "Manufacture"
REPACK = "Repack"

RECIPE_LINKS = (
	{
		"label": "Recipes",
		"link_type": "Page",
		"link_to": "recipes",
		"icon": "book-open",
	},
	{
		"label": "Convert Stock",
		"link_type": "Page",
		"link_to": "convert-stock",
		"icon": "repeat",
	},
	{
		"label": "Recipe",
		"link_type": "DocType",
		"link_to": "Recipe",
		"icon": "scroll-text",
	},
	{
		"label": "Production / Conversion Register",
		"link_type": "Report",
		"link_to": "Production Conversion Register",
		"icon": "chart-column",
		"report_ref_doctype": "Stock Entry",
	},
)


class RecipeError(ValueError):
	"""A recipe or a conversion the plant cannot post."""


def rounded(value, precision=6) -> float:
	return round(float(value or 0), precision)


def as_bool(value) -> bool:
	return value in (1, True, "1", "true", "True", "yes", "Yes")


def loss_factor(process_loss_percentage) -> float:
	return 1 + float(process_loss_percentage or 0) / 100


def can_override(roles) -> bool:
	return bool(OVERRIDE_ROLES.intersection(set(roles or [])))


def may_undo(permissions) -> bool:
	"""Cancel is enough. A user without Delete is not given Delete."""
	return bool((permissions or {}).get("cancel"))


def _number(value, label) -> float:
	if value is None or value == "":
		raise RecipeError(f"{label} is required.")
	try:
		return float(value)
	except (TypeError, ValueError):
		raise RecipeError(f"{label} has to be a number.")


def _optional_number(value):
	if value is None or value == "":
		return None
	try:
		return float(value)
	except (TypeError, ValueError):
		raise RecipeError("Enter a number.")


def _percent(value):
	number = _optional_number(value)
	if number is None or number == 0:
		return None
	return number


def _iso_date(value, label) -> str:
	value = clean(value)
	if not value:
		return ""
	if len(value) == 10 and value[4] == "-" and value[7] == "-" and value.replace("-", "").isdigit():
		return value
	raise RecipeError(f"{label} has to be a date.")


def _active(value) -> int:
	if value in (0, "0", False, "false", "False", "no"):
		return 0
	return 1


def _blank_row(row, *, sub=False) -> bool:
	if not isinstance(row, dict):
		return True
	if sub:
		return not clean(row.get("sub_recipe")) and not clean(row.get("item_code")) and not row.get("qty")
	return not clean(row.get("item_code")) and _percent(row.get("percentage")) is None and not row.get("qty")


def assert_division_choice(division, company, division_rows) -> str:
	"""Require a division when this company has one. Never swap in a different division."""
	division = clean(division)
	company = clean(company)
	if division_rows is None:
		return division
	names = []
	for row in division_rows or []:
		if clean(row.get("company")) != company:
			continue
		if row.get("is_active") in (0, "0", False):
			continue
		name = clean(row.get("name") or row.get("division_name"))
		if name:
			names.append(name)
	if not names:
		if division:
			raise RecipeError(f"{company} has no division, so leave division blank.")
		return ""
	if not division:
		raise RecipeError("Choose a division.")
	if division not in names:
		raise RecipeError(f"{division} is not an active division of {company}.")
	return division


def assert_allowed(company, division, allowed_companies, allowed_divisions) -> None:
	"""Empty allow-lists mean the user is not restricted."""
	if allowed_companies and clean(company) not in {clean(row) for row in allowed_companies}:
		raise RecipeError("You cannot use that company.")
	if division and allowed_divisions and clean(division) not in {clean(row) for row in allowed_divisions}:
		raise RecipeError("You cannot use that division.")


def restrict_filters(filters, allowed_companies, allowed_divisions) -> dict:
	"""Narrow a register to the companies and divisions this user may see."""
	filters = dict(filters or {})
	company = clean(filters.get("company"))
	division = clean(filters.get("division"))
	companies = [clean(row) for row in (allowed_companies or []) if clean(row)]
	divisions = [clean(row) for row in (allowed_divisions or []) if clean(row)]
	if companies:
		if company and company not in companies:
			raise RecipeError("You cannot use that company.")
		if not company and len(companies) == 1:
			filters["company"] = companies[0]
		elif not company:
			filters["companies"] = companies
	if divisions:
		if division and division not in divisions:
			raise RecipeError("You cannot use that division.")
		if not division and len(divisions) == 1:
			filters["division"] = divisions[0]
		elif not division:
			filters["divisions"] = divisions
	return filters


def _check_uom(item, uom, stock_uoms) -> None:
	if not stock_uoms or item not in stock_uoms:
		return
	stock_uom = clean(stock_uoms.get(item))
	if stock_uom and stock_uom != uom:
		raise RecipeError(f"{item} is stocked in {stock_uom}. Use {stock_uom} on the recipe.")


def _ingredient(row, index, batch_qty, batch_uom, loss, stock_uoms) -> dict:
	item = clean(row.get("item_code"))
	if not item:
		raise RecipeError(f"Ingredient row {index} needs an item.")
	uom = clean(row.get("uom")) or batch_uom
	percentage = _percent(row.get("percentage"))
	if percentage is not None:
		if percentage < 0 or percentage > 100:
			raise RecipeError(f"The percentage for {item} has to be from 0 to 100.")
		if uom != batch_uom:
			raise RecipeError(
				f"{item} uses {uom}, and the recipe output is {batch_uom}. "
				"Percentages only work when those match."
			)
		qty = rounded(batch_qty * (percentage / 100) * loss_factor(loss))
	else:
		qty = _number(row.get("qty"), f"Quantity for {item}")
		if qty <= 0:
			raise RecipeError(f"Quantity for {item} has to be greater than zero.")
		qty = rounded(qty)
	_check_uom(item, uom, stock_uoms)
	return {
		"item_code": item,
		"item_name": clean(row.get("item_name")),
		"percentage": percentage,
		"qty": qty,
		"uom": uom,
	}


def _pack(row, index, stock_uoms) -> dict:
	item = clean(row.get("item_code"))
	if not item:
		raise RecipeError(f"Packaging row {index} needs an item.")
	qty = _number(row.get("qty"), f"Quantity for {item}")
	if qty <= 0:
		raise RecipeError(f"Quantity for {item} has to be greater than zero.")
	uom = clean(row.get("uom"))
	if not uom:
		raise RecipeError(f"Choose a UOM for {item}.")
	_check_uom(item, uom, stock_uoms)
	return {"item_code": item, "item_name": clean(row.get("item_name")), "qty": rounded(qty), "uom": uom}


def _sub_assembly(row, index, sub_items, stock_uoms) -> dict:
	sub_recipe = clean(row.get("sub_recipe"))
	if not sub_recipe:
		raise RecipeError(f"Sub-recipe row {index} needs a recipe.")
	item = clean((sub_items or {}).get(sub_recipe) or row.get("item_code"))
	if not item:
		raise RecipeError(f"Save {sub_recipe} first, then choose it here.")
	qty = _number(row.get("qty"), f"Quantity for {sub_recipe}")
	if qty <= 0:
		raise RecipeError(f"Quantity for {sub_recipe} has to be greater than zero.")
	uom = clean(row.get("uom"))
	if not uom:
		raise RecipeError(f"Choose a UOM for {sub_recipe}.")
	_check_uom(item, uom, stock_uoms)
	return {
		"sub_recipe": sub_recipe,
		"item_code": item,
		"item_name": clean(row.get("item_name")),
		"qty": rounded(qty),
		"uom": uom,
	}


def _percent_rules(ingredients) -> None:
	if not ingredients:
		return
	percents = [row["percentage"] for row in ingredients if row["percentage"] is not None]
	if percents and len(percents) != len(ingredients):
		raise RecipeError("Use percentages for every ingredient, or quantities for every ingredient.")
	if not percents:
		return
	total = round(sum(percents), 6)
	if abs(total - 100) > 0.001:
		shown = f"{total:g}"
		raise RecipeError(f"Ingredient percentages add up to {shown}%. They need to add up to 100%.")


def _duplicates(finished, ingredients, packaging, sub_assemblies) -> None:
	seen = {finished: "the finished item"}
	groups = (
		("an ingredient", ingredients),
		("a pack", packaging),
		("a sub-recipe", sub_assemblies),
	)
	for label, rows in groups:
		for row in rows:
			item = row["item_code"]
			if item in seen:
				raise RecipeError(f"{item} is already {seen[item]}. It can only be on the recipe once.")
			seen[item] = label


def assert_no_cycle(name, children) -> None:
	stack = []

	def walk(node):
		if node in stack:
			path = " → ".join([*stack, node])
			raise RecipeError(f"Recipes cannot include each other in a loop: {path}.")
		stack.append(node)
		for child in children.get(node) or []:
			walk(child)
		stack.pop()

	walk(name)


def prepare_recipe(raw, context=None) -> dict:
	"""Return the recipe that will be saved. Percent lines get a quantity."""
	context = context or {}
	if not isinstance(raw, dict):
		raise RecipeError("The recipe is missing.")
	name = clean(raw.get("recipe_name") or raw.get("name"))
	if not name:
		raise RecipeError("Enter a recipe name.")
	company = clean(raw.get("company"))
	if not company:
		raise RecipeError("Choose a company.")
	division_rows = context.get("division_rows") if "division_rows" in context else None
	division = assert_division_choice(raw.get("division"), company, division_rows)
	if division:
		row_company = ""
		for row in context.get("division_rows") or []:
			if clean(row.get("name") or row.get("division_name")) == division:
				row_company = clean(row.get("company"))
				break
		if row_company:
			try:
				validate_division(row_company, company)
			except DivisionError as exc:
				raise RecipeError(str(exc))
	item = clean(raw.get("item"))
	if not item:
		raise RecipeError("Choose the finished item.")
	qty = _number(raw.get("qty"), "Output quantity")
	if qty <= 0:
		raise RecipeError("Output quantity has to be greater than zero.")
	qty = rounded(qty)
	uom = clean(raw.get("uom"))
	if not uom:
		raise RecipeError("Choose the output UOM.")
	stock_uoms = context.get("stock_uoms") or {}
	_check_uom(item, uom, stock_uoms)
	loss = _optional_number(raw.get("process_loss_percentage")) or 0
	if loss < 0 or loss > 100:
		raise RecipeError("Process loss has to be from 0 to 100 percent.")
	loss = rounded(loss, 6)
	ingredients = [
		_ingredient(row, index, qty, uom, loss, stock_uoms)
		for index, row in enumerate(raw.get("ingredients") or [], start=1)
		if not _blank_row(row)
	]
	packaging = [
		_pack(row, index, stock_uoms)
		for index, row in enumerate(raw.get("packaging") or [], start=1)
		if not _blank_row(row)
	]
	sub_assemblies = [
		_sub_assembly(row, index, context.get("sub_items") or {}, stock_uoms)
		for index, row in enumerate(raw.get("sub_assemblies") or [], start=1)
		if not _blank_row(row, sub=True)
	]
	if not ingredients and not packaging and not sub_assemblies:
		raise RecipeError("Add an ingredient, a pack, or a sub-recipe.")
	_percent_rules(ingredients)
	_duplicates(item, ingredients, packaging, sub_assemblies)
	children = dict(context.get("sub_children") or {})
	children[name] = [row["sub_recipe"] for row in sub_assemblies]
	assert_no_cycle(name, children)
	# A percentage is a share of the batch before loss, so the loss-free total is known.
	# A quantity typed by hand is already the consumption, and is not guessed apart.
	if ingredients and all(row["percentage"] is not None for row in ingredients):
		free, free_uom = loss_free_batch(ingredients, loss)
	else:
		free, free_uom = 0.0, ""
	return {
		"recipe_name": name,
		"company": company,
		"division": division,
		"item": item,
		"item_name": clean(raw.get("item_name")),
		"qty": qty,
		"uom": uom,
		"process_loss_percentage": loss,
		"is_active": _active(raw.get("is_active", 1)),
		"bom": clean(raw.get("bom")),
		"notes": str(raw.get("notes") or "").strip(),
		"ingredients": ingredients,
		"packaging": packaging,
		"sub_assemblies": sub_assemblies,
		"loss_free_qty": free,
		"loss_free_uom": free_uom,
	}


def loss_free_batch(ingredients, loss) -> tuple[float, str]:
	"""Ingredient quantity for one batch before process loss, when every line shares a UOM."""
	if not ingredients:
		return 0.0, ""
	uoms = {row["uom"] for row in ingredients}
	if len(uoms) != 1:
		return 0.0, ""
	factor = loss_factor(loss)
	if factor <= 0:
		return 0.0, ""
	total = sum(row["qty"] / factor for row in ingredients)
	return rounded(total), next(iter(uoms))


def flat_lines(recipe) -> list:
	rows = []
	for line in recipe.get("ingredients") or []:
		rows.append({**line, "line_type": "Ingredient"})
	for line in recipe.get("sub_assemblies") or []:
		rows.append({**line, "line_type": "Sub Assembly"})
	for line in recipe.get("packaging") or []:
		rows.append({**line, "line_type": "Packaging"})
	return rows


def entry_purpose(recipe) -> str:
	"""A blend of raw spices is Manufacture. Packing a sub-recipe is Repack."""
	if recipe.get("ingredients"):
		return MANUFACTURE
	return REPACK


def bom_document(recipe, sub_boms=None) -> dict:
	"""The BOM this recipe keeps in step. Process loss stays on the ingredient quantities."""
	sub_boms = sub_boms or {}
	items = []
	for line in flat_lines(recipe):
		row = {
			"item_code": line["item_code"],
			"qty": line["qty"],
			"uom": line["uom"],
			"conversion_factor": 1,
			"include_item_in_manufacturing": 1,
			"do_not_explode": 0,
			"bom_no": "",
		}
		if line["line_type"] == "Sub Assembly":
			bom_no = clean(sub_boms.get(line["sub_recipe"]))
			if not bom_no:
				raise RecipeError(f"Save {line['sub_recipe']} first so this recipe can use its BOM.")
			row["bom_no"] = bom_no
			row["do_not_explode"] = 1
		items.append(row)
	return {
		"doctype": "BOM",
		"item": recipe["item"],
		"company": recipe["company"],
		"quantity": recipe["qty"],
		"uom": recipe["uom"],
		"is_active": 1 if recipe.get("is_active", 1) else 0,
		"with_operations": 0,
		"process_loss_percentage": 0,
		"set_qty_based_on_percentage": 0,
		"rm_cost_as_per": "Valuation Rate",
		"recipe": recipe["recipe_name"],
		"division": recipe.get("division") or "",
		"items": items,
	}


def bom_signature(document) -> tuple:
	items = tuple(
		(
			row.get("item_code"),
			rounded(row.get("qty")),
			row.get("uom") or "",
			row.get("bom_no") or "",
			int(row.get("do_not_explode") or 0),
		)
		for row in document.get("items") or []
	)
	return (
		document.get("item"),
		rounded(document.get("quantity")),
		document.get("uom") or "",
		document.get("company"),
		items,
	)


def should_revise_bom(previous, desired) -> bool:
	return bom_signature(previous) != bom_signature(desired)


def default_bom_flag(previous_is_default, other_default_exists) -> int:
	"""Become the default only when this recipe already was, or when the item has none."""
	if previous_is_default:
		return 1
	if other_default_exists:
		return 0
	return 1


def scaled_lines(recipe, planned_qty) -> list:
	factor = float(planned_qty) / float(recipe["qty"])
	rows = []
	for line in flat_lines(recipe):
		rows.append({**line, "required": rounded(line["qty"] * factor), "qty": rounded(line["qty"] * factor)})
	return rows


def loss_free_for(recipe, planned_qty) -> float:
	if not recipe.get("loss_free_qty"):
		return 0.0
	return rounded(float(recipe["loss_free_qty"]) * float(planned_qty) / float(recipe["qty"]))


def _dedupe(values) -> list:
	seen = []
	for value in values or []:
		name = clean(value)
		if name and name not in seen:
			seen.append(name)
	return seen


def check_batch_dates(batch_no, manufacturing_date, expiry_date) -> tuple[str, str, str]:
	batch_no = clean(batch_no)
	manufacturing_date = _iso_date(manufacturing_date, "Manufacturing date")
	expiry_date = _iso_date(expiry_date, "Expiry date")
	if (manufacturing_date or expiry_date) and not batch_no:
		raise RecipeError("Enter a batch no, or clear the manufacturing and expiry dates.")
	if manufacturing_date and expiry_date and expiry_date < manufacturing_date:
		raise RecipeError("Expiry date cannot be before the manufacturing date.")
	return batch_no, manufacturing_date, expiry_date


def batch_action(existing, item, manufacturing_date, expiry_date) -> str:
	"""What to do with the finished batch: create, use, or fill blank dates."""
	if not existing:
		return "create"
	owner = clean(existing.get("item"))
	if owner and owner != item:
		name = clean(existing.get("name") or existing.get("batch_id")) or "that batch"
		raise RecipeError(f"Batch {name} belongs to {owner}.")
	current_mfg = clean(existing.get("manufacturing_date"))
	current_exp = clean(existing.get("expiry_date"))
	if manufacturing_date and current_mfg and current_mfg != manufacturing_date:
		raise RecipeError("That batch already has a different manufacturing date.")
	if expiry_date and current_exp and current_exp != expiry_date:
		raise RecipeError("That batch already has a different expiry date.")
	if (manufacturing_date and not current_mfg) or (expiry_date and not current_exp):
		return "update"
	return "use"


def missing_batches(lines, batch_items, finished_item, finished_batch) -> list:
	needed = set(batch_items or [])
	missing = []
	for line in lines:
		if rounded(line.get("qty")) <= 0:
			continue
		if line["item_code"] in needed and not clean(line.get("batch_no")):
			missing.append(line["item_code"])
	if finished_item in needed and not clean(finished_batch):
		missing.append(finished_item)
	return missing


def allocate(lines, bins, warehouses) -> list:
	"""Split each actual quantity across the source warehouses, in the order given."""
	warehouses = _dedupe(warehouses)
	remaining = {}
	rates = {}
	for bin_row in bins or []:
		warehouse = clean(bin_row.get("warehouse"))
		item = clean(bin_row.get("item_code"))
		if not warehouse or not item or warehouse not in warehouses:
			continue
		key = (item, warehouse)
		have = max(0.0, float(bin_row.get("actual_qty") or 0))
		remaining[key] = remaining.get(key, 0.0) + have
		rates[key] = float(bin_row.get("valuation_rate") or 0)
	rows = []
	for line in lines:
		need = rounded(line.get("qty"))
		available = rounded(sum(remaining.get((line["item_code"], warehouse), 0.0) for warehouse in warehouses))
		left = need
		splits = []
		weighted = 0.0
		taken = 0.0
		for warehouse in warehouses:
			if left <= 1e-9:
				break
			have = remaining.get((line["item_code"], warehouse), 0.0)
			if have <= 1e-9:
				continue
			take = min(have, left)
			remaining[(line["item_code"], warehouse)] = have - take
			rate = rates.get((line["item_code"], warehouse), 0.0)
			splits.append({"warehouse": warehouse, "qty": rounded(take), "rate": rate})
			weighted += take * rate
			taken += take
			left -= take
		shortfall = rounded(max(0.0, need - available))
		if left > 1e-9 and warehouses:
			warehouse = warehouses[-1]
			rate = rates.get((line["item_code"], warehouse), 0.0)
			if splits and splits[-1]["warehouse"] == warehouse:
				splits[-1]["qty"] = rounded(splits[-1]["qty"] + left)
			else:
				splits.append({"warehouse": warehouse, "qty": rounded(left), "rate": rate})
			weighted += left * rate
			taken += left
		rate = (weighted / taken) if taken else 0.0
		rows.append(
			{
				"item_code": line["item_code"],
				"item_name": line.get("item_name") or "",
				"uom": line.get("uom") or "",
				"line_type": line.get("line_type") or "",
				"required": rounded(line.get("required", line.get("qty"))),
				"actual_qty": need,
				"available": available,
				"shortfall": shortfall,
				"rate": rounded(rate, 6),
				"amount": rounded(need * rate, 2),
				"splits": splits,
				"batch_no": clean(line.get("batch_no")),
				"needs_batch": bool(line.get("needs_batch")),
			}
		)
	return rows


def shortfall_message(has_shortfall, roles, confirmed, submitting, rows=None) -> str:
	if not has_shortfall or not submitting:
		return ""
	names = [row["item_code"] for row in rows or [] if rounded(row.get("shortfall")) > 0]
	detail = ", ".join(names) if names else "a material"
	if not as_bool(confirmed):
		return (
			f"Not enough stock for {detail}. "
			"Tick convert despite short stock, which only a Manufacturing Manager or a System Manager can do."
		)
	if not can_override(roles):
		return "Only a Manufacturing Manager or a System Manager can convert when stock is short."
	return ""


def _edits(raw_lines) -> dict:
	edits = {}
	for row in raw_lines or []:
		if not isinstance(row, dict):
			continue
		item = clean(row.get("item_code"))
		if not item:
			continue
		edits[item] = {
			"actual_qty": row.get("actual_qty"),
			"batch_no": clean(row.get("batch_no")),
		}
	return edits


def build_conversion(recipe, request, bins) -> dict:
	"""Preview and the Stock Entry to insert. Submit is blocked while material is short."""
	request = request or {}
	if not recipe or not recipe.get("is_active", 1):
		raise RecipeError("This recipe is inactive.")
	if not clean(recipe.get("bom")):
		raise RecipeError("Save the recipe so it can write a BOM, then convert.")
	planned = _number(request.get("qty"), "Quantity to produce")
	if planned <= 0:
		raise RecipeError("Quantity to produce has to be greater than zero.")
	planned = rounded(planned)
	company = clean(request.get("company") or recipe.get("company"))
	if company != clean(recipe.get("company")):
		raise RecipeError(f"This recipe belongs to {recipe.get('company')}.")
	division_rows = request.get("division_rows") if "division_rows" in request else None
	division = assert_division_choice(request.get("division") if request.get("division") is not None else recipe.get("division"), company, division_rows)
	assert_allowed(company, division, request.get("allowed_companies"), request.get("allowed_divisions"))
	sources = _dedupe(request.get("source_warehouses"))
	if not sources:
		raise RecipeError("Choose a source warehouse.")
	target = clean(request.get("target_warehouse"))
	if not target:
		raise RecipeError("Choose a target warehouse.")
	if request.get("actual_output") in (None, ""):
		actual_output = planned
	else:
		actual_output = _number(request.get("actual_output"), "Actual output")
	if actual_output <= 0:
		raise RecipeError("Actual output has to be greater than zero.")
	actual_output = rounded(actual_output)
	batch_no, manufacturing_date, expiry_date = check_batch_dates(
		request.get("batch_no"), request.get("manufacturing_date"), request.get("expiry_date")
	)
	batch_items = set(request.get("batch_items") or [])
	edits = _edits(request.get("lines"))
	lines = scaled_lines(recipe, planned)
	for line in lines:
		edit = edits.get(line["item_code"]) or {}
		if "actual_qty" in edit and edit["actual_qty"] not in (None, ""):
			qty = _number(edit["actual_qty"], f"Actual quantity for {line['item_code']}")
			if qty < 0:
				raise RecipeError(f"Actual quantity for {line['item_code']} cannot be negative.")
			line["qty"] = rounded(qty)
		line["batch_no"] = edit.get("batch_no") or ""
		line["needs_batch"] = line["item_code"] in batch_items
	if not any(line["qty"] > 0 for line in lines):
		raise RecipeError("Enter a quantity for at least one material.")
	submitting = bool(request.get("submitting"))
	missing = missing_batches(lines, batch_items, recipe["item"], batch_no)
	if submitting and missing:
		raise RecipeError("Enter a batch no for " + ", ".join(missing) + ".")
	rows = allocate(lines, bins, sources)
	has_shortfall = any(row["shortfall"] > 0 for row in rows)
	roles = request.get("roles") or []
	confirmed = request.get("confirm_shortfall")
	block = shortfall_message(has_shortfall, roles, confirmed, submitting, rows)
	fg_completed = actual_output if actual_output > planned else planned
	process_loss_qty = rounded(max(0.0, fg_completed - actual_output))
	process_loss_percentage = rounded((process_loss_qty / fg_completed) * 100) if fg_completed else 0.0
	purpose = entry_purpose(recipe)
	items = []
	for row in rows:
		if row["actual_qty"] <= 0:
			continue
		for split in row["splits"]:
			if split["qty"] <= 0:
				continue
			items.append(
				{
					"item_code": row["item_code"],
					"qty": split["qty"],
					"uom": row["uom"],
					"stock_uom": row["uom"],
					"conversion_factor": 1,
					"s_warehouse": split["warehouse"],
					"t_warehouse": None,
					"is_finished_item": 0,
					"recipe_line_type": row["line_type"],
					"batch_no": row["batch_no"] or None,
					"use_serial_batch_fields": 1 if row["batch_no"] else 0,
				}
			)
	items.append(
		{
			"item_code": recipe["item"],
			"qty": actual_output,
			"uom": recipe["uom"],
			"stock_uom": recipe["uom"],
			"conversion_factor": 1,
			"s_warehouse": None,
			"t_warehouse": target,
			"is_finished_item": 1,
			"recipe_line_type": "Finished",
			"batch_no": batch_no or None,
			"use_serial_batch_fields": 1 if batch_no else 0,
		}
	)
	estimated = rounded(sum(row["amount"] for row in rows), 2)
	document = {
		"doctype": "Stock Entry",
		"purpose": purpose,
		"stock_entry_type": purpose,
		"company": company,
		"division": division,
		"recipe": recipe["recipe_name"],
		"bom_no": recipe["bom"],
		"from_bom": 1,
		"use_multi_level_bom": 0,
		"fg_completed_qty": fg_completed,
		"process_loss_qty": process_loss_qty,
		"process_loss_percentage": process_loss_percentage,
		"planned_qty": planned,
		"expected_loss_pct": recipe.get("process_loss_percentage") or 0,
		"loss_free_qty": loss_free_for(recipe, planned),
		"confirm_shortfall": 1 if has_shortfall and as_bool(confirmed) and can_override(roles) else 0,
		"remarks": f"Recipe {recipe['recipe_name']}",
		"items": items,
	}
	preview = {
		"recipe": recipe["recipe_name"],
		"item": recipe["item"],
		"item_name": recipe.get("item_name") or "",
		"uom": recipe["uom"],
		"company": company,
		"division": division,
		"purpose": purpose,
		"bom": recipe["bom"],
		"planned_qty": planned,
		"actual_output": actual_output,
		"expected_loss_pct": recipe.get("process_loss_percentage") or 0,
		"lines": rows,
		"has_shortfall": has_shortfall,
		"estimated_cost": estimated,
		"cost_per_unit": rounded(estimated / actual_output, 2) if actual_output else 0,
		"yield_pct": rounded((actual_output / planned) * 100, 2) if planned else 0,
		"can_override": can_override(roles),
		"block": block,
		"batch_no": batch_no,
		"manufacturing_date": manufacturing_date,
		"expiry_date": expiry_date,
		"finished_needs_batch": recipe["item"] in batch_items,
	}
	return {"document": document, "preview": preview}


def register_columns() -> list:
	return [
		{"fieldname": "posting_date", "label": "Date", "fieldtype": "Date", "width": 110},
		{"fieldname": "stock_entry", "label": "Stock Entry", "fieldtype": "Link", "options": "Stock Entry", "width": 160},
		{"fieldname": "recipe", "label": "Recipe", "fieldtype": "Link", "options": "Recipe", "width": 180},
		{"fieldname": "company", "label": "Company", "fieldtype": "Link", "options": "Company", "width": 180},
		{"fieldname": "division", "label": "Division", "fieldtype": "Link", "options": "Division", "width": 140},
		{"fieldname": "item_code", "label": "Finished item", "fieldtype": "Link", "options": "Item", "width": 160},
		{"fieldname": "planned_qty", "label": "Planned qty", "fieldtype": "Float", "width": 110},
		{"fieldname": "actual_output", "label": "Actual output", "fieldtype": "Float", "width": 120},
		{"fieldname": "uom", "label": "UOM", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"fieldname": "yield_pct", "label": "Yield %", "fieldtype": "Percent", "width": 90},
		{"fieldname": "expected_loss_pct", "label": "Expected loss %", "fieldtype": "Percent", "width": 130},
		{"fieldname": "actual_loss_pct", "label": "Actual loss %", "fieldtype": "Percent", "width": 120},
		{"fieldname": "loss_vs_expected", "label": "Loss vs expected", "fieldtype": "Percent", "width": 140},
		{"fieldname": "total_cost", "label": "Total cost", "fieldtype": "Currency", "width": 120},
		{"fieldname": "cost_per_unit", "label": "Cost per unit", "fieldtype": "Currency", "width": 120},
		{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 110},
		{"fieldname": "purpose", "label": "Purpose", "fieldtype": "Data", "width": 120},
	]


def _matches(entry, filters) -> bool:
	if entry.get("purpose") not in (MANUFACTURE, REPACK):
		return False
	if not clean(entry.get("recipe")):
		return False
	if not as_bool(filters.get("include_cancelled")) and int(entry.get("docstatus") or 0) == 2:
		return False
	company = clean(filters.get("company"))
	if company and clean(entry.get("company")) != company:
		return False
	companies = filters.get("companies") or []
	if companies and clean(entry.get("company")) not in {clean(row) for row in companies}:
		return False
	division = clean(filters.get("division"))
	if division and clean(entry.get("division")) != division:
		return False
	divisions = filters.get("divisions") or []
	if divisions and clean(entry.get("division")) not in {clean(row) for row in divisions}:
		return False
	recipe = clean(filters.get("recipe"))
	if recipe and clean(entry.get("recipe")) != recipe:
		return False
	posting = str(entry.get("posting_date") or "")
	if filters.get("from_date") and posting < str(filters["from_date"]):
		return False
	if filters.get("to_date") and posting > str(filters["to_date"]):
		return False
	return True


def conversion_metrics(entry) -> dict:
	"""Yield, loss against the recipe, and cost per finished unit."""
	items = entry.get("items") or []
	planned = float(entry.get("planned_qty") or 0)
	actual = sum(float(row.get("qty") or 0) for row in items if row.get("is_finished_item"))
	expected = float(entry.get("expected_loss_pct") or 0)
	free = float(entry.get("loss_free_qty") or 0)
	consumed = sum(
		float(row.get("qty") or 0)
		for row in items
		if row.get("recipe_line_type") == "Ingredient" and not row.get("is_finished_item")
	)
	actual_loss = None
	variance = None
	if free > 0 and consumed > 0:
		actual_loss = ((consumed - free) / free) * 100
		variance = actual_loss - expected
	cost = 0.0
	finished_item = ""
	finished_uom = ""
	for row in items:
		if row.get("is_finished_item"):
			finished_item = row.get("item_code") or finished_item
			finished_uom = row.get("uom") or finished_uom
			continue
		if not row.get("s_warehouse"):
			continue
		if row.get("basic_amount") not in (None, ""):
			cost += float(row.get("basic_amount") or 0)
		else:
			cost += float(row.get("qty") or 0) * float(row.get("rate") or 0)
	status = {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(int(entry.get("docstatus") or 0), "")
	return {
		"posting_date": entry.get("posting_date"),
		"stock_entry": entry.get("name"),
		"recipe": entry.get("recipe"),
		"company": entry.get("company"),
		"division": entry.get("division"),
		"item_code": finished_item,
		"planned_qty": rounded(planned),
		"actual_output": rounded(actual),
		"uom": finished_uom,
		"yield_pct": rounded((actual / planned) * 100, 2) if planned else 0,
		"expected_loss_pct": rounded(expected, 2),
		"actual_loss_pct": None if actual_loss is None else rounded(actual_loss, 2),
		"loss_vs_expected": None if variance is None else rounded(variance, 2),
		"total_cost": rounded(cost, 2),
		"cost_per_unit": rounded(cost / actual, 2) if actual else 0,
		"status": status,
		"purpose": entry.get("purpose"),
	}


def register_rows(entries, filters=None) -> list:
	filters = filters or {}
	rows = [conversion_metrics(entry) for entry in entries or [] if _matches(entry, filters)]
	rows.sort(key=lambda row: (str(row.get("posting_date") or ""), str(row.get("stock_entry") or "")))
	return rows


def report_filters(filters) -> list:
	"""frappe.get_all filters for the register. Cancelled rows stay out unless asked for."""
	filters = filters or {}
	rows = [
		["purpose", "in", [MANUFACTURE, REPACK]],
		["recipe", "!=", ""],
	]
	if not as_bool(filters.get("include_cancelled")):
		rows.append(["docstatus", "!=", 2])
	if clean(filters.get("company")):
		rows.append(["company", "=", clean(filters["company"])])
	elif filters.get("companies"):
		rows.append(["company", "in", [clean(row) for row in filters["companies"] if clean(row)]])
	if clean(filters.get("division")):
		rows.append(["division", "=", clean(filters["division"])])
	elif filters.get("divisions"):
		rows.append(["division", "in", [clean(row) for row in filters["divisions"] if clean(row)]])
	if clean(filters.get("recipe")):
		rows.append(["recipe", "=", clean(filters["recipe"])])
	if filters.get("from_date"):
		rows.append(["posting_date", ">=", filters["from_date"]])
	if filters.get("to_date"):
		rows.append(["posting_date", "<=", filters["to_date"]])
	return rows


def sidebar_item(link) -> dict:
	return {
		"added": 0,
		"child": 0,
		"collapsible": 0,
		"is_default_module": 0,
		"hidden": 0,
		"icon": link["icon"],
		"indent": 0,
		"keep_closed": 0,
		"label": link["label"],
		"link_to": link["link_to"],
		"link_type": link["link_type"],
		"open_in_new_tab": 0,
		"show_arrow": 0,
		"type": "Link",
		"url": "",
	}


def missing_sidebar_links(existing) -> list:
	have = {(link_type, link_to) for link_type, link_to in existing or []}
	return [sidebar_item(link) for link in RECIPE_LINKS if (link["link_type"], link["link_to"]) not in have]


def workspace_shortcut(link) -> dict:
	kind = link["link_type"]
	row = {
		"label": link["label"],
		"link_to": link["link_to"],
		"type": kind,
		"icon": link["icon"],
		"color": "",
		"url": "",
		"stats_filter": "",
		"format": "",
		"doc_view": "List" if kind == "DocType" else "",
	}
	if kind == "Report":
		row["report_ref_doctype"] = link.get("report_ref_doctype") or ""
	return row


def stock_entry_fields() -> dict:
	"""Custom fields written on migrate. Nothing here is a recipe or a quantity."""
	division = {
		"fieldname": "division",
		"label": "Division",
		"fieldtype": "Link",
		"options": "Division",
		"insert_after": "company",
		"in_standard_filter": 1,
		"link_filters": '[["Division","company","=","eval:doc.company"]]',
	}
	return {
		"Stock Entry": [
			division,
			{
				"fieldname": "recipe",
				"label": "Recipe",
				"fieldtype": "Link",
				"options": "Recipe",
				"insert_after": "bom_no",
				"in_standard_filter": 1,
				"read_only": 1,
			},
			{
				"fieldname": "planned_qty",
				"label": "Planned Qty",
				"fieldtype": "Float",
				"insert_after": "fg_completed_qty",
				"read_only": 1,
				"description": "The quantity asked for on Convert Stock.",
			},
			{
				"fieldname": "expected_loss_pct",
				"label": "Expected Loss %",
				"fieldtype": "Percent",
				"insert_after": "planned_qty",
				"read_only": 1,
			},
			{
				"fieldname": "loss_free_qty",
				"label": "Loss-free ingredient qty",
				"fieldtype": "Float",
				"insert_after": "expected_loss_pct",
				"read_only": 1,
				"hidden": 1,
			},
			{
				"fieldname": "confirm_shortfall",
				"label": "Convert despite short stock",
				"fieldtype": "Check",
				"insert_after": "loss_free_qty",
				"description": "Manufacturing Manager or System Manager only.",
			},
		],
		"BOM": [
			dict(division),
			{
				"fieldname": "recipe",
				"label": "Recipe",
				"fieldtype": "Link",
				"options": "Recipe",
				"insert_after": "item",
				"read_only": 1,
				"in_standard_filter": 1,
			},
		],
		"Stock Entry Detail": [
			{
				"fieldname": "recipe_line_type",
				"label": "Recipe Line",
				"fieldtype": "Data",
				"insert_after": "item_code",
				"read_only": 1,
				"hidden": 1,
			}
		],
	}
