// Distributor 360. Frappe evals this file when the page opens. The body is drawn
// here, and a failed call is written into the page instead of failing silently.
(function () {
	const API = "melliflous_branding.distributor_records";
	const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
	const TABS = [
		["invoices", "Invoices"],
		["credit_notes", "Credit Notes"],
		["payments", "Payments"],
		["visits", "Visits"],
		["statements", "Stock Statements"],
		["complaints", "Complaints"],
	];

	function el(tag, className, text) {
		const node = document.createElement(tag);
		if (className) node.className = className;
		if (text != null) node.textContent = text;
		return node;
	}

	function plain(text) {
		return String(text || "")
			.replace(/<[^>]*>/g, "")
			.trim();
	}

	function errorText(error) {
		const payload = (error && (error.responseJSON || error)) || {};
		if (payload._server_messages) {
			try {
				const messages = JSON.parse(payload._server_messages);
				const first = JSON.parse(messages[0]);
				if (first && first.message) return plain(first.message);
			} catch (ignored) {
				/* use the fallback below */
			}
		}
		if (payload.exception) {
			const parts = String(payload.exception).split(":");
			const last = plain(parts[parts.length - 1]);
			if (last) return last;
		}
		if (payload.message) return plain(payload.message);
		if (error && error.message) return plain(error.message);
		return __("Something went wrong. Please try again.");
	}

	function contentHost(page, wrapper) {
		if (page && page.main && page.main[0]) return page.main[0];
		return (
			wrapper.querySelector(".layout-main-section") ||
			wrapper.querySelector(".page-content") ||
			wrapper
		);
	}

	function prettyDate(iso) {
		if (!iso) return "";
		const parts = String(iso).slice(0, 10).split("-");
		if (parts.length < 3) return String(iso);
		return `${Number(parts[2])} ${MONTHS[Number(parts[1]) - 1] || ""} ${parts[0]}`;
	}

	function moneyText(value, currency) {
		if (value == null || value === "") return "—";
		const number = Number(value);
		if (!Number.isFinite(number)) return "—";
		if (window.frappe && frappe.format) {
			try {
				return plain(frappe.format(number, { fieldtype: "Currency", options: currency || "" }));
			} catch (ignored) {
				/* fall through */
			}
		}
		const formatted = number.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
		return currency ? `${currency} ${formatted}` : formatted;
	}

	function docHref(doctype, name) {
		const slug = String(doctype || "")
			.toLowerCase()
			.replace(/ /g, "-");
		return `/desk/${slug}/${encodeURIComponent(name)}`;
	}

	function render(page, wrapper) {
		const host = contentHost(page, wrapper);
		const root = el("div", "melliflous-quick melliflous-360");
		host.replaceChildren(root);

		const note = el("div", "banner");
		note.hidden = true;
		root.appendChild(note);
		function show(message, isError) {
			note.hidden = false;
			note.classList.toggle("is-error", !!isError);
			note.textContent = message;
		}

		root.appendChild(
			el(
				"p",
				"hint",
				__(
					"Primary billing is the company net total before GST. Credit notes are subtracted. Secondary sales come from stock statements."
				)
			)
		);

		const distributorSlot = el("div");
		root.appendChild(el("label", "", __("Distributor")));
		root.appendChild(distributorSlot);
		const companySlot = el("div");
		root.appendChild(el("label", "", __("Company")));
		root.appendChild(companySlot);

		let distributorControl;
		let companyControl;
		try {
			distributorControl = frappe.ui.form.make_control({
				parent: distributorSlot,
				df: {
					fieldtype: "Link",
					options: "Customer",
					fieldname: "distributor",
					label: __("Distributor"),
					change() {
						schedule();
					},
				},
				render_input: true,
			});
			companyControl = frappe.ui.form.make_control({
				parent: companySlot,
				df: {
					fieldtype: "Link",
					options: "Company",
					fieldname: "company",
					label: __("Company"),
					change() {
						schedule();
					},
				},
				render_input: true,
			});
			distributorControl.refresh();
			companyControl.refresh();
		} catch (error) {
			show(errorText(error), true);
			root.appendChild(el("p", "", __("The distributor page could not be built.")));
			return;
		}

		const actions = el("div", "btn-row");
		actions.appendChild(actionButton(__("New Visit"), "btn-primary", () => openNew("Distributor Visit", { visit_date: frappe.datetime.get_today() })));
		actions.appendChild(actionButton(__("New Stock Statement"), "btn-default", () => openNew("Distributor Stock Statement", { statement_month: frappe.datetime.month_start() })));
		actions.appendChild(actionButton(__("New Complaint"), "btn-default", () => openNew("Distributor Complaint", { complaint_date: frappe.datetime.get_today() })));
		root.appendChild(actions);

		const growthLabel = el("label", "", __("Growth % for the next target"));
		const growth = el("input", "form-control");
		growth.type = "number";
		growth.min = "-50";
		growth.max = "200";
		growth.step = "1";
		growth.value = "10";
		root.appendChild(growthLabel);
		root.appendChild(growth);
		root.appendChild(
			el("p", "hint", __("Suggested target is the last three months of primary, including this month, times this growth."))
		);

		const body = el("div");
		root.appendChild(body);

		let requestId = 0;
		let state = null;
		let timer = 0;
		let silence = false;

		function selectedDistributor() {
			return (distributorControl.get_value && distributorControl.get_value()) || "";
		}

		function selectedCompany() {
			return (companyControl.get_value && companyControl.get_value()) || "";
		}

		function schedule() {
			if (silence) return;
			window.clearTimeout(timer);
			timer = window.setTimeout(load, 200);
		}

		function sameView(customer) {
			if (!state || state.customer !== customer) return false;
			if ((state.company || "") !== selectedCompany()) return false;
			const shown = Number(state.suggestion && state.suggestion.growth_pct);
			const asked = Number(growth.value);
			return Number.isFinite(shown) && Number.isFinite(asked) && shown === asked;
		}

		function load() {
			const customer = selectedDistributor();
			body.replaceChildren();
			if (!customer) {
				body.appendChild(el("p", "hint", __("Pick a distributor.")));
				return;
			}
			if (sameView(customer)) {
				draw(state);
				return;
			}
			const current = ++requestId;
			body.appendChild(el("p", "", __("Loading…")));
			note.hidden = true;
			frappe
				.call({
					method: `${API}.dashboard`,
					args: { customer: customer, company: selectedCompany(), growth_pct: growth.value },
				})
				.then((response) => {
					if (current !== requestId) return;
					state = response.message || {};
					if (state.company && selectedCompany() !== state.company) {
						silence = true;
						companyControl.set_value(state.company);
						window.setTimeout(() => {
							silence = false;
						}, 800);
					}
					draw(state);
				})
				.catch((error) => {
					if (current !== requestId) return;
					body.replaceChildren();
					show(errorText(error), true);
					body.appendChild(el("p", "", __("The distributor could not be loaded.")));
				});
		}

		function actionButton(label, className, onClick) {
			const button = el("button", `btn ${className}`, label);
			button.type = "button";
			button.addEventListener("click", onClick);
			return button;
		}

		function openNew(doctype, values) {
			const customer = selectedDistributor();
			if (!customer) {
				show(__("Pick a distributor first."), true);
				return;
			}
			frappe.route_options = Object.assign({ distributor: customer, company: selectedCompany() || (state && state.company) }, values);
			frappe.new_doc(doctype);
		}

		function draw(data) {
			body.replaceChildren();
			const currency = data.currency || "";
			body.appendChild(el("h2", "", data.customer_name || data.customer || __("Distributor")));
			if (!data.profile) {
				const missing = el("p", "hint", __("No distributor profile yet."));
				body.appendChild(missing);
				if (frappe.model && frappe.model.can_create && frappe.model.can_create("Distributor Profile")) {
					const create = actionButton(__("New Profile"), "btn-default", () => {
						frappe.route_options = { customer: data.customer, company: data.company };
						frappe.new_doc("Distributor Profile");
					});
					body.appendChild(create);
				}
			} else {
				const bits = [];
				if (data.profile.area) bits.push(data.profile.area);
				if (data.profile.territory) bits.push(data.profile.territory);
				if (data.profile.visit_frequency) bits.push(data.profile.visit_frequency);
				if (data.profile.account_manager) bits.push(data.profile.account_manager);
				if (data.profile.sales_person || data.profile.salesman) bits.push(data.profile.sales_person || data.profile.salesman);
				if (!data.profile.is_active) bits.push(__("Inactive"));
				if (bits.length) body.appendChild(el("p", "hint", bits.join(" · ")));
			}

			const kpis = el("div", "kpi-grid");
			const last = data.last_billing;
			kpis.appendChild(
				kpi(
					__("Last billing"),
					last ? `${prettyDate(last.posting_date)} · ${moneyText(last.amount, currency)}` : __("No billing yet")
				)
			);
			kpis.appendChild(kpi(__("Primary, this month"), moneyText(data.primary_mtd, currency)));
			kpis.appendChild(kpi(__("Primary, 3 months"), moneyText(data.primary_3m, currency)));
			kpis.appendChild(kpi(__("Primary, 12 months"), moneyText(data.primary_12m, currency)));
			const secondaryLabel = data.statement_month
				? __("Secondary, {0}", [prettyDate(data.statement_month)])
				: __("Secondary sales");
			kpis.appendChild(
				kpi(secondaryLabel, data.secondary_sales == null ? __("No statement") : moneyText(data.secondary_sales, currency))
			);
			kpis.appendChild(
				kpi(
					__("Closing stock"),
					data.closing_value == null
						? __("No statement")
						: `${moneyText(data.closing_value, currency)} · ${Number(data.closing_qty || 0)}`
				)
			);
			kpis.appendChild(kpi(__("Counters"), data.counters == null ? "—" : String(data.counters)));
			kpis.appendChild(kpi(__("Last visit"), data.last_visit ? prettyDate(data.last_visit) : __("No visit yet")));
			kpis.appendChild(
				kpi(__("Days since order"), data.days_since_order == null ? __("No order yet") : String(data.days_since_order))
			);
			kpis.appendChild(kpi(__("Open complaints"), String(data.open_complaints || 0)));
			kpis.appendChild(kpi(__("Outstanding"), moneyText(data.outstanding, currency)));
			body.appendChild(kpis);
			if (data.overdue_amount) {
				body.appendChild(el("p", "hint", __("Overdue receivable: {0}", [moneyText(data.overdue_amount, currency)])));
			}

			body.appendChild(el("h2", "", __("Primary and secondary")));
			body.appendChild(chart(data.chart || []));

			const suggestion = data.suggestion || {};
			body.appendChild(el("h2", "", __("Next target")));
			const monthBits = (suggestion.months || [])
				.filter((row) => row.label)
				.map((row) => `${row.label} ${moneyText(row.primary, currency)}`);
			body.appendChild(
				el(
					"p",
					"",
					__(
						"{0}: average primary {1} at {2}% growth is {3}.",
						[
							suggestion.period_label || __("Next month"),
							moneyText(suggestion.average, currency),
							String(suggestion.growth_pct ?? growth.value),
							moneyText(suggestion.amount, currency),
						]
					)
				)
			);
			if (monthBits.length) body.appendChild(el("p", "hint", monthBits.join(" · ")));
			if (Number(suggestion.amount) > 0) {
				const create = actionButton(__("Create Target"), "btn-primary", () => createTarget(data));
				body.appendChild(create);
			} else {
				body.appendChild(el("p", "hint", __("There is no primary billing in the last three months to base a target on.")));
			}

			body.appendChild(el("h2", "", __("Top products")));
			body.appendChild(products(data.products || [], currency));
			body.appendChild(el("h2", "", __("Product mix")));
			body.appendChild(mix(data.mix || {}));
			body.appendChild(el("h2", "", __("Buying pattern")));
			const buying = data.buying || {};
			const pattern = el("div", "kpi-grid");
			pattern.appendChild(kpi(__("Orders, 12 months"), String(buying.order_count || 0)));
			pattern.appendChild(kpi(__("Average order value"), moneyText(buying.average_order_value, currency)));
			pattern.appendChild(
				kpi(
					__("Average days between orders"),
					buying.average_days_between == null ? "—" : String(buying.average_days_between)
				)
			);
			pattern.appendChild(kpi(__("Orders per month"), String(buying.orders_per_month || 0)));
			body.appendChild(pattern);

			body.appendChild(el("h2", "", __("Records")));
			drawTabs(data.tabs || {}, currency);
		}

		function kpi(label, value) {
			const card = el("div", "kpi");
			card.appendChild(el("div", "label", label));
			card.appendChild(el("div", "value", value));
			return card;
		}

		function chart(rows) {
			const wrap = el("div", "chart");
			const legend = el("div", "legend");
			legend.appendChild(swatch("primary", __("Primary")));
			legend.appendChild(swatch("secondary", __("Secondary")));
			wrap.appendChild(legend);
			const values = [];
			rows.forEach((row) => {
				values.push(Math.abs(Number(row.primary) || 0));
				if (row.secondary != null) values.push(Math.abs(Number(row.secondary) || 0));
			});
			const max = Math.max(1, ...values);
			if (!rows.length) {
				wrap.appendChild(el("p", "hint", __("No billing in the last 12 months.")));
				return wrap;
			}
			rows.forEach((row) => {
				const line = el("div", "month-row");
				line.appendChild(el("div", "month-label", `${row.label || ""} ${String(row.year || "").slice(2)}`));
				const track = el("div", "bar-track");
				track.appendChild(bar("primary", row.primary, max));
				track.appendChild(bar("secondary", row.secondary, max));
				line.appendChild(track);
				wrap.appendChild(line);
			});
			wrap.appendChild(el("p", "hint", __("A month with no stock statement has no secondary bar.")));
			return wrap;
		}

		function swatch(kind, label) {
			const node = el("span", `swatch ${kind}`, label);
			return node;
		}

		function bar(kind, value, max) {
			const row = el("div", "bar-line");
			if (value == null) {
				row.appendChild(el("span", "bar-value", "—"));
				return row;
			}
			const number = Number(value) || 0;
			const width = Math.max(0, Math.min(100, (Math.abs(number) / max) * 100));
			const graphic = el("span", `bar ${kind}`);
			graphic.style.width = `${width}%`;
			row.appendChild(graphic);
			row.appendChild(el("span", "bar-value", number.toLocaleString(undefined, { maximumFractionDigits: 0 })));
			return row;
		}

		function products(rows, currency) {
			if (!rows.length) return el("p", "hint", __("No product sales in the last 12 months."));
			const table = el("table");
			const head = el("tr");
			[__("Item"), __("Qty"), __("Amount"), __("Share")].forEach((label) => head.appendChild(el("th", "", label)));
			table.appendChild(head);
			rows.forEach((row) => {
				const line = el("tr");
				line.appendChild(el("td", "", row.item_name || row.item || ""));
				line.appendChild(el("td", "", String(row.qty ?? "")));
				line.appendChild(el("td", "", moneyText(row.amount, currency)));
				line.appendChild(el("td", "", `${row.share}%`));
				table.appendChild(line);
			});
			const wrap = el("div", "table-wrap");
			wrap.appendChild(table);
			return wrap;
		}

		function mix(data) {
			const items = data.items || [];
			const months = data.months || [];
			if (!items.length) return el("p", "hint", __("No product mix in the last 12 months."));
			const table = el("table");
			const head = el("tr");
			head.appendChild(el("th", "", __("Item")));
			months.forEach((month) => head.appendChild(el("th", "", `${month.label} ${String(month.year || "").slice(2)}`)));
			table.appendChild(head);
			items.forEach((item) => {
				const line = el("tr");
				line.appendChild(el("td", "", item.item_name || item.item || ""));
				(item.shares || []).forEach((share) => {
					line.appendChild(el("td", "", share == null ? "—" : `${share}%`));
				});
				table.appendChild(line);
			});
			const wrap = el("div", "table-wrap");
			wrap.appendChild(table);
			return wrap;
		}

		let activeTab = "invoices";

		function drawTabs(tabs, currency) {
			const chips = el("div", "chips");
			const list = el("div");
			function paint() {
				chips.replaceChildren();
				TABS.forEach((entry) => {
					const button = el("button", "btn btn-default", __(entry[1]));
					button.type = "button";
					button.classList.toggle("is-on", entry[0] === activeTab);
					button.addEventListener("click", () => {
						activeTab = entry[0];
						paint();
					});
					chips.appendChild(button);
				});
				list.replaceChildren();
				const rows = tabs[activeTab] || [];
				if (!rows.length) {
					list.appendChild(el("p", "hint", __("Nothing here yet.")));
					return;
				}
				rows.forEach((row) => {
					const card = el("div", "melliflous-card");
					const title = el("a", "who", row.name || __("Open"));
					title.href = docHref(row.doctype, row.name);
					title.addEventListener("click", (event) => {
						event.preventDefault();
						frappe.set_route("Form", row.doctype, row.name);
					});
					card.appendChild(title);
					const bits = [prettyDate(row.date), row.text || ""];
					if (row.amount != null) bits.push(moneyText(row.amount, currency));
					card.appendChild(el("div", "meta", bits.filter(Boolean).join(" · ")));
					list.appendChild(card);
				});
			}
			body.appendChild(chips);
			body.appendChild(list);
			paint();
		}

		function createTarget(data) {
			const suggestion = data.suggestion || {};
			const who = data.customer_name || data.customer;
			const question = __("Set the {0} primary target for {1} to {2}?", [
				suggestion.period_label || __("next month"),
				who,
				moneyText(suggestion.amount, data.currency),
			]);
			if (!window.confirm(question)) return;
			frappe
				.call({
					method: `${API}.create_next_target`,
					args: { customer: data.customer, company: data.company, growth_pct: growth.value },
				})
				.then((response) => {
					const saved = response.message || {};
					show(__("Target {0} set to {1}.", [saved.name || "", moneyText(saved.target_amount, data.currency)]));
				})
				.catch((error) => show(errorText(error), true));
		}

		growth.addEventListener("change", load);

		const options = frappe.route_options || {};
		if (options.company) companyControl.set_value(options.company);
		else {
			const presetCompany = frappe.defaults.get_user_default("company");
			if (presetCompany) companyControl.set_value(presetCompany);
		}
		if (options.distributor) distributorControl.set_value(options.distributor);
		if (frappe.route_options) {
			delete frappe.route_options.distributor;
			delete frappe.route_options.company;
		}
		if (!selectedDistributor()) body.appendChild(el("p", "hint", __("Pick a distributor.")));
	}

	frappe.pages["distributor-360"].on_page_load = function (wrapper) {
		try {
			const page = frappe.ui.make_app_page({
				parent: wrapper,
				title: __("Distributor 360"),
				single_column: true,
			});
			render(page, wrapper);
		} catch (error) {
			const host =
				wrapper.querySelector(".layout-main-section") ||
				wrapper.querySelector(".page-content") ||
				wrapper;
			const box = el("div", "melliflous-quick melliflous-360");
			box.appendChild(el("div", "banner is-error", errorText(error)));
			box.appendChild(el("p", "", __("The distributor could not be loaded.")));
			host.appendChild(box);
		}
	};
})();
