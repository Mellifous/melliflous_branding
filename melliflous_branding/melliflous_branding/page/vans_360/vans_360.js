// Vans 360. The numbers still come from vans_dashboard. This file only draws them.
frappe.pages["vans-360"] = frappe.pages["vans-360"] || {};
frappe.pages["vans-360"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Vans 360"), single_column: true });
	wrapper.classList.add("vans-360-page");
	placeVanMark(wrapper);
	ensureStyle();
	const boot = (frappe.boot && frappe.boot.melliflous_branding) || {};
	const state = {
		company: boot.company || "",
		division: boot.division || "",
		kind: "month",
		anchor: todayISO(),
	};
	const root = document.createElement("div");
	root.className = "vans-360";
	page.main.append(root);
	root.innerHTML =
		'<div class="vans-actions">' +
		'<button type="button" class="vans-btn vans-btn-solid" data-act="report">+ Daily Report</button>' +
		'<button type="button" class="vans-btn vans-btn-solid" data-act="cash">+ Cash Transfer</button>' +
		'<button type="button" class="vans-btn" data-act="excel">Excel</button>' +
		'<button type="button" class="vans-btn" data-act="pdf">PDF</button>' +
		'<a class="vans-text-link" href="/desk/melliflous-branding/van">Van list</a>' +
		"</div>" +
		'<div class="vans-toolbar">' +
		'<button type="button" class="vans-filter-toggle" aria-expanded="false">Filters</button>' +
		'<div class="vans-period" role="group" aria-label="' + esc(__("Period")) + '">' +
		'<button type="button" data-preset="Today">Today</button>' +
		'<button type="button" data-preset="Week">Week</button>' +
		'<button type="button" data-preset="MTD" class="is-on">Month</button>' +
		"</div></div>" +
		'<div class="vans-filter-panel" hidden>' +
		'<div class="vans-company"></div><div class="vans-division"></div>' +
		"</div>" +
		'<div class="vans-range">' +
		'<div class="vans-kind" role="group" aria-label="' + esc(__("Range")) + '">' +
		'<button type="button" data-kind="day">Day</button>' +
		'<button type="button" data-kind="week">Week</button>' +
		'<button type="button" data-kind="month" class="is-on">Month</button>' +
		"</div>" +
		'<div class="vans-picker">' +
		'<button type="button" class="vans-step" data-step="-1" aria-label="' + esc(__("Previous")) + '">‹</button>' +
		'<input class="vans-date" type="date" aria-label="' + esc(__("Date")) + '">' +
		'<input class="vans-month" type="month" aria-label="' + esc(__("Month")) + '" hidden>' +
		'<button type="button" class="vans-step" data-step="1" aria-label="' + esc(__("Next")) + '">›</button>' +
		"</div>" +
		'<p class="vans-range-label"></p>' +
		"</div>" +
		'<div class="vans-results"></div>';

	const results = root.querySelector(".vans-results");
	const companyControl = frappe.ui.form.make_control({
		parent: root.querySelector(".vans-company"),
		df: {
			fieldname: "company",
			fieldtype: "Link",
			options: "Company",
			label: __("Company"),
			default: state.company,
			change: onCompany,
			onchange: onCompany,
		},
		render_input: true,
	});
	const divisionControl = frappe.ui.form.make_control({
		parent: root.querySelector(".vans-division"),
		df: {
			fieldname: "division",
			fieldtype: "Link",
			options: "Division",
			label: __("Division"),
			default: state.division,
			change: onDivision,
			onchange: onDivision,
		},
		render_input: true,
	});
	if (state.company) companyControl.set_value(state.company);
	if (state.division) divisionControl.set_value(state.division);

	function onCompany() {
		const next = companyControl.get_value() || "";
		if (next === state.company) return;
		state.company = next;
		load();
	}

	function onDivision() {
		const next = divisionControl.get_value() || "";
		if (next === state.division) return;
		state.division = next;
		load();
	}

	root.addEventListener("click", (event) => {
		const act = event.target.closest("[data-act]");
		if (act && root.contains(act)) {
			if (act.dataset.act === "report") frappe.new_doc("Van Daily Report");
			else if (act.dataset.act === "cash") frappe.new_doc("Cash Transfer");
			else if (act.dataset.act === "excel") download("csv");
			else if (act.dataset.act === "pdf") download("html");
			return;
		}
		const preset = event.target.closest("[data-preset]");
		if (preset && root.contains(preset)) {
			state.anchor = todayISO();
			state.kind = preset.dataset.preset === "Today" ? "day" : preset.dataset.preset === "Week" ? "week" : "month";
			syncPicker();
			load();
			return;
		}
		const kind = event.target.closest("[data-kind]");
		if (kind && root.contains(kind)) {
			state.kind = kind.dataset.kind;
			syncPicker();
			load();
			return;
		}
		const step = event.target.closest("[data-step]");
		if (step && root.contains(step)) {
			state.anchor = shiftAnchor(state.anchor, state.kind, Number(step.dataset.step));
			syncPicker();
			load();
			return;
		}
		const drill = event.target.closest("[data-list], [data-doc]");
		if (drill && root.contains(drill)) {
			openDrill(drill);
			return;
		}
		const filters = event.target.closest(".vans-filter-toggle");
		if (filters && root.contains(filters)) {
			const panel = root.querySelector(".vans-filter-panel");
			const open = panel.hasAttribute("hidden");
			if (open) panel.removeAttribute("hidden");
			else panel.setAttribute("hidden", "");
			filters.setAttribute("aria-expanded", open ? "true" : "false");
			return;
		}
		const toggle = event.target.closest(".vans-section-toggle");
		if (!toggle || !results.contains(toggle)) return;
		const section = toggle.closest(".vans-section");
		const open = section.classList.toggle("is-open");
		toggle.setAttribute("aria-expanded", open ? "true" : "false");
	});

	const dateInput = root.querySelector(".vans-date");
	const monthInput = root.querySelector(".vans-month");
	dateInput.addEventListener("change", () => {
		if (!dateInput.value) return;
		state.anchor = dateInput.value;
		syncPicker();
		load();
	});
	monthInput.addEventListener("change", () => {
		if (!monthInput.value) return;
		state.anchor = monthInput.value + "-01";
		syncPicker();
		load();
	});

	function load() {
		const bounds = boundsFor(state.kind, state.anchor);
		state.start = bounds.start;
		state.end = bounds.end;
		results.innerHTML = '<p class="vans-empty">' + esc(__("Loading…")) + "</p>";
		frappe.call({
			method: "melliflous_branding.van_records.vans_dashboard",
			args: {
				company: state.company,
				division: state.division,
				preset: "Custom",
				start: state.start,
				end: state.end,
			},
			callback(response) {
				draw(results, (response && response.message) || {}, state);
			},
			error() {
				results.innerHTML = '<p class="vans-empty">' + esc(__("Could not load Vans 360.")) + "</p>";
			},
		});
	}

	function download(fileFormat) {
		frappe.call({
			method: "melliflous_branding.van_records.van_report_download",
			args: {
				kind: "Detailed sales",
				company: state.company,
				division: state.division,
				preset: "Custom",
				start: state.start,
				end: state.end,
				file_format: fileFormat,
			},
			callback(response) {
				const file = (response && response.message) || {};
				if (fileFormat === "html") {
					const popup = window.open("", "_blank");
					if (popup) popup.document.write(file.body || "");
					return;
				}
				const blob = new Blob([file.body || ""], { type: "text/csv" });
				const link = document.createElement("a");
				link.href = URL.createObjectURL(blob);
				link.download = file.filename || "vans.csv";
				link.click();
			},
		});
	}

	function syncPicker() {
		const today = todayISO();
		const bounds = boundsFor(state.kind, state.anchor);
		state.start = bounds.start;
		state.end = bounds.end;
		root.querySelectorAll("[data-kind]").forEach((button) => {
			button.classList.toggle("is-on", button.dataset.kind === state.kind);
		});
		root.querySelectorAll("[data-preset]").forEach((button) => {
			const preset = button.dataset.preset;
			const on =
				preset === "Today"
					? state.kind === "day" && state.anchor === today
					: preset === "Week"
						? state.kind === "week" && bounds.start <= today && today <= bounds.end
						: state.kind === "month" && state.anchor.slice(0, 7) === today.slice(0, 7);
			button.classList.toggle("is-on", on);
		});
		dateInput.hidden = state.kind === "month";
		monthInput.hidden = state.kind !== "month";
		dateInput.value = state.anchor;
		monthInput.value = state.anchor.slice(0, 7);
		root.querySelector(".vans-range-label").textContent = rangeLabel(state.kind, bounds.start, bounds.end);
	}

	syncPicker();
	load();
};

