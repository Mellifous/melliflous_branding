// Quick Invoice. A short draft for Melliflous International Multi Trade.
// Classic price lists are GST-inclusive at 5 percent. The draft stores the rate before GST.
// Save never submits. Frappe reads this file when the page opens.
frappe.pages["quick-invoice"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Quick Invoice"),
		single_column: true,
	});
	const root = document.createElement("div");
	root.className = "melliflous-quick melliflous-invoice";
	page.body.append(root);

	const API = "melliflous_branding.invoice_records";
	const state = { customer: "", price_list: "", rows: [] };

	function el(tag, className, text) {
		const node = document.createElement(tag);
		if (className) node.className = className;
		if (text != null) node.textContent = text;
		return node;
	}

	function money(value) {
		const number = Number(value);
		if (!isFinite(number)) return "0.00";
		return (Math.round((number + Number.EPSILON) * 100) / 100).toFixed(2);
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

	const note = banner();
	root.appendChild(
		el(
			"p",
			"note",
			__(
				"Company: Melliflous International Multi Trade Pvt Ltd. Classic price lists include 5% GST. The rate below is the price before GST."
			)
		)
	);

	const customerHolder = el("div");
	const priceHolder = el("div");
	root.appendChild(customerHolder);
	root.appendChild(priceHolder);
	const price = el("select", "form-control");
	price.setAttribute("aria-label", __("Price List"));
	const priceLabel = el("label", "", __("Price List"));
	priceHolder.appendChild(priceLabel);
	priceHolder.appendChild(price);

	const items = el("div");
	root.appendChild(items);
	const add = el("button", "btn btn-default", __("Add item"));
	add.type = "button";
	add.style.marginTop = "12px";
	add.style.minHeight = "44px";
	root.appendChild(add);

	const totals = el("div", "totals");
	const totalBoxes = {};
	["Taxable", "CGST", "SGST", "Grand total"].forEach((label) => {
		const box = el("div", "total");
		box.appendChild(el("div", "label", __(label)));
		const value = el("div", "value", "0.00");
		box.appendChild(value);
		totals.appendChild(box);
		totalBoxes[label] = value;
	});
	root.appendChild(totals);

	const actions = el("div", "btn-row");
	const saveInvoice = el("button", "btn btn-primary", __("Save as Draft"));
	const saveQuote = el("button", "btn btn-default", __("Save as Draft Quotation"));
	saveInvoice.type = "button";
	saveQuote.type = "button";
	actions.appendChild(saveInvoice);
	actions.appendChild(saveQuote);
	root.appendChild(actions);

	const customer = frappe.ui.form.make_control({
		parent: $(customerHolder),
		df: {
			fieldtype: "Link",
			options: "Customer",
			fieldname: "customer",
			label: __("Customer"),
			reqd: 1,
			onchange() {
				state.customer = customer.get_value() || "";
				loadOptions(state.customer);
			},
		},
		render_input: true,
	});

	function control(parent, df) {
		return frappe.ui.form.make_control({ parent: $(parent), df, render_input: true });
	}

	function paintTotals() {
		let taxable = 0;
		let cgst = 0;
		let sgst = 0;
		state.rows.forEach((row) => {
			const qty = Number(row.qty.get_value()) || 0;
			const rate = Number(row.rate) || 0;
			const amount = Number(money(qty * rate));
			const tax = Number(money((amount * (Number(row.tax_percent) || 0)) / 100));
			const half = Number(money(tax / 2));
			taxable += amount;
			cgst += half;
			sgst += Number(money(tax - half));
		});
		totalBoxes.Taxable.textContent = money(taxable);
		totalBoxes.CGST.textContent = money(cgst);
		totalBoxes.SGST.textContent = money(sgst);
		totalBoxes["Grand total"].textContent = money(taxable + cgst + sgst);
	}

	function addRow() {
		const card = el("div", "row-card");
		const itemSlot = el("div");
		const qtySlot = el("div");
		const rateSlot = el("div");
		const batchSlot = el("div");
		card.appendChild(itemSlot);
		card.appendChild(qtySlot);
		card.appendChild(rateSlot);
		card.appendChild(batchSlot);
		const remove = el("button", "btn btn-default", __("Remove"));
		remove.type = "button";
		remove.style.marginTop = "8px";
		remove.style.minHeight = "44px";
		card.appendChild(remove);
		items.appendChild(card);

		const row = { rate: 0, tax_percent: 0, batchTouched: false, card };
		row.item = control(itemSlot, {
			fieldtype: "Link",
			options: "Item",
			label: __("Item"),
			reqd: 1,
			onchange() {
				quoteRow(row);
			},
		});
		row.qty = control(qtySlot, {
			fieldtype: "Float",
			label: __("Qty"),
			reqd: 1,
			default: 1,
			onchange() {
				quoteRow(row);
				paintTotals();
			},
		});
		row.qty.set_value(1);
		row.rateField = control(rateSlot, {
			fieldtype: "Currency",
			label: __("Rate before GST"),
			read_only: 1,
		});
		row.batch = control(batchSlot, {
			fieldtype: "Link",
			options: "Batch",
			label: __("Batch"),
			onchange() {
				row.batchTouched = true;
			},
			get_query() {
				const item = row.item.get_value();
				return item ? { filters: { item: item } } : {};
			},
		});
		remove.addEventListener("click", () => {
			card.remove();
			state.rows = state.rows.filter((entry) => entry !== row);
			if (!state.rows.length) addRow();
			paintTotals();
		});
		state.rows.push(row);
		paintTotals();
	}

	function quoteRow(row) {
		const item = row.item.get_value();
		if (!item || !state.price_list) {
			row.rate = 0;
			row.tax_percent = 0;
			row.rateField.set_value(0);
			paintTotals();
			return;
		}
		frappe
			.call({
				method: API + ".item_quote",
				args: {
					item_code: item,
					price_list: state.price_list,
					customer: state.customer,
					qty: row.qty.get_value() || 1,
				},
			})
			.then((response) => {
				const quote = response && response.message;
				if (!quote) return;
				row.rate = Number(quote.rate) || 0;
				row.tax_percent = Number(quote.tax_percent) || 0;
				row.rateField.set_value(row.rate);
				if (quote.batch_no && !row.batchTouched) row.batch.set_value(quote.batch_no);
				paintTotals();
			})
			.catch((response) => {
				note.show(serverMessage(response), true);
			});
	}

	function fillPrices(names, selected) {
		const current = selected || state.price_list;
		price.replaceChildren();
		(names || []).forEach((name) => {
			const option = el("option", "", name);
			option.value = name;
			price.appendChild(option);
		});
		if (current) price.value = current;
		state.price_list = price.value || "";
	}

	function loadOptions(customerName) {
		frappe
			.call({ method: API + ".form_options", args: { customer: customerName || "" } })
			.then((response) => {
				const data = (response && response.message) || {};
				fillPrices(data.price_lists, data.price_list);
				state.rows.forEach(quoteRow);
			})
			.catch((response) => note.show(serverMessage(response), true));
	}

	function payload(doctype) {
		return {
			doctype: doctype,
			customer: customer.get_value() || "",
			price_list: price.value || "",
			items: state.rows.map((row) => ({
				item_code: row.item.get_value() || "",
				qty: row.qty.get_value(),
				batch_no: row.batch.get_value() || "",
			})),
		};
	}

	function clientErrors(body) {
		if (!String(body.customer || "").trim()) return __("Choose a customer first.");
		if (!String(body.price_list || "").trim()) return __("Choose a price list.");
		if (!body.items.length) return __("Add at least one item.");
		for (let index = 0; index < body.items.length; index += 1) {
			const row = body.items[index];
			if (!String(row.item_code || "").trim()) return __("Pick an item on row {0}.", [index + 1]);
			const qty = Number(row.qty);
			if (!isFinite(qty) || qty <= 0) {
				const name = row.item_code || __("row {0}", [index + 1]);
				return __("Enter a quantity greater than zero for {0}.", [name]);
			}
		}
		return "";
	}

	function serverMessage(response) {
		const raw = response && (response._server_messages || (response.responseJSON && response.responseJSON._server_messages));
		try {
			const list = JSON.parse(raw);
			return list
				.map((row) => {
					try {
						const parsed = JSON.parse(row);
						return parsed.message || "";
					} catch (error) {
						return String(row || "");
					}
				})
				.filter(Boolean)
				.join(" ");
		} catch (error) {
			return __("Could not save the draft. Check the customer and items, then try again.");
		}
	}

	function save(doctype) {
		note.clear();
		const body = payload(doctype);
		const problem = clientErrors(body);
		if (problem) {
			note.show(problem, true);
			return;
		}
		saveInvoice.disabled = true;
		saveQuote.disabled = true;
		frappe
			.call({ method: API + ".save_draft", args: { payload: body } })
			.then((response) => {
				const message = response && response.message;
				if (!message || !message.name) throw response;
				note.show(message.message || __("Draft saved."), false);
				frappe.set_route("Form", message.doctype, message.name);
			})
			.catch((response) => {
				note.show(serverMessage(response), true);
			})
			.then(() => {
				saveInvoice.disabled = false;
				saveQuote.disabled = false;
			});
	}

	price.addEventListener("change", () => {
		state.price_list = price.value || "";
		state.rows.forEach(quoteRow);
	});
	add.addEventListener("click", () => addRow());
	saveInvoice.addEventListener("click", () => save("Sales Invoice"));
	saveQuote.addEventListener("click", () => save("Quotation"));

	addRow();
	loadOptions("");
	paintTotals();
};
