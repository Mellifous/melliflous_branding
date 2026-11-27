// Convert Stock. Pick a recipe and a quantity. Convert submits a Stock Entry.
frappe.pages["convert-stock"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Convert Stock"),
		single_column: true,
	});
	ensureRecipeStyles();
	const root = document.createElement("div");
	root.className = "melliflous-quick melliflous-convert";
	page.body.append(root);

	const state = {
		sources: [],
		preview: null,
		lines: [],
		busy: false,
	};

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

	function qtyText(value) {
		const number = Number(value);
		if (!isFinite(number)) return "0";
		return String(Math.round((number + Number.EPSILON) * 1e6) / 1e6);
	}

	function money(value) {
		const number = Number(value);
		if (!isFinite(number)) return "0.00";
		return (Math.round((number + Number.EPSILON) * 100) / 100).toFixed(2);
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
			return __("Could not convert. Check the recipe, warehouses, and quantities.");
		}
	}

	function linkControl(parent, df) {
		return frappe.ui.form.make_control({ parent: $(parent), df, render_input: true });
	}

	const note = banner();
	root.appendChild(
		el(
			"p",
			"intro",
			__(
				"Choose the company, division, recipe, and how much to make. Convert submits a stock entry, so raw materials and packs leave the source warehouse and the finished item enters the target warehouse."
			)
		)
	);

	const companySlot = el("div");
	const divisionSlot = el("div");
	const recipeSlot = el("div");
	root.appendChild(companySlot);
	root.appendChild(divisionSlot);
	root.appendChild(recipeSlot);

	const company = linkControl(companySlot, {
		fieldtype: "Link",
		options: "Company",
		fieldname: "company",
		label: __("Company"),
		reqd: 1,
		onchange() {
			if (division.get_value()) division.set_value("");
			schedule();
		},
	});
	const division = linkControl(divisionSlot, {
		fieldtype: "Link",
		options: "Division",
		fieldname: "division",
		label: __("Division"),
		reqd: 1,
		get_query() {
			return { filters: { company: company.get_value() || "", is_active: 1 } };
		},
		onchange: schedule,
	});
	const recipe = linkControl(recipeSlot, {
		fieldtype: "Link",
		options: "Recipe",
		fieldname: "recipe",
		label: __("Recipe"),
		reqd: 1,
		get_query() {
			const filters = { is_active: 1 };
			if (company.get_value()) filters.company = company.get_value();
			return { filters };
		},
		onchange: schedule,
	});

	const qtyLabel = el("label", "", __("Quantity to produce"));
	const qty = el("input", "form-control");
	qty.type = "number";
	qty.min = "0";
	qty.step = "any";
	qty.inputMode = "decimal";
	qty.value = "1";
	qty.setAttribute("aria-label", __("Quantity to produce"));
	qty.addEventListener("change", schedule);
	root.appendChild(qtyLabel);
	root.appendChild(qty);

	const sourceHeading = el("h2", "", __("Source warehouses"));
	root.appendChild(sourceHeading);
	root.appendChild(
		el("p", "intro", __("Materials are taken from the first warehouse that has stock, then the next."))
	);
	const sourceHost = el("div");
	root.appendChild(sourceHost);
	const addSource = el("button", "btn btn-default", __("Add source warehouse"));
	addSource.type = "button";
	addSource.style.minHeight = "48px";
	addSource.style.marginTop = "8px";
	addSource.addEventListener("click", () => addWarehouse());
	root.appendChild(addSource);

	const targetSlot = el("div");
	root.appendChild(targetSlot);
	const target = linkControl(targetSlot, {
		fieldtype: "Link",
		options: "Warehouse",
		fieldname: "target_warehouse",
		label: __("Target warehouse"),
		reqd: 1,
		get_query() {
			return { filters: { company: company.get_value() || "", is_group: 0, disabled: 0 } };
		},
		onchange: schedule,
	});

	const outputLabel = el("label", "", __("Actual output"));
	const output = el("input", "form-control");
	output.type = "number";
	output.min = "0";
	output.step = "any";
	output.inputMode = "decimal";
	output.setAttribute("aria-label", __("Actual output"));
	output.addEventListener("change", () => {
		state.outputEdited = true;
		schedule();
	});
	root.appendChild(outputLabel);
	root.appendChild(output);
	root.appendChild(
		el(
			"p",
			"intro",
			__(
				"Leave actual output equal to the quantity to produce when the batch came out in full. Lower it when the floor got less. Expected process loss is already included in the spice quantities."
			)
		)
	);

	const linesHost = el("div");
	root.appendChild(linesHost);
	const yieldLine = el("p", "yield");
	root.appendChild(yieldLine);

	const totals = el("div", "totals");
	const costValue = el("div", "value", "0.00");
	const unitValue = el("div", "value", "0.00");
	["Estimated cost", "Cost per unit"].forEach((label, index) => {
		const box = el("div", "total");
		box.appendChild(el("div", "label", __(label)));
		box.appendChild(index === 0 ? costValue : unitValue);
		totals.appendChild(box);
	});
	root.appendChild(totals);

	const batchLabel = el("label", "", __("Finished batch no"));
	const batch = el("input", "form-control");
	batch.type = "text";
	batch.autocomplete = "off";
	batch.setAttribute("aria-label", __("Finished batch no"));
	root.appendChild(batchLabel);
	root.appendChild(batch);
	const mfgLabel = el("label", "", __("Manufacturing date"));
	const mfg = el("input", "form-control");
	mfg.type = "date";
	root.appendChild(mfgLabel);
	root.appendChild(mfg);
	const expLabel = el("label", "", __("Expiry date"));
	const exp = el("input", "form-control");
	exp.type = "date";
	root.appendChild(expLabel);
	root.appendChild(exp);

	const confirmRow = el("label", "confirm");
	const confirmBox = el("input");
	confirmBox.type = "checkbox";
	confirmRow.appendChild(confirmBox);
	confirmRow.appendChild(el("span", "", __("Convert despite short stock")));
	confirmRow.hidden = true;
	root.appendChild(confirmRow);
	confirmBox.addEventListener("change", paintActions);

	const convert = el("button", "btn btn-primary btn-convert", __("Convert"));
	const draft = el("button", "btn btn-default btn-draft", __("Save as draft"));
	convert.type = "button";
	draft.type = "button";
	convert.addEventListener("click", () => post(1));
	draft.addEventListener("click", () => post(0));
	root.appendChild(convert);
	root.appendChild(draft);

	const resultHost = el("div");
	root.appendChild(resultHost);
	const recentHeading = el("h2", "", __("Recent conversions"));
	root.appendChild(recentHeading);
	const recentHost = el("div");
	root.appendChild(recentHost);

	function addWarehouse(value) {
		const card = el("div", "line-card");
		const slot = el("div");
		card.appendChild(slot);
		const remove = el("button", "btn btn-default", __("Remove"));
		remove.type = "button";
		remove.style.minHeight = "44px";
		remove.style.marginTop = "8px";
		card.appendChild(remove);
		sourceHost.appendChild(card);
		const control = linkControl(slot, {
			fieldtype: "Link",
			options: "Warehouse",
			fieldname: "source_warehouse",
			label: __("Source warehouse"),
			get_query() {
				return { filters: { company: company.get_value() || "", is_group: 0, disabled: 0 } };
			},
			onchange: schedule,
		});
		if (value) control.set_value(value);
		const entry = { card, control };
		state.sources.push(entry);
		remove.addEventListener("click", () => {
			state.sources = state.sources.filter((row) => row !== entry);
			card.remove();
			if (!state.sources.length) addWarehouse();
			schedule();
		});
	}

	function payload() {
		return {
			recipe: recipe.get_value(),
			company: company.get_value(),
			division: division.get_value(),
			qty: qty.value,
			source_warehouses: state.sources.map((row) => row.control.get_value()).filter(Boolean),
			target_warehouse: target.get_value(),
			actual_output: output.value,
			lines: state.lines.map((row) => ({
				item_code: row.item_code,
				actual_qty: row.input.value,
				batch_no: row.batch ? row.batch.value : "",
			})),
			batch_no: batch.value,
			manufacturing_date: mfg.value,
			expiry_date: exp.value,
			confirm_shortfall: confirmBox.checked ? 1 : 0,
		};
	}

	function paintLines(preview) {
		linesHost.textContent = "";
		state.lines = [];
		(preview.lines || []).forEach((line) => {
			const card = el("div", "line-card" + (line.shortfall > 0 ? " is-short" : ""));
			card.appendChild(el("h3", "", line.item_name || line.item_code));
			card.appendChild(el("div", "", line.line_type || ""));
			const stats = el("div", "stats");
			[
				[__("Need"), qtyText(line.required) + " " + (line.uom || "")],
				[__("In stock"), qtyText(line.available) + " " + (line.uom || "")],
				[__("Short"), qtyText(line.shortfall) + " " + (line.uom || "")],
			].forEach((pair, index) => {
				const stat = el("div", "stat");
				stat.appendChild(el("div", "label", pair[0]));
				const value = el("div", index === 2 ? "value short" : "value", pair[1]);
				stat.appendChild(value);
				stats.appendChild(stat);
			});
			card.appendChild(stats);
			const label = el("label", "", __("Actual qty"));
			const input = el("input", "form-control");
			input.type = "number";
			input.min = "0";
			input.step = "any";
			input.inputMode = "decimal";
			input.value = qtyText(line.actual_qty);
			input.setAttribute("aria-label", __("Actual qty for {0}", [line.item_code]));
			card.appendChild(label);
			card.appendChild(input);
			let batchInput = null;
			if (line.needs_batch) {
				const batchName = el("label", "", __("Batch no"));
				batchInput = el("input", "form-control");
				batchInput.type = "text";
				batchInput.value = line.batch_no || "";
				batchInput.setAttribute("aria-label", __("Batch no for {0}", [line.item_code]));
				card.appendChild(batchName);
				card.appendChild(batchInput);
			}
			const where = (line.splits || [])
				.map((split) => qtyText(split.qty) + " " + (line.uom || "") + " · " + split.warehouse)
				.join("\n");
			if (where) card.appendChild(el("p", "intro", where));
			linesHost.appendChild(card);
			const record = { item_code: line.item_code, input, batch: batchInput, available: Number(line.available) || 0, card };
			input.addEventListener("input", () => {
				const actual = Number(input.value);
				const short = Math.max(0, (isFinite(actual) ? actual : 0) - record.available);
				card.classList.toggle("is-short", short > 0);
			});
			state.lines.push(record);
		});
	}

	function paintActions() {
		const preview = state.preview;
		if (!preview) {
			convert.disabled = true;
			draft.disabled = true;
			return;
		}
		const blocked = preview.has_shortfall && !(preview.can_override && confirmBox.checked);
		confirmRow.hidden = !(preview.has_shortfall && preview.can_override);
		convert.disabled = state.busy || !preview.can_submit || blocked || !!preview.block && !preview.can_override;
		if (preview.has_shortfall && !preview.can_override) convert.disabled = true;
		draft.disabled = state.busy || !preview.can_create;
		yieldLine.textContent = __(
			"{0}. Yield {1}%. Expected loss {2}%.",
			[preview.purpose || "", qtyText(preview.yield_pct), qtyText(preview.expected_loss_pct)]
		);
		costValue.textContent = money(preview.estimated_cost);
		unitValue.textContent = money(preview.cost_per_unit);
		if (!state.outputEdited) output.value = qtyText(preview.actual_output);
	}

	function schedule() {
		clearTimeout(schedule.timer);
		schedule.timer = setTimeout(loadPreview, 350);
	}

	function loadPreview() {
		if (!recipe.get_value() || !qty.value) return;
		frappe.call({
			method: "melliflous_branding.recipe_records.preview_conversion",
			args: payload(),
			callback(response) {
				state.preview = response.message;
				if (!state.preview) return;
				note.clear();
				if (state.preview.uom) outputLabel.textContent = __("Actual output ({0})", [state.preview.uom]);
				paintLines(state.preview);
				if (state.preview.block) note.show(state.preview.block, true);
				paintActions();
			},
			error(response) {
				note.show(serverMessage(response), true);
			},
		});
	}

	function post(submit) {
		note.clear();
		if (!recipe.get_value()) {
			note.show(__("Choose a recipe."), true);
			return;
		}
		state.busy = true;
		paintActions();
		const args = payload();
		args.submit = submit;
		frappe.call({
			method: "melliflous_branding.recipe_records.convert_stock",
			args,
			callback(response) {
				state.busy = false;
				const body = response.message || {};
				state.preview = body.preview || state.preview;
				paintActions();
				resultHost.textContent = "";
				const card = el("div", "recent-card");
				const verb = body.docstatus === 1 ? __("Converted") : __("Saved as draft");
				card.appendChild(el("h3", "", verb + " " + (body.name || "")));
				const open = el("button", "btn btn-default", __("Open stock entry"));
				open.type = "button";
				open.style.minHeight = "48px";
				open.addEventListener("click", () => frappe.set_route("Form", "Stock Entry", body.name));
				card.appendChild(open);
				if (body.docstatus === 1 && state.preview && state.preview.can_cancel) {
					const undo = el("button", "btn btn-default btn-undo", __("Undo this conversion"));
					undo.type = "button";
					undo.addEventListener("click", () => undoEntry(body.name, card));
					card.appendChild(undo);
				}
				resultHost.appendChild(card);
				note.show(verb + " " + body.name, false);
				loadRecent();
			},
			error(response) {
				state.busy = false;
				paintActions();
				note.show(serverMessage(response), true);
			},
		});
	}

	function undoEntry(name, card) {
		frappe.confirm(__("Cancel stock entry {0}? Stock returns to where it was.", [name]), () => {
			frappe.call({
				method: "melliflous_branding.recipe_records.cancel_conversion",
				args: { name },
				callback() {
					if (card) card.remove();
					note.show(__("Cancelled {0}.", [name]), false);
					loadRecent();
				},
				error(response) {
					note.show(serverMessage(response), true);
				},
			});
		});
	}

	function loadRecent() {
		frappe.call({
			method: "melliflous_branding.recipe_records.recent_conversions",
			args: { company: company.get_value(), division: division.get_value() },
			callback(response) {
				const body = response.message || { rows: [] };
				recentHost.textContent = "";
				(body.rows || []).forEach((row) => {
					const card = el("div", "recent-card");
					card.appendChild(el("h3", "", row.recipe || row.name));
					card.appendChild(
						el(
							"p",
							"intro",
							[row.name, row.posting_date, row.division, row.docstatus === 1 ? __("Submitted") : __("Draft")]
								.filter(Boolean)
								.join(" · ")
						)
					);
					if (row.docstatus === 1 && body.can_cancel) {
						const undo = el("button", "btn btn-default btn-undo", __("Undo this conversion"));
						undo.type = "button";
						undo.addEventListener("click", () => undoEntry(row.name, card));
						card.appendChild(undo);
					}
					recentHost.appendChild(card);
				});
			},
		});
	}

	company.set_value(frappe.defaults.get_user_default("company"));
	division.set_value(frappe.defaults.get_user_default("division"));
	if (frappe.route_options && frappe.route_options.recipe) {
		recipe.set_value(frappe.route_options.recipe);
		frappe.route_options = null;
	}
	addWarehouse();
	loadRecent();
	paintActions();
};

function ensureRecipeStyles() {
	if (document.getElementById("melliflous-recipes-css")) return;
	const link = document.createElement("link");
	link.id = "melliflous-recipes-css";
	link.rel = "stylesheet";
	link.href = "/assets/melliflous_branding/css/recipes.css?v=20261127r";
	document.head.appendChild(link);
}