function ensureStyle() {
	if (document.getElementById("vans-360-style")) return;
	const style = document.createElement("style");
	style.id = "vans-360-style";
	style.textContent = VANS_CSS;
	document.head.appendChild(style);
}

function placeVanMark(wrapper) {
	const title = wrapper.querySelector(".page-title .title-text, .title-text");
	if (!title || title.querySelector(".vans-360-mark")) return;
	const mark = document.createElement("span");
	mark.className = "vans-360-mark";
	mark.setAttribute("aria-hidden", "true");
	mark.innerHTML = icon("M3 7h11v8H3V7zm11 2h4l3 3v3h-7V9zM6.5 18a1.5 1.5 0 1 0 .01-3A1.5 1.5 0 0 0 6.5 18zm10 0a1.5 1.5 0 1 0 .01-3A1.5 1.5 0 0 0 16.5 18z");
	title.prepend(mark);
}

function draw(host, data, scope) {
	const overview = data.overview || {};
	const vans = data.vans || [];
	const live = vans.filter((row) => String(row.status || "") === "Live");
	const fleet = (live.length || vans.length || 0);
	const out = Number(overview.vans_worked != null ? overview.vans_worked : overview.vans_logged_today) || 0;
	const span = scope || {};
	const percent = Number(overview.percent) || 0;
	const missed = Number(overview.missed_van_days) || 0;
	const mismatches = Number(overview.mismatches) || 0;
	const strike = Number(overview.strike) || 0;
	const outlets = Number(overview.new_outlets) || 0;
	const salesTone = !overview.target ? "" : percent >= 100 ? "is-good" : "is-warn";
	const cards = [
		kpi("Daily Run Rate", overview.run_rate == null ? "—" : rupee(overview.run_rate, true), "M4 16a8 8 0 0 1 16 0", "", listAttrs(span, "Van Daily Report", "date")),
		kpi("Vans Out", fleet ? out + " of " + fleet : String(out), "M3 7h11v8H3V7zm11 2h4l3 3v3h-7V9z", out && fleet && out >= fleet ? "is-good" : "", listAttrs(span, "Van Daily Report", "date") + ' data-worked-flag="1"'),
		kpi("Strike Rate", pct(strike), "M5 13l4 4 10-10", strike >= 60 ? "is-good" : strike ? "is-warn" : "", listAttrs(span, "Van Daily Report", "date")),
		kpi("Missed Van Days", String(missed), "M8 4v3M16 4v3M5 9h14v10H5zM9 13l6 4", missed > 0 ? "is-bad" : "is-good", listAttrs(span, "Van Daily Report", "date")),
		kpi("Mismatches", String(mismatches), "M12 4l8 14H4zM12 10v4M12 16h.01", mismatches > 0 ? "is-bad" : "is-good", listAttrs(span, "Van Daily Report", "date") + ' data-mismatch="1"'),
		kpi("New Outlets", String(outlets), "M12 8v8M8 12h8", outlets > 0 ? "is-good" : "", listAttrs(span, "Van Daily Report", "date") + ' data-outlets="1"'),
	].join("");
	const bar = Math.max(0, Math.min(percent, 100));
	host.innerHTML =
		'<button type="button" class="vans-kpi vans-kpi-wide vans-tap ' + salesTone + '"' + listAttrs(span, "Van Daily Report", "date") + ">" +
		'<span class="vans-kpi-label">' + icon("M4 16l5-5 4 4 7-8") + "<span>Sales vs Target</span></span>" +
		'<span class="vans-kpi-value">' + esc(rupee(overview.sales, true)) + "</span>" +
		'<span class="vans-kpi-note">Target ' + esc(rupee(overview.target, true)) + " · " + esc(pct(percent)) + "</span>" +
		'<span class="vans-bar" role="progressbar" aria-valuenow="' + esc(String(Math.round(percent))) + '" aria-valuemin="0" aria-valuemax="100"><span style="width:' + bar + '%"></span></span>' +
		"</button>" +
		'<div class="vans-kpis">' + cards + "</div>" +
		sectionBlock("Leaderboard", "M4 18V6M10 18V10M16 18V4M22 18H2", true, data.leaderboard, [
			{ label: "Salesperson", text: (row) => row.worked_by || "—" },
			{ label: "Sales", text: (row) => rupee(row.sales, true) },
			{ label: "Target", text: (row) => rupee(row.target, true) },
			{ label: "Days Worked", text: (row) => String(row.days ?? 0) },
		], (row) => listAttrs(span, "Van Daily Report", "date") + attr("data-worked", row.worked_by)) +
		sectionBlock("Cash", "M3 10h18v8H3zM5 6h14l2 4H3z", true, null, null, cashBody(data.cash || {}, span)) +
		sectionBlock("Exceptions", "M12 9v4M12 17h.01", false, data.exceptions, [
			{ label: "Van", text: (row) => row.van || "—" },
			{ label: "Issue", text: (row) => issueLabel(row.kind) },
			{ label: "Date", text: (row) => prettyDate(row.date) },
		], (row) => listAttrs(Object.assign({}, span, row.date ? { start: String(row.date).slice(0, 10), end: String(row.date).slice(0, 10) } : {}), "Van Daily Report", "date") + attr("data-van", row.van)) +
		sectionBlock("Beats", "M4 8h16v10H4z", false, data.beats, [
			{ label: "Beat", text: (row) => row.beat || "—" },
			{ label: "Van", text: (row) => row.van || "—" },
			{ label: "Last Visited", text: (row) => prettyDate(row.last_worked) },
			{ label: "Overdue", text: (row) => (Number(row.overdue) ? "Overdue" : "On time") },
		], (row) => (row.beat_id || row.beat ? attr("data-doc", "Van Beat") + attr("data-name", row.beat_id || row.beat) : attr("data-doc", "Van") + attr("data-name", row.van))) +
		sectionBlock("Reported vs invoiced", "M6 4h12v16H6z", false, data.reported_vs_invoiced, [
			{ label: "Date", text: (row) => prettyDate(row.date) },
			{ label: "Van", text: (row) => row.van || "—" },
			{ label: "Reported", text: (row) => rupee(row.reported, true) },
			{ label: "Invoiced", text: (row) => rupee(row.invoiced, true) },
			{ label: "Unbilled", text: (row) => (Number(row.unbilled) ? "Unbilled" : "Billed") },
		], (row) => listAttrs({ company: span.company, start: String(row.date || "").slice(0, 10), end: String(row.date || "").slice(0, 10) }, "Sales Invoice", "posting_date") + attr("data-custom-van", row.van));
}

