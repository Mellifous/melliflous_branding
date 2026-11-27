// Recipes. A short form that saves a recipe and the BOM behind it.
frappe.pages["recipes"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Recipes"),
		single_column: true,
	});
	ensureRecipeStyles();
	const root = document.createElement("div");
	root.className = "melliflous-quick melliflous-recipe";
	page.body.append(root);

	const state = { mode: "percent", ingredients: [], packaging: [], subs: [], name: "", canWrite: false };

	function el(tag, className, text) {
		const node = document.createElement(tag);
		if (className) node.className = className;
		if (text != null) node.textContent = text;
		return node;
	}

	function banner() {
		const node = el("div", "banner");
		node.hidden = true;
		root.appendChild(node);
		return {
			show(message, isError) {
				node.hidden = false;
				node.classList.toggle("is-error", !!isError);
				node.textContent = message;
			},
			clear() {
				node.hidden = true;
				node.textContent = "";
			},
		};
	}

	function serverMessage(response) {
		const raw =
			response &&
			(response._server_messages || (response.responseJSON && response.responseJSON._server_messages));
		try {
			const list = JSON.parse(raw);
			return list
				.map((row) => {
					try {
						return JSON.parse(row).message || "";
					} catch (error) {
						return String(row || "");
					}
				})
				.filter(Boolean)
				.join(" ");
		} catch (error) {
			return __("Could not save the recipe.");
		}
	}

	function linkControl(parent, df) {
		return frappe.ui.form.make_control({ parent: $(parent), df, render_input: true });
	}

	function qtyOf(batch, percentage, loss) {
		const qty = (Number(batch) || 0) * ((Number(percentage) || 0) / 100) * (1 + (Number(loss) || 0) / 100);
		return Math.round((qty + Number.EPSILON) * 1e6) / 1e6;
	}

	const note = banner();
	root.appendChild(
		el(
			"p",
			"intro",
			__(
				"A recipe is the blend or the pack. Saving it writes a BOM. Percentages are the blend before process loss, and the loss adds extra spice. Packs and sub-recipes use the quantity you type."
			)
		)
	);

	const listHost = el("div");
	root.appendChild(listHost);
	const create = el("button", "btn btn-primary btn-save", __("New recipe"));
	create.type = "button";
	create.addEventListener("click", () => openForm(null));
	root.appendChild(create);

	const form = el("div");
	form.hidden = true;
	root.appendChild(form);

	const nameLabel = el("label", "", __("Recipe name"));
	const nameInput = el("input", "form-control");
	nameInput.type = "text";
	nameInput.setAttribute("aria-label", __("Recipe name"));
	form.appendChild(nameLabel);
	form.appendChild(nameInput);

	const companySlot = el("div");
	const divisionSlot = el("div");
	const itemSlot = el("div");
	form.appendChild(companySlot);
	form.appendChild(divisionSlot);
	form.appendChild(itemSlot);
	const company = linkControl(companySlot, {
		fieldtype: "Link",
		options: "Company",
		fieldname: "company",
		label: __("Company"),
		reqd: 1,
	});
	const division = linkControl(divisionSlot, {
		fieldtype: "Link",
		options: "Division",
		fieldname: "division",
		label: __("Division"),
		get_query() {
			return { filters: { company: company.get_value() || "", is_active: 1 } };
		},
	});
	const item = linkControl(itemSlot, {
		fieldtype: "Link",
		options: "Item",
		fieldname: "item",
		label: __("Finished item"),
		reqd: 1,
		get_query: () => ({ filters: { is_stock_item: 1, disabled: 0 } }),
		onchange() {
			const value = item.get_value();
			if (!value) return;
			frappe.db.get_value("Item", value, "stock_uom").then((response) => {
				const uom = response.message && response.message.stock_uom;
				if (uom) uomControl.set_value(uom);
			});
		},
	});

	const qtyLabel = el("label", "", __("Output quantity"));
	const qty = el("input", "form-control");
	qty.type = "number";
	qty.min = "0";
	qty.step = "any";
	qty.value = "1";
	qty.addEventListener("input", paintMath);
	form.appendChild(qtyLabel);
	form.appendChild(qty);
	const uomSlot = el("div");
	form.appendChild(uomSlot);
	const uomControl = linkControl(uomSlot, {
		fieldtype: "Link",
		options: "UOM",
		fieldname: "uom",
		label: __("Output UOM"),
		reqd: 1,
	});
	const lossLabel = el("label", "", __("Expected process loss %"));
	const loss = el("input", "form-control");
	loss.type = "number";
	loss.min = "0";
	loss.max = "100";
	loss.step = "any";
	loss.value = "0";
	loss.addEventListener("input", paintMath);
	form.appendChild(lossLabel);
	form.appendChild(loss);

	const mode = el("div", "mode");
	const byPercent = el("button", "btn btn-default is-on", __("By percent"));
	const byQty = el("button", "btn btn-default", __("By quantity"));
	byPercent.type = "button";
	byQty.type = "button";
	mode.appendChild(byPercent);
	mode.appendChild(byQty);
	form.appendChild(mode);
	byPercent.addEventListener("click", () => setMode("percent"));
	byQty.addEventListener("click", () => setMode("qty"));

	form.appendChild(el("h2", "", __("Ingredients")));
	const ingredientHost = el("div");
	form.appendChild(ingredientHost);
	const addIngredient = el("button", "btn btn-default", __("Add ingredient"));
	addIngredient.type = "button";
	addIngredient.style.minHeight = "48px";
	addIngredient.addEventListener("click", () => pushIngredient());
	form.appendChild(addIngredient);
	const pct = el("p", "pct");
	form.appendChild(pct);

	form.appendChild(el("h2", "", __("Packaging")));
	const packHost = el("div");
	form.appendChild(packHost);
	const addPack = el("button", "btn btn-default", __("Add pack"));
	addPack.type = "button";
	addPack.style.minHeight = "48px";
	addPack.addEventListener("click", () => pushPack());
	form.appendChild(addPack);

	form.appendChild(el("h2", "", __("Sub-recipes")));
	const subHost = el("div");
	form.appendChild(subHost);
	const addSub = el("button", "btn btn-default", __("Add sub-recipe"));
	addSub.type = "button";
	addSub.style.minHeight = "48px";
	addSub.addEventListener("click", () => pushSub());
	form.appendChild(addSub);
	form.appendChild(
		el(
			"p",
			"intro",
			__("A sub-recipe is a bulk blend you already make. Packing consumes that blend from stock. It does not grind the spices again.")
		)
	);

	const notesLabel = el("label", "", __("Notes"));
	const notes = el("textarea", "form-control");
	notes.rows = 3;
	form.appendChild(notesLabel);
	form.appendChild(notes);

	const save = el("button", "btn btn-primary btn-save", __("Save recipe"));
	save.type = "button";
	save.addEventListener("click", saveRecipe);
	form.appendChild(save);
	const convertLink = el("button", "btn btn-default btn-save", __("Convert this recipe"));
	convertLink.type = "button";
	convertLink.addEventListener("click", () => {
		if (!state.name) {
			note.show(__("Save the recipe first."), true);
			return;
		}
		frappe.route_options = { recipe: state.name };
		frappe.set_route("convert-stock");
	});
	form.appendChild(convertLink);

	function setMode(next) {
		state.mode = next;
		byPercent.classList.toggle("is-on", next === "percent");
		byQty.classList.toggle("is-on", next === "qty");
		state.ingredients.forEach((row) => {
			row.percent.hidden = next !== "percent";
			row.percentLabel.hidden = next !== "percent";
			row.qty.hidden = next === "percent";
			row.qtyLabel.hidden = next === "percent";
			row.computed.hidden = next !== "percent";
		});
		paintMath();
	}

	function pushIngredient(values) {
		values = values || {};
		const card = el("div", "line-card");
		const itemSlot = el("div");
		const uomSlot = el("div");
		card.appendChild(itemSlot);
		const percentLabel = el("label", "", __("Percent"));
		const percent = el("input", "form-control");
		percent.type = "number";
		percent.min = "0";
		percent.max = "100";
		percent.step = "any";
		percent.value = values.percentage || "";
		percent.addEventListener("input", paintMath);
		const qtyLabel = el("label", "", __("Qty"));
		const qtyInput = el("input", "form-control");
		qtyInput.type = "number";
		qtyInput.min = "0";
		qtyInput.step = "any";
		qtyInput.value = values.qty || "";
		const computed = el("p", "intro", "");
		card.appendChild(percentLabel);
		card.appendChild(percent);
		card.appendChild(qtyLabel);
		card.appendChild(qtyInput);
		card.appendChild(computed);
		card.appendChild(uomSlot);
		const remove = el("button", "btn btn-default", __("Remove"));
		remove.type = "button";
		remove.style.minHeight = "44px";
		card.appendChild(remove);
		ingredientHost.appendChild(card);
		const itemControl = linkControl(itemSlot, {
			fieldtype: "Link",
			options: "Item",
			fieldname: "ingredient",
			label: __("Ingredient"),
			get_query: () => ({ filters: { is_stock_item: 1, disabled: 0 } }),
			onchange() {
				const chosen = itemControl.get_value();
				if (!chosen) return;
				frappe.db.get_value("Item", chosen, "stock_uom").then((response) => {
					const uom = response.message && response.message.stock_uom;
					if (uom) uomField.set_value(uom);
				});
			},
		});
		const uomField = linkControl(uomSlot, {
			fieldtype: "Link",
			options: "UOM",
			fieldname: "uom",
			label: __("UOM"),
		});
		if (values.item_code) itemControl.set_value(values.item_code);
		if (values.uom) uomField.set_value(values.uom);
		const record = { card, item: itemControl, percent, percentLabel, qty: qtyInput, qtyLabel, computed, uom: uomField };
		state.ingredients.push(record);
		remove.addEventListener("click", () => {
			state.ingredients = state.ingredients.filter((row) => row !== record);
			card.remove();
			paintMath();
		});
		setMode(state.mode);
	}

	function pushPack(values) {
		values = values || {};
		const card = el("div", "line-card");
		const itemSlot = el("div");
		const uomSlot = el("div");
		card.appendChild(itemSlot);
		const qtyLabel = el("label", "", __("Qty for this output"));
		const qtyInput = el("input", "form-control");
		qtyInput.type = "number";
		qtyInput.min = "0";
		qtyInput.step = "any";
		qtyInput.value = values.qty || "";
		card.appendChild(qtyLabel);
		card.appendChild(qtyInput);
		card.appendChild(uomSlot);
		const remove = el("button", "btn btn-default", __("Remove"));
		remove.type = "button";
		remove.style.minHeight = "44px";
		card.appendChild(remove);
		packHost.appendChild(card);
		const itemControl = linkControl(itemSlot, {
			fieldtype: "Link",
			options: "Item",
			fieldname: "pack",
			label: __("Pack"),
			get_query: () => ({ filters: { is_stock_item: 1, disabled: 0 } }),
		});
		const uomField = linkControl(uomSlot, {
			fieldtype: "Link",
			options: "UOM",
			fieldname: "uom",
			label: __("UOM"),
		});
		if (values.item_code) itemControl.set_value(values.item_code);
		if (values.uom) uomField.set_value(values.uom);
		const record = { card, item: itemControl, qty: qtyInput, uom: uomField };
		state.packaging.push(record);
		remove.addEventListener("click", () => {
			state.packaging = state.packaging.filter((row) => row !== record);
			card.remove();
		});
	}

	function pushSub(values) {
		values = values || {};
		const card = el("div", "line-card");
		const recipeSlot = el("div");
		const uomSlot = el("div");
		card.appendChild(recipeSlot);
		const qtyLabel = el("label", "", __("Qty for this output"));
		const qtyInput = el("input", "form-control");
		qtyInput.type = "number";
		qtyInput.min = "0";
		qtyInput.step = "any";
		qtyInput.value = values.qty || "";
		card.appendChild(qtyLabel);
		card.appendChild(qtyInput);
		card.appendChild(uomSlot);
		const remove = el("button", "btn btn-default", __("Remove"));
		remove.type = "button";
		remove.style.minHeight = "44px";
		card.appendChild(remove);
		subHost.appendChild(card);
		const recipeControl = linkControl(recipeSlot, {
			fieldtype: "Link",
			options: "Recipe",
			fieldname: "sub_recipe",
			label: __("Sub-recipe"),
			get_query() {
				return { filters: { is_active: 1, name: ["!=", state.name || ""] } };
			},
			onchange() {
				const chosen = recipeControl.get_value();
				if (!chosen) return;
				frappe.db.get_value("Recipe", chosen, "uom").then((response) => {
					const uom = response.message && response.message.uom;
					if (uom) uomField.set_value(uom);
				});
			},
		});
		const uomField = linkControl(uomSlot, {
			fieldtype: "Link",
			options: "UOM",
			fieldname: "uom",
			label: __("UOM"),
		});
		if (values.sub_recipe) recipeControl.set_value(values.sub_recipe);
		if (values.uom) uomField.set_value(values.uom);
		const record = { card, recipe: recipeControl, qty: qtyInput, uom: uomField };
		state.subs.push(record);
		remove.addEventListener("click", () => {
			state.subs = state.subs.filter((row) => row !== record);
			card.remove();
		});
	}

	function paintMath() {
		let total = 0;
		state.ingredients.forEach((row) => {
			const percentage = Number(row.percent.value) || 0;
			total += percentage;
			const computed = qtyOf(qty.value, percentage, loss.value);
			row.computed.textContent = percentage ? __("Uses {0}", [String(computed)]) : "";
		});
		const shown = Math.round(total * 1000) / 1000;
		if (state.mode !== "percent" || !state.ingredients.length) {
			pct.textContent = "";
			return;
		}
		const ok = Math.abs(shown - 100) <= 0.001;
		pct.classList.toggle("is-ok", ok);
		pct.classList.toggle("is-bad", !ok);
		pct.textContent = __("Ingredients add up to {0}%. They need to add up to 100%.", [shown]);
		if (ok) pct.textContent = __("Ingredients add up to 100%.");
	}

	function clearLines() {
		state.ingredients = [];
		state.packaging = [];
		state.subs = [];
		ingredientHost.textContent = "";
		packHost.textContent = "";
		subHost.textContent = "";
	}

	function openForm(detail) {
		form.hidden = false;
		clearLines();
		state.name = detail ? detail.name : "";
		nameInput.value = detail ? detail.recipe_name || detail.name : "";
		nameInput.disabled = !!detail;
		company.set_value((detail && detail.company) || frappe.defaults.get_user_default("company"));
		division.set_value((detail && detail.division) || frappe.defaults.get_user_default("division"));
		item.set_value(detail ? detail.item : "");
		qty.value = detail ? detail.qty : 1;
		uomControl.set_value(detail ? detail.uom : "");
		loss.value = detail ? detail.process_loss_percentage || 0 : 0;
		notes.value = detail ? detail.notes || "" : "";
		const usesPercent = !detail || (detail.ingredients || []).some((row) => row.percentage);
		setMode(usesPercent ? "percent" : "qty");
		(detail && detail.ingredients ? detail.ingredients : []).forEach(pushIngredient);
		(detail && detail.packaging ? detail.packaging : []).forEach(pushPack);
		(detail && detail.sub_assemblies ? detail.sub_assemblies : []).forEach(pushSub);
		if (!detail) pushIngredient();
		save.hidden = detail ? !detail.can_write : !state.canWrite;
		paintMath();
		form.scrollIntoView({ block: "start" });
	}

	function saveRecipe() {
		note.clear();
		const body = {
			recipe_name: nameInput.value,
			company: company.get_value(),
			division: division.get_value(),
			item: item.get_value(),
			qty: qty.value,
			uom: uomControl.get_value(),
			process_loss_percentage: loss.value,
			is_active: 1,
			notes: notes.value,
			ingredients: state.ingredients.map((row) => ({
				item_code: row.item.get_value(),
				percentage: state.mode === "percent" ? row.percent.value : "",
				qty: state.mode === "qty" ? row.qty.value : "",
				uom: row.uom.get_value(),
			})),
			packaging: state.packaging.map((row) => ({
				item_code: row.item.get_value(),
				qty: row.qty.value,
				uom: row.uom.get_value(),
			})),
			sub_assemblies: state.subs.map((row) => ({
				sub_recipe: row.recipe.get_value(),
				qty: row.qty.value,
				uom: row.uom.get_value(),
			})),
		};
		save.disabled = true;
		frappe.call({
			method: "melliflous_branding.recipe_records.save_recipe",
			args: { payload: body },
			callback(response) {
				save.disabled = false;
				const saved = response.message || {};
				state.name = saved.name || state.name;
				nameInput.disabled = true;
				note.show(__("Saved {0}. BOM {1}.", [saved.name || "", saved.bom || ""]), false);
				loadList();
			},
			error(response) {
				save.disabled = false;
				note.show(serverMessage(response), true);
			},
		});
	}

	function loadList() {
		frappe.call({
			method: "melliflous_branding.recipe_records.list_recipes",
			args: {
				company: frappe.defaults.get_user_default("company"),
				division: frappe.defaults.get_user_default("division"),
			},
			callback(response) {
				const body = response.message || { recipes: [] };
				state.canWrite = !!body.can_write;
				create.hidden = !state.canWrite;
				listHost.textContent = "";
				(body.recipes || []).forEach((row) => {
					const card = el("div", "line-card");
					card.appendChild(el("h3", "", row.recipe_name || row.name));
					card.appendChild(
						el(
							"p",
							"intro",
							[row.item_name || row.item, String(row.qty) + " " + (row.uom || ""), row.division]
								.filter(Boolean)
								.join(" · ")
						)
					);
					const edit = el("button", "btn btn-default", __("Open"));
					edit.type = "button";
					edit.style.minHeight = "48px";
					edit.addEventListener("click", () => {
						frappe.call({
							method: "melliflous_branding.recipe_records.recipe_detail",
							args: { name: row.name },
							callback(detail) {
								openForm(detail.message);
							},
							error(errorResponse) {
								note.show(serverMessage(errorResponse), true);
							},
						});
					});
					card.appendChild(edit);
					listHost.appendChild(card);
				});
			},
		});
	}

	loadList();
};

function ensureRecipeStyles() {
	if (document.getElementById("melliflous-recipes-css")) return;
	const link = document.createElement("link");
	link.id = "melliflous-recipes-css";
	link.rel = "stylesheet";
	link.href = "/assets/melliflous_branding/css/recipes.css?v=20261127r";
	document.head.appendChild(link);
}
