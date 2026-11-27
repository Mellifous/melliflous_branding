// Distributor 360. Frappe evals this file when the page opens. The body is drawn
// here, and a failed call is written into the page instead of failing silently.
(function () {
	const API = "melliflous_branding.distributor_records";
	const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
	const TABS = [
		["invoices", "Invoices"],
		["draft_invoices", "Draft invoices"],
		["credit_notes", "Credit Notes"],
		["quotations", "Quotations"],
		["sales_orders", "Sales Orders"],
		["payments", "Payments"],
		["visits", "Visits"],
		["statements", "Stock Statements"],
		["complaints", "Complaints"],
	];
	const EMPTY_BILLING = "₹0 — no submitted invoices yet";

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

	function glyph(name) {
		const paths = {
			primary:
				'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 19h16v2H4zm2-3 4-5 3 3 5-7 2 1.4-7 9.6-3-3-3 3.8z"/></svg>',
			secondary:
				'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 7h16v2H4zm0 4h10v2H4zm0 4h16v2H4z"/></svg>',
			stock:
				'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 7 12 3l9 4-9 4zm0 3.2V17l9 4 9-4v-6.8l-9 4z"/></svg>',
			billing:
				'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M6 2h9l5 5v15H6zm8 1.5V8h4.5zM8 12h8v2H8zm0 4h6v2H8z"/></svg>',
			counters:
				'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 18V6h4v12zm6 0V10h4v8zm6 0V4h4v14z"/></svg>',
			money:
				'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 3a9 9 0 1 0 .01 18.01A9 9 0 0 0 12 3m1 14v1h-2v-1c-1.7-.3-3-1.4-3-3h2c0 .6.7 1 2 1s2-.4 2-1-1-1-2.5-1.3C8.2 12.1 7 11 7 9.2 7 7.4 8.4 6.2 11 6V5h2v1c1.5.2 2.6 1.1 2.9 2.5h-2c-.2-.5-.6-.8-1.4-.8-1 0-1.5.4-1.5 1s.6.9 2.2 1.2C15.8 10.4 17 11.5 17 13.3c0 1.9-1.5 3.2-4 3.7"/></svg>',
			visit:
				'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7m0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5"/></svg>',
			quote:
				'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M6 4h9l5 5v11H6zm8 1.5V9h3.5zM8 13h8v2H8zm0 4h5v2H8z"/></svg>',
		};
		const node = el("span", "kpi-icon");
		node.innerHTML = paths[name] || "";
		return node;
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

		const toolbar = el("div", "toolbar");
		const distributorSlot = el("div");
		const companySlot = el("div");
		distributorSlot.appendChild(el("label", "", __("Distributor")));
		companySlot.appendChild(el("label", "", __("Company")));
		toolbar.appendChild(distributorSlot);
		toolbar.appendChild(companySlot);
		root.appendChild(toolbar);

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
		actions.appendChild(pill(__("New Visit"), "visit", () => openNew("Distributor Visit", { visit_date: frappe.datetime.get_today() })));
		actions.appendChild(pill(__("New Quotation"), "quote", openQuotation));
		actions.appendChild(
			pill(__("New Stock Statement"), "stock", () =>
				openNew("Distributor Stock Statement", { statement_month: frappe.datetime.month_start() })
			)
		);
		actions.appendChild(
			pill(__("New Complaint"), "complaint", () =>
				openNew("Distributor Complaint", { complaint_date: frappe.datetime.get_today() })
			)
		);
		actions.appendChild(pill(__("Create Target"), "target", () => createTarget(state)));
		root.appendChild(actions);

		const growthRow = el("div", "growth-row");
		const growthLabel = el("label", "", __("Growth % for the next target"));
		const growth = el("input", "form-control");
		growth.type = "number";
		growth.min = "-50";
		growth.max = "200";
		growth.step = "1";
		growth.value = "10";
		growthRow.appendChild(growthLabel);
		growthRow.appendChild(growth);
		root.appendChild(growthRow);

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

		function pill(label, tone, onClick) {
			const button = el("button", `pill ${tone}`, label);
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
			frappe.route_options = Object.assign(
				{ distributor: customer, company: selectedCompany() || (state && state.company) },
				values
			);
			frappe.new_doc(doctype);
		}

		function openQuotation() {
			const customer = selectedDistributor();
			if (!customer) {
				show(__("Pick a distributor first."), true);
				return;
			}
			frappe.route_options = {
				quotation_to: "Customer",
				party_name: customer,
				company: selectedCompany() || (state && state.company) || "",
			};
			frappe.new_doc("Quotation");
		}

		function draw(data) {
			body.replaceChildren();
			const currency = data.currency || "";
			const signals = data.signals || {};
			const profile = data.profile;
			body.appendChild(headerBand(data, profile));
			body.appendChild(kpiRow(data, signals, currency));
			body.appendChild(quotationPanel(data, currency));
			body.appendChild(draftPanel((data.tabs || {}).draft_invoices || [], currency));
			body.appendChild(targetCard(data, signals, currency));
			body.appendChild(el("h2", "", __("Top products")));
			body.appendChild(products(data.products || [], currency));
			body.appendChild(el("h2", "", __("Product mix")));
			body.appendChild(mix(data.mix || {}));
			body.appendChild(el("h2", "", __("Timeline")));
			body.appendChild(timeline(data.tabs || {}, currency));
			body.appendChild(el("h2", "", __("Buying pattern")));
			body.appendChild(buyingCards(data.buying || {}, currency));
			body.appendChild(el("h2", "", __("Primary and secondary")));
			body.appendChild(chart(data.chart || []));
			body.appendChild(el("h2", "", __("Records")));
			drawTabs(data.tabs || {}, currency);
			body.appendChild(legend());
		}

		function headerBand(data, profile) {
			const band = el("div", "band");
			const title = el("div", "band-title", data.customer_name || data.customer || __("Distributor"));
			band.appendChild(title);
			const people = el("div", "band-people");
			people.appendChild(person(__("Account manager"), profile && profile.account_manager));
			people.appendChild(person(__("Salesman"), (profile && (profile.sales_person || profile.salesman)) || ""));
			if (profile && (profile.area || profile.territory)) {
				people.appendChild(person(__("Area"), [profile.area, profile.territory].filter(Boolean).join(" · ")));
			}
			band.appendChild(people);
			if (profile) {
				band.appendChild(
					el(
						"span",
						`status-pill ${profile.is_active ? "is-on" : "is-off"}`,
						profile.is_active ? __("Active") : __("Inactive")
					)
				);
			}
			if (!profile) {
				band.appendChild(el("p", "band-note", __("No distributor profile yet.")));
				if (frappe.model && frappe.model.can_create && frappe.model.can_create("Distributor Profile")) {
					const create = pill(__("New Profile"), "stock", () => {
						frappe.route_options = { customer: data.customer, company: data.company };
						frappe.new_doc("Distributor Profile");
					});
					band.appendChild(create);
				}
			}
			return band;
		}

		function person(label, value) {
			const node = el("div", "person");
			node.appendChild(el("span", "person-label", label));
			node.appendChild(el("span", "person-value", value || __("Not set")));
			return node;
		}

		function kpiRow(data, signals, currency) {
			const grid = el("div", "kpi-grid");
			const quiet = signals.no_submitted_invoices;
			const primaryValue = quiet ? __(EMPTY_BILLING) : moneyText(data.primary_mtd, currency);
			const primaryCard = kpiCard(
				"primary",
				__("Primary MTD"),
				primaryValue,
				signals.primary_tone || "neutral",
				signals.achievement_pct != null ? `${signals.achievement_pct}% ${__("of target")}` : __("No target set")
			);
			if (signals.target_amount) {
				primaryCard.appendChild(progress(signals.achievement_pct, signals.primary_tone));
			}
			grid.appendChild(primaryCard);
			const secondary = signals.secondary_mtd;
			grid.appendChild(
				kpiCard(
					"secondary",
					__("Secondary MTD"),
					secondary == null ? __("No stock statement this month") : moneyText(secondary, currency),
					secondary == null ? "neutral" : "teal"
				)
			);
			grid.appendChild(stockCard(data, signals, currency));
			const last = data.last_billing;
			grid.appendChild(
				kpiCard(
					"billing",
					__("Last billing"),
					quiet || !last
						? __(EMPTY_BILLING)
						: `${prettyDate(last.posting_date)} · ${moneyText(last.amount, currency)}`,
					signals.billing_tone || "neutral",
					data.days_since_order == null ? "" : __("{0} days ago", [String(data.days_since_order)])
				)
			);
			grid.appendChild(
				kpiCard(
					"counters",
					__("Counters active"),
					data.counters == null ? __("No profile yet") : String(data.counters),
					data.counters ? "green" : "neutral"
				)
			);
			const owing = kpiCard(
				"money",
				__("Outstanding"),
				quiet ? __(EMPTY_BILLING) : moneyText(data.outstanding, currency),
				signals.overdue_tone || "green",
				Number(data.overdue_amount) > 0
					? __("Overdue {0}", [moneyText(data.overdue_amount, currency)])
					: __("Nothing overdue")
			);
			grid.appendChild(owing);
			const due = data.profile && data.profile.next_visit_due;
			grid.appendChild(
				kpiCard(
					"visit",
					__("Next visit due"),
					due ? prettyDate(due) : __("No visit scheduled"),
					signals.visit_tone || "red"
				)
			);
			const quotes = data.quotations || {};
			grid.appendChild(
				kpiCard(
					"quote",
					__("Quotations"),
					quotes.count ? moneyText(quotes.total_value, currency) : __("No quotations yet"),
					quotes.count ? "amber" : "neutral",
					quotes.count
						? __("{0} drafts · {1} submitted", [String(quotes.draft_count || 0), String(quotes.submitted_count || 0)])
						: ""
				)
			);
			return grid;
		}

		function quotationPanel(data, currency) {
			const panel = el("section", "panel");
			panel.appendChild(el("h2", "", __("Quotations")));
			const quotes = data.quotations || {};
			const pills = el("div", "qpill-row");
			(quotes.pills || []).forEach((pillRow) => {
				pills.appendChild(
					el("span", `qpill tone-${pillRow.tone || "grey"}`, `${pillRow.status} ${pillRow.count}`)
				);
			});
			if ((quotes.pills || []).length) panel.appendChild(pills);
			const rows = (data.tabs || {}).quotations || [];
			if (!rows.length) {
				panel.appendChild(el("p", "hint", __("No quotations for this customer yet.")));
				return panel;
			}
			panel.appendChild(docList(rows, currency));
			return panel;
		}

		function draftPanel(rows, currency) {
			const panel = el("section", "panel");
			panel.appendChild(el("h2", "", __("Draft invoices — not counted")));
			panel.appendChild(
				el("p", "hint", __("Drafts are not included in primary, the target, or outstanding."))
			);
			if (!rows.length) {
				panel.appendChild(el("p", "hint", __("No draft invoices.")));
				return panel;
			}
			panel.appendChild(docList(rows, currency));
			return panel;
		}

		function docList(rows, currency) {
			const list = el("div");
			rows.forEach((row) => {
				const card = el("div", "melliflous-card");
				const title = el("a", "who", row.name || __("Open"));
				title.href = docHref(row.doctype, row.name);
				title.addEventListener("click", (event) => {
					event.preventDefault();
					frappe.set_route("Form", row.doctype, row.name);
				});
				card.appendChild(title);
				if (row.status) {
					card.appendChild(el("span", `qpill tone-${row.tone || "grey"}`, row.status));
				}
				const bits = [prettyDate(row.date), row.text || ""];
				if (row.amount != null) bits.push(moneyText(row.amount, currency));
				card.appendChild(el("div", "meta", bits.filter(Boolean).join(" · ")));
				list.appendChild(card);
			});
			return list;
		}

		function stockCard(data, signals, currency) {
			let value = __("No stock statement yet");
			let detail = "";
			if (data.closing_qty != null) {
				const cover = signals.cover_days;
				const coverText =
					cover == null ? "" : cover >= 999 ? __("Not moving") : __("{0} days of cover", [String(cover)]);
				value = `${Number(data.closing_qty)} · ${moneyText(data.closing_value, currency)}`;
				detail = coverText;
			}
			return kpiCard("stock", __("Stock on hand"), value, signals.cover_tone || "neutral", detail);
		}

		function kpiCard(iconName, label, value, tone, detail) {
			const card = el("div", `kpi tone-${tone || "neutral"}`);
			const head = el("div", "kpi-head");
			head.appendChild(glyph(iconName));
			head.appendChild(el("div", "label", label));
			card.appendChild(head);
			card.appendChild(el("div", "value", value));
			if (detail) card.appendChild(el("div", "detail", detail));
			return card;
		}

		function progress(pct, tone) {
			const wrap = el("div", "progress");
			const bar = el("span", `progress-bar tone-${tone || "neutral"}`);
			const width = Math.max(0, Math.min(100, Number(pct) || 0));
			bar.style.width = `${width}%`;
			wrap.appendChild(bar);
			return wrap;
		}

		function targetCard(data, signals, currency) {
			const card = el("section", "panel");
			card.appendChild(el("h2", "", __("Target and recent primary")));
			const suggestion = data.suggestion || {};
			const quiet = signals.no_submitted_invoices;
			if (quiet) {
				card.appendChild(el("p", "", __(EMPTY_BILLING)));
			}
			if (signals.target_amount) {
				card.appendChild(
					el(
						"p",
						"",
						__("{0} of {1} this month ({2}%).", [
							moneyText(data.primary_mtd, currency),
							moneyText(signals.target_amount, currency),
							String(signals.achievement_pct),
						])
					)
				);
				card.appendChild(progress(signals.achievement_pct, signals.primary_tone));
			} else if (!quiet) {
				card.appendChild(el("p", "hint", __("No target is set for this month.")));
			}
			card.appendChild(sparkline((data.chart || []).slice(-6)));
			const monthBits = (suggestion.months || [])
				.filter((row) => row.label)
				.map((row) => `${row.label} ${moneyText(row.primary, currency)}`);
			card.appendChild(
				el(
					"p",
					"",
					__("{0}: average primary {1} at {2}% growth is {3}.", [
						suggestion.period_label || __("Next month"),
						moneyText(suggestion.average, currency),
						String(suggestion.growth_pct ?? growth.value),
						quiet ? __(EMPTY_BILLING) : moneyText(suggestion.amount, currency),
					])
				)
			);
			if (monthBits.length) card.appendChild(el("p", "hint", monthBits.join(" · ")));
			if (!(Number(suggestion.amount) > 0)) {
				card.appendChild(el("p", "hint", __("There is no primary billing in the last three months to base a target on.")));
			}
			return card;
		}

		function sparkline(rows) {
			const wrap = el("div", "spark");
			if (!rows.length) {
				wrap.appendChild(el("p", "hint", __("No billing in the last 12 months.")));
				return wrap;
			}
			const max = Math.max(1, ...rows.map((row) => Math.abs(Number(row.primary) || 0)));
			rows.forEach((row) => {
				const column = el("div", "spark-col");
				const bar = el("span", "spark-bar");
				const height = Math.max(4, (Math.abs(Number(row.primary) || 0) / max) * 100);
				bar.style.height = `${height}%`;
				column.appendChild(bar);
				column.appendChild(el("span", "spark-label", row.label || ""));
				wrap.appendChild(column);
			});
			return wrap;
		}

		function products(rows, currency) {
			if (!rows.length) return el("p", "hint", __("No product sales in the last 12 months."));
			const table = el("table");
			const head = el("tr");
			[__("Item"), __("Qty"), __("Amount"), __("Share"), __("Pace")].forEach((label) =>
				head.appendChild(el("th", "", label))
			);
			table.appendChild(head);
			rows.forEach((row) => {
				const line = el("tr");
				line.appendChild(el("td", "", row.item_name || row.item || ""));
				line.appendChild(el("td", "", String(row.qty ?? "")));
				line.appendChild(el("td", "", moneyText(row.amount, currency)));
				line.appendChild(el("td", "", `${row.share}%`));
				const pace = el("td");
				pace.appendChild(el("span", `badge pace-${row.pace || "no-movement"}`, paceLabel(row.pace)));
				line.appendChild(pace);
				table.appendChild(line);
			});
			const wrap = el("div", "table-wrap");
			wrap.appendChild(table);
			return wrap;
		}

		function paceLabel(pace) {
			if (pace === "fast") return __("Fast");
			if (pace === "slow") return __("Slow");
			return __("No movement");
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

		function timeline(tabs, currency) {
			const kinds = [
				["invoices", "invoice", __("Invoice")],
				["draft_invoices", "draft", __("Draft invoice")],
				["credit_notes", "credit", __("Credit note")],
				["quotations", "quotation", __("Quotation")],
				["sales_orders", "order", __("Sales order")],
				["payments", "payment", __("Payment")],
				["visits", "visit", __("Visit")],
				["complaints", "complaint", __("Complaint")],
			];
			const rows = [];
			kinds.forEach((kind) => {
				(tabs[kind[0]] || []).forEach((row) => {
					rows.push({ kind: kind[1], kindLabel: kind[2], row: row });
				});
			});
			rows.sort((left, right) => String(right.row.date || "").localeCompare(String(left.row.date || "")));
			const list = el("div", "timeline");
			if (!rows.length) {
				list.appendChild(el("p", "hint", __("No visits, invoices, or complaints yet.")));
				return list;
			}
			rows.slice(0, 18).forEach((entry) => {
				const item = el("div", `event kind-${entry.kind}`);
				item.appendChild(el("span", "event-mark", entry.kindLabel.slice(0, 1)));
				const copy = el("div");
				const title = el("a", "who", entry.row.name || entry.kindLabel);
				title.href = docHref(entry.row.doctype, entry.row.name);
				title.addEventListener("click", (event) => {
					event.preventDefault();
					frappe.set_route("Form", entry.row.doctype, entry.row.name);
				});
				copy.appendChild(title);
				const bits = [entry.kindLabel, prettyDate(entry.row.date), entry.row.text || ""];
				if (entry.row.amount != null) bits.push(moneyText(entry.row.amount, currency));
				copy.appendChild(el("div", "meta", bits.filter(Boolean).join(" · ")));
				item.appendChild(copy);
				list.appendChild(item);
			});
			return list;
		}

		function buyingCards(buying, currency) {
			const grid = el("div", "kpi-grid");
			grid.appendChild(kpiCard("primary", __("Orders, 12 months"), String(buying.order_count || 0), buying.order_count ? "green" : "neutral"));
			grid.appendChild(
				kpiCard(
					"billing",
					__("Average order value"),
					buying.order_count ? moneyText(buying.average_order_value, currency) : __(EMPTY_BILLING),
					"neutral"
				)
			);
			grid.appendChild(
				kpiCard(
					"visit",
					__("Average days between orders"),
					buying.average_days_between == null ? "—" : String(buying.average_days_between),
					"neutral"
				)
			);
			grid.appendChild(kpiCard("secondary", __("Orders per month"), String(buying.orders_per_month || 0), "teal"));
			return grid;
		}

		function chart(rows) {
			const wrap = el("div", "chart");
			const legendRow = el("div", "legend");
			legendRow.appendChild(swatch("primary", __("Primary")));
			legendRow.appendChild(swatch("secondary", __("Secondary")));
			wrap.appendChild(legendRow);
			const values = [];
			rows.forEach((row) => {
				values.push(Math.abs(Number(row.primary) || 0));
				if (row.secondary != null) values.push(Math.abs(Number(row.secondary) || 0));
			});
			const max = Math.max(1, ...values);
			const anyPrimary = rows.some((row) => Number(row.primary));
			if (!rows.length || !anyPrimary) {
				wrap.appendChild(el("p", "hint", __(EMPTY_BILLING)));
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
			return el("span", `swatch ${kind}`, label);
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
					const empty =
						entryEmpty(activeTab) || __("Nothing here yet.");
					list.appendChild(el("p", "hint", empty));
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

		function entryEmpty(tab) {
			if (tab === "invoices" || tab === "credit_notes") return __(EMPTY_BILLING);
			if (tab === "visits") return __("No visits yet.");
			if (tab === "statements") return __("No stock statement yet.");
			if (tab === "complaints") return __("No complaints. That is a good month.");
			if (tab === "payments") return __("No payments recorded yet.");
			if (tab === "quotations") return __("No quotations for this customer yet.");
			if (tab === "sales_orders") return __("No sales orders for this customer yet.");
			if (tab === "draft_invoices") return __("No draft invoices.");
			return "";
		}

		function legend() {
			const box = el("section", "legend-box");
			box.appendChild(el("h2", "", __("Colour key")));
			const items = [
				["green", __("On track: target at 100% or more, stock cover 7–30 days, billed within 7 days, visit still ahead.")],
				["amber", __("Watch: target 70–99%, cover under 7 or 30–45 days, last bill 8–15 days ago, visit due today.")],
				["red", __("Act: target under 70%, cover at 0 or over 45 days, no bill for 16 days, visit overdue, or money overdue.")],
				["fast", __("Fast: recent product sales are holding or growing.")],
				["slow", __("Slow: recent product sales have fallen.")],
				["still", __("No movement: nothing sold in the last three months.")],
			];
			items.forEach((item) => {
				const row = el("div", "legend-row");
				row.appendChild(el("span", `legend-dot tone-${item[0]}`));
				row.appendChild(el("span", "", item[1]));
				box.appendChild(row);
			});
			box.appendChild(
				el(
					"p",
					"hint",
					__(
						"Timeline: visits blue, invoices green, draft invoices grey, credit notes purple, quotations amber, sales orders teal, payments green, complaints red."
					)
				)
			);
			return box;
		}

		function createTarget(data) {
			if (!data || !data.customer) {
				show(__("Pick a distributor first."), true);
				return;
			}
			const suggestion = data.suggestion || {};
			if (!(Number(suggestion.amount) > 0)) {
				show(__("There is no primary billing in the last three months to base a target on."), true);
				return;
			}
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