function kpi(label, value, path, tone, attrs) {
	return (
		'<button type="button" class="vans-kpi vans-tap ' + tone + '"' + (attrs || "") + '><span class="vans-kpi-label">' +
		icon(path) +
		"<span>" + esc(label) + '</span></span><span class="vans-kpi-value">' +
		esc(value) +
		"</span></button>"
	);
}

function sectionBlock(title, path, open, rows, fields, bodyOrOpen) {
	const html = typeof bodyOrOpen === "string" ? bodyOrOpen : null;
	const openAttrs = typeof bodyOrOpen === "function" ? bodyOrOpen : null;
	const list = rows || [];
	const count = html != null ? cashCount(html) : list.length;
	const body = html != null ? html : list.length ? items(list, fields, openAttrs) : emptyLine();
	return (
		'<section class="vans-section' + (open ? " is-open" : "") + '">' +
		'<button type="button" class="vans-section-toggle" aria-expanded="' + (open ? "true" : "false") + '">' +
		icon(path) +
		'<span class="vans-section-name">' + esc(title) + '</span><span class="vans-count">' + esc(String(count)) + "</span></button>" +
		'<div class="vans-section-body">' + body + "</div></section>"
	);
}

function cashBody(cash, span) {
	const balances = cash.balances || [];
	const transfers = cash.transfers || [];
	if (!balances.length && !transfers.length) return emptyLine();
	return (
		"<h3>In hand</h3>" +
		(balances.length
			? items(balances, [
				{ label: "Holder", text: (row) => row.holder || "—" },
				{ label: "Cash in Hand", text: (row) => rupee(row.balance, true) },
			], () => listAttrs(span, "Cash Transfer", "posting_date"))
			: emptyLine()) +
		"<h3>Transfers</h3>" +
		(transfers.length
			? items(transfers, [
				{ label: "Date", text: (row) => prettyDate(row.posting_date) },
				{ label: "From", text: (row) => row.from_holder || "—" },
				{ label: "To", text: (row) => row.to_holder || row.to_bank || "—" },
				{ label: "Amount", text: (row) => rupee(row.amount, true) },
			], (row) => attr("data-doc", "Cash Transfer") + attr("data-name", row.name))
			: emptyLine())
	);
}

function cashCount(html) {
	return (html.match(/class="vans-item"/g) || []).length;
}

function items(rows, fields, openAttrs) {
	return rows
		.slice(0, 40)
		.map((row) => {
			const title = fields[0];
			const rest = fields
				.slice(1)
				.map((field) => "<div><dt>" + esc(field.label) + "</dt><dd>" + esc(field.text(row)) + "</dd></div>")
				.join("");
			const attrs = openAttrs ? openAttrs(row) : "";
			return '<button type="button" class="vans-item vans-tap"' + attrs + '><span class="vans-item-title">' + esc(title.text(row)) + "</span><dl>" + rest + "</dl></button>";
		})
		.join("");
}

function emptyLine() {
	return '<p class="vans-empty">' + icon("M12 8v4M12 16h.01M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z") + "<span>No reports yet for this period</span></p>";
}

function issueLabel(kind) {
	const names = {
		absent: "SR absent",
		"0%": "No sales",
		"<70% target": "Under 70% of target",
		mismatch: "Cash mismatch",
		idle: "Van idle",
		"frequent absence": "Often absent",
		"low strike": "Low strike rate",
	};
	return names[kind] || kind || "—";
}

function icon(path) {
	return '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="' + path + '"/></svg>';
}

function rupee(value, short) {
	const number = Number(value);
	if (!Number.isFinite(number)) return "—";
	const sign = number < 0 ? "-" : "";
	const abs = Math.abs(number);
	if (short && abs >= 10000000) return sign + "₹" + trimNumber(abs / 10000000) + " Cr";
	if (short && abs >= 100000) return sign + "₹" + trimNumber(abs / 100000) + " L";
	return sign + "₹" + indianGroup(Math.round(abs));
}

function trimNumber(value) {
	return (Math.round(value * 100) / 100).toFixed(2).replace(/\.00$/, "").replace(/(\.\d)0$/, "$1");
}

function indianGroup(whole) {
	const text = String(whole);
	if (text.length <= 3) return text;
	const head = text.slice(0, -3);
	const tail = text.slice(-3);
	return head.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," + tail;
}

function pct(value) {
	const number = Number(value);
	if (!Number.isFinite(number)) return "—";
	const rounded = Math.round(number * 10) / 10;
	return (rounded % 1 ? String(rounded) : String(rounded.toFixed(0))) + "%";
}

function prettyDate(value) {
	const text = String(value || "").slice(0, 10);
	const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
	if (!match) return value ? String(value) : "—";
	const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
	return String(Number(match[3])) + " " + months[Number(match[2]) - 1];
}

function todayISO() {
	const now = new Date();
	return isoDate(new Date(now.getFullYear(), now.getMonth(), now.getDate()));
}

function isoDate(day) {
	const month = String(day.getMonth() + 1).padStart(2, "0");
	const date = String(day.getDate()).padStart(2, "0");
	return day.getFullYear() + "-" + month + "-" + date;
}

function parseISO(value) {
	const parts = String(value || "").slice(0, 10).split("-");
	return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
}

function boundsFor(kind, anchor) {
	const day = parseISO(anchor);
	if (kind === "day") {
		const text = isoDate(day);
		return { start: text, end: text };
	}
	if (kind === "week") {
		const monday = new Date(day.getFullYear(), day.getMonth(), day.getDate() - ((day.getDay() + 6) % 7));
		const sunday = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + 6);
		return { start: isoDate(monday), end: isoDate(sunday) };
	}
	const start = new Date(day.getFullYear(), day.getMonth(), 1);
	const end = new Date(day.getFullYear(), day.getMonth() + 1, 0);
	return { start: isoDate(start), end: isoDate(end) };
}

function shiftAnchor(anchor, kind, step) {
	const day = parseISO(anchor);
	if (kind === "day") day.setDate(day.getDate() + step);
	else if (kind === "week") day.setDate(day.getDate() + step * 7);
	else day.setMonth(day.getMonth() + step);
	return isoDate(day);
}

function rangeLabel(kind, start, end) {
	if (kind === "day") return prettyFull(start);
	if (kind === "month") {
		const day = parseISO(start);
		const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
		return months[day.getMonth()] + " " + day.getFullYear();
	}
	const from = parseISO(start);
	const to = parseISO(end);
	const short = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
	if (from.getMonth() === to.getMonth() && from.getFullYear() === to.getFullYear()) {
		return from.getDate() + "-" + to.getDate() + " " + short[from.getMonth()] + " " + from.getFullYear();
	}
	return prettyFull(start) + " – " + prettyFull(end);
}

function prettyFull(value) {
	const day = parseISO(value);
	const short = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
	return day.getDate() + " " + short[day.getMonth()] + " " + day.getFullYear();
}

function attr(name, value) {
	if (value == null || value === "") return "";
	return " " + name + '="' + esc(value) + '"';
}

function listAttrs(span, doctype, dateField) {
	return (
		attr("data-list", doctype) +
		attr("data-datefield", dateField) +
		attr("data-from", span && span.start) +
		attr("data-to", span && span.end) +
		attr("data-company", span && span.company) +
		attr("data-division", span && span.division)
	);
}

function openDrill(node) {
	if (!window.frappe || !frappe.set_route) return;
	const doc = node.dataset.doc;
	const name = node.dataset.name;
	if (doc && name) {
		frappe.set_route("Form", doc, name);
		return;
	}
	const list = node.dataset.list;
	if (!list) return;
	const filters = {};
	if (node.dataset.company) filters.company = node.dataset.company;
	if (node.dataset.division) filters.division = node.dataset.division;
	if (node.dataset.van) filters.van = node.dataset.van;
	if (node.dataset.customVan) filters.custom_van = node.dataset.customVan;
	if (node.dataset.worked) filters.worked_by = node.dataset.worked;
	const from = node.dataset.from;
	const to = node.dataset.to;
	const dateField = node.dataset.datefield || "date";
	if (from && to) filters[dateField] = ["Between", [from, to]];
	if (node.dataset.workedFlag) filters.worked = ["!=", "No"];
	if (node.dataset.mismatch) filters.mismatch = [">", 0];
	if (node.dataset.outlets) filters.new_outlets = [">", 0];
	frappe.route_options = filters;
	frappe.set_route("List", list);
}

function esc(value) {
	const text = String(value == null ? "" : value);
	if (typeof window !== "undefined" && window.frappe && frappe.utils && frappe.utils.escape_html) return frappe.utils.escape_html(text);
	return text.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
}

const VANS_CSS = `
.vans-360-page .page-head {
	position: relative !important;
	top: auto !important;
	height: auto !important;
	z-index: 2;
	background: #f8f8f8 !important;
	border-bottom: 1px solid #e7e5e4;
}
.vans-360-page .page-title,
.vans-360-page .title-area,
.vans-360-page .title-text {
	display: flex;
	align-items: center;
	min-height: 0;
	overflow: visible;
}
.vans-360-mark { display: inline-flex; width: 22px; height: 22px; margin-right: 8px; color: #44403c; flex: 0 0 auto; }
.vans-360-mark svg { width: 22px; height: 22px; }
.vans-360-page .layout-main-section { margin-top: 0 !important; background: transparent; border: 0; box-shadow: none; }
.vans-360 { padding: 12px 12px 80px; color: #1c1917; max-width: 1080px; }
.vans-actions, .vans-toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.vans-actions .vans-btn { flex: 1 1 calc(50% - 8px); }
.vans-actions { margin-bottom: 12px; }
.vans-btn, .vans-filter-toggle {
	min-height: 44px;
	padding: 0 14px;
	border-radius: 12px;
	border: 1px solid #d6d3d1;
	background: #fff;
	color: #1c1917;
	font-weight: 700;
	font-size: 14px;
	cursor: pointer;
}
.vans-btn:hover, .vans-filter-toggle:hover, .vans-step:hover { border-color: #a8a29e; }
.vans-btn:active, .vans-filter-toggle:active, .vans-step:active { background: #f5f5f4; }
.vans-btn-solid { background: #1c1917; color: #fff; border-color: #1c1917; }
.vans-text-link { color: #44403c; font-size: 13px; font-weight: 600; margin-left: auto; }
.vans-toolbar { margin-bottom: 10px; }
.vans-period { display: flex; flex: 1 1 220px; padding: 3px; border-radius: 999px; background: #efefef; }
.vans-period button, .vans-kind button {
	flex: 1;
	min-height: 44px;
	border: 0;
	border-radius: 999px;
	background: transparent;
	color: #44403c;
	font-weight: 700;
	cursor: pointer;
}
.vans-period button.is-on, .vans-kind button.is-on { background: #fff; color: #1c1917; box-shadow: 0 1px 2px rgba(28, 25, 23, 0.08); }
.vans-range { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 0 0 8px; }
.vans-kind { display: flex; flex: 1 1 220px; padding: 3px; border-radius: 999px; background: #efefef; }
.vans-picker { display: flex; flex: 1 1 220px; align-items: center; gap: 8px; }
.vans-step, .vans-date, .vans-month {
	min-height: 44px;
	border: 1px solid #d6d3d1;
	border-radius: 12px;
	background: #fff;
	color: #1c1917;
	font-size: 16px;
}
.vans-step { width: 44px; font-size: 22px; cursor: pointer; }
.vans-date, .vans-month { flex: 1; padding: 0 10px; }
.vans-range-label { flex: 1 1 100%; margin: 0; font-weight: 800; color: #1c1917; }
.vans-filter-panel { display: grid; gap: 8px; margin: 0 0 12px; }
.vans-filter-panel[hidden] { display: none !important; }
.vans-kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
.vans-kpi, .vans-section {
	background: #fff;
	border: 1px solid #e7e5e4;
	border-radius: 16px;
	box-shadow: 0 1px 2px rgba(28, 25, 23, 0.05), 0 8px 20px rgba(28, 25, 23, 0.04);
}
.vans-kpi { display: flex; flex-direction: column; align-items: stretch; width: 100%; min-height: 44px; padding: 12px; min-width: 0; text-align: left; font: inherit; color: inherit; cursor: pointer; }
.vans-kpi:hover, .vans-item:hover { border-color: #a8a29e; }
.vans-kpi:active, .vans-item:active { background: #f5f5f4; }
.vans-kpi-wide { margin-top: 4px; }
.vans-kpi-label, .vans-section-toggle { display: flex; align-items: center; gap: 6px; color: #44403c; font-size: 12px; font-weight: 700; }
.vans-kpi-label svg, .vans-section-toggle svg { flex: 0 0 auto; }
.vans-kpi-value { margin-top: 8px; font-size: 1.35rem; font-weight: 800; line-height: 1.15; letter-spacing: -0.02em; color: #1c1917; overflow-wrap: anywhere; }
.vans-kpi-note { margin: 6px 0 8px; color: #57534e; font-size: 13px; }
.vans-bar { height: 8px; border-radius: 999px; background: #e7e5e4; overflow: hidden; }
.vans-bar span { display: block; height: 100%; background: #44403c; }
.vans-kpi.is-good { border-top: 3px solid #15803d; }
.vans-kpi.is-good .vans-bar span { background: #15803d; }
.vans-kpi.is-warn { border-top: 3px solid #b45309; }
.vans-kpi.is-warn .vans-bar span { background: #b45309; }
.vans-kpi.is-bad { border-top: 3px solid #b91c1c; }
.vans-kpi.is-bad .vans-bar span { background: #b91c1c; }
.vans-section { margin-top: 10px; overflow: hidden; }
.vans-section-toggle {
	width: 100%;
	min-height: 48px;
	padding: 10px 12px;
	border: 0;
	background: transparent;
	text-align: left;
	font-size: 15px;
	color: #1c1917;
	cursor: pointer;
}
.vans-section-name { flex: 1; text-align: left; }
.vans-count { flex: 0 0 auto; min-width: 1.5rem; padding: 2px 8px; border-radius: 999px; background: #efefef; color: #44403c; font-size: 12px; text-align: center; }
.vans-section-body { display: none; padding: 0 12px 12px; }
.vans-section.is-open .vans-section-body { display: block; }
.vans-section h3 { margin: 8px 0; font-size: 13px; color: #57534e; }
.vans-item { display: block; width: 100%; min-height: 44px; padding: 10px 0; border: 0; border-top: 1px solid #e7e5e4; border-radius: 0; background: transparent; color: inherit; font: inherit; text-align: left; cursor: pointer; }
.vans-item-title { font-weight: 800; margin-bottom: 6px; }
.vans-item dl { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; margin: 0; }
.vans-item dt { font-size: 11px; color: #57534e; font-weight: 600; }
.vans-item dd { margin: 0; font-weight: 700; color: #1c1917; overflow-wrap: anywhere; }
.vans-empty { display: flex; align-items: center; gap: 8px; margin: 8px 0; color: #57534e; font-size: 14px; }
.vans-empty svg { flex: 0 0 auto; }
@media (min-width: 800px) {
	.vans-kpis { grid-template-columns: repeat(4, minmax(0, 1fr)); }
	.vans-actions .vans-btn { flex: 0 1 auto; }
	.vans-360 { padding-left: 16px; padding-right: 16px; }
}
[data-theme="dark"] .vans-360 { color: #f5f5f4; }
[data-theme="dark"] .vans-kpi,
[data-theme="dark"] .vans-section,
[data-theme="dark"] .vans-btn,
[data-theme="dark"] .vans-filter-toggle { background: #292524; border-color: #44403c; color: #f5f5f4; }
[data-theme="dark"] .vans-btn-solid { background: #f5f5f4; color: #1c1917; }
[data-theme="dark"] .vans-kpi-value,
[data-theme="dark"] .vans-item dd,
[data-theme="dark"] .vans-section-toggle { color: #f5f5f4; }
[data-theme="dark"] .vans-360-page .page-head { background: #1c1917 !important; border-bottom-color: #44403c; }
`;
