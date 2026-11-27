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

	// The desk often keeps an old copy of app_include_css after a pull. The page
	// script is what actually updates, so the rules travel with it.
	const PAGE_STYLE = `
/* Distributor 360. Light desk theme, cards stack on a phone. */
.melliflous-quick.melliflous-360 {
	max-width: 76rem;
	color: #1c1917;
}
.melliflous-360 .toolbar {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 12px;
	margin-top: 8px;
}
.melliflous-360 .growth-row {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 12px;
	margin-top: 8px;
}
.melliflous-360 .growth-row .form-control {
	max-width: 8rem;
}
.melliflous-360 .pill {
	border: 0;
	border-radius: 999px;
	min-height: 44px;
	padding: 0 16px;
	color: #fff;
	font-weight: 700;
	cursor: pointer;
}
.melliflous-360 .pill.visit { background: #2f6fdb; }
.melliflous-360 .pill.quote { background: #e07a1f; }
.melliflous-360 .pill.stock { background: #0e8f8a; }
.melliflous-360 .pill.complaint { background: #c0392b; }
.melliflous-360 .pill.target { background: #1f9d55; }
.melliflous-360 .band {
	margin-top: 16px;
	padding: 20px 22px;
	border-radius: 18px;
	background: linear-gradient(120deg, #C8102E 0%, #7A0019 100%);
	color: #fff;
}
.melliflous-360 .band-title {
	font-size: 1.6rem;
	font-weight: 800;
	line-height: 1.2;
}
.melliflous-360 .band-people {
	display: flex;
	flex-wrap: wrap;
	gap: 16px;
	margin-top: 12px;
}
.melliflous-360 .person-label {
	display: block;
	font-size: 0.75rem;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	opacity: 0.85;
}
.melliflous-360 .person-value {
	font-weight: 700;
}
.melliflous-360 .status-pill {
	display: inline-block;
	margin-top: 14px;
	padding: 4px 12px;
	border-radius: 999px;
	background: rgba(255, 255, 255, 0.18);
	font-weight: 700;
}
.melliflous-360 .status-pill.is-off { background: rgba(0, 0, 0, 0.25); }
.melliflous-360 .band-note { margin: 10px 0 0; }
.melliflous-360 .band .pill { margin-top: 12px; }
.melliflous-360 .kpi-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
	gap: 8px;
	margin-top: 12px;
}
.melliflous-360 .kpi {
	padding: 12px;
	border: 1px solid #eadfd8;
	border-radius: 14px;
	background: #fff;
	border-top: 4px solid #d6d3d1;
}
.melliflous-360 .kpi.tone-green { border-top-color: #1f9d55; background: #f3fbf6; }
.melliflous-360 .kpi.tone-amber { border-top-color: #e07a1f; background: #fff8ef; }
.melliflous-360 .kpi.tone-red { border-top-color: #c0392b; background: #fdf4f3; }
.melliflous-360 .kpi.tone-teal { border-top-color: #0e8f8a; background: #f3fbfa; }
.melliflous-360 .kpi-head {
	display: flex;
	align-items: center;
	gap: 8px;
}
.melliflous-360 .kpi-icon {
	display: inline-flex;
	width: 28px;
	height: 28px;
	align-items: center;
	justify-content: center;
	border-radius: 8px;
	background: #f4f1ee;
	color: #6b1d2a;
}
.melliflous-360 svg {
	width: 18px !important;
	height: 18px !important;
	max-width: 18px;
	max-height: 18px;
}
.melliflous-360 .kpi-icon svg { width: 18px; height: 18px; }
.melliflous-360 .kpi .detail {
	margin-top: 4px;
	color: #57534e;
	font-size: 0.85rem;
}
.melliflous-360 .progress {
	height: 8px;
	margin-top: 10px;
	border-radius: 999px;
	background: #efe7e2;
	overflow: hidden;
}
.melliflous-360 .progress-bar {
	display: block;
	height: 100%;
	border-radius: 999px;
	background: #a8a29e;
}
.melliflous-360 .progress-bar.tone-green { background: #1f9d55; }
.melliflous-360 .progress-bar.tone-amber { background: #e07a1f; }
.melliflous-360 .progress-bar.tone-red { background: #c0392b; }
.melliflous-360 .panel {
	margin-top: 16px;
	padding: 14px 16px;
	border: 1px solid #eadfd8;
	border-radius: 16px;
	background: #fff;
}
.melliflous-360 .spark {
	display: flex;
	align-items: flex-end;
	gap: 8px;
	height: 88px;
	margin-top: 12px;
}
.melliflous-360 .spark-col {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	height: 100%;
	justify-content: flex-end;
}
.melliflous-360 .spark-bar {
	display: block;
	width: 100%;
	max-width: 28px;
	border-radius: 6px 6px 2px 2px;
	background: #c0392b;
}
.melliflous-360 .spark-label {
	margin-top: 4px;
	font-size: 0.75rem;
	color: #57534e;
}
.melliflous-360 .badge {
	display: inline-block;
	padding: 2px 8px;
	border-radius: 999px;
	font-size: 0.8rem;
	font-weight: 700;
}
.melliflous-360 .badge.pace-fast { background: #e7f6ee; color: #135c36; }
.melliflous-360 .badge.pace-slow { background: #fff4e5; color: #9a4d00; }
.melliflous-360 .badge.pace-no-movement { background: #fde8e8; color: #8d1d1d; }
.melliflous-360 .timeline { display: flex; flex-direction: column; gap: 8px; }
.melliflous-360 .event {
	display: flex;
	gap: 10px;
	align-items: flex-start;
	padding: 10px 12px;
	border: 1px solid #eadfd8;
	border-radius: 12px;
	background: #fff;
}
.melliflous-360 .event-mark {
	flex: 0 0 auto;
	width: 28px;
	height: 28px;
	border-radius: 999px;
	color: #fff;
	font-weight: 800;
	line-height: 28px;
	text-align: center;
}
.melliflous-360 .kind-visit .event-mark { background: #2f6fdb; }
.melliflous-360 .kind-invoice .event-mark { background: #1f9d55; }
.melliflous-360 .kind-payment .event-mark { background: #1f9d55; }
.melliflous-360 .kind-order .event-mark { background: #0e8f8a; }
.melliflous-360 .kind-quotation .event-mark { background: #e07a1f; }
.melliflous-360 .kind-draft .event-mark { background: #78716c; }
.melliflous-360 .kind-complaint .event-mark { background: #c0392b; }
.melliflous-360 .kind-credit .event-mark { background: #7a45c4; }
.melliflous-360 .qpill-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }
.melliflous-360 .qpill {
	display: inline-block;
	margin: 6px 8px 0 0;
	padding: 3px 10px;
	border-radius: 999px;
	font-size: 0.8rem;
	font-weight: 700;
	background: #e7e5e4;
	color: #44403c;
}
.melliflous-360 .qpill.tone-grey { background: #e7e5e4; color: #44403c; }
.melliflous-360 .qpill.tone-blue { background: #e8f0fc; color: #1d4e89; }
.melliflous-360 .qpill.tone-green { background: #e7f6ee; color: #135c36; }
.melliflous-360 .qpill.tone-red { background: #fde8e8; color: #8d1d1d; }
.melliflous-360 .legend-box {
	margin-top: 20px;
	padding: 12px 14px;
	border-radius: 14px;
	background: #faf7f5;
}
.melliflous-360 .legend-row {
	display: flex;
	gap: 8px;
	align-items: flex-start;
	margin-top: 6px;
}
.melliflous-360 .legend-dot {
	flex: 0 0 auto;
	width: 12px;
	height: 12px;
	margin-top: 4px;
	border-radius: 999px;
	background: #a8a29e;
}
.melliflous-360 .legend-dot.tone-green,
.melliflous-360 .legend-dot.tone-fast { background: #1f9d55; }
.melliflous-360 .legend-dot.tone-amber,
.melliflous-360 .legend-dot.tone-slow { background: #e07a1f; }
.melliflous-360 .legend-dot.tone-red,
.melliflous-360 .legend-dot.tone-still { background: #c0392b; }
@media (max-width: 720px) {
	.melliflous-360 .toolbar,
	.melliflous-360 .kpi-grid {
		grid-template-columns: 1fr;
	}
	.melliflous-360 .band-title { font-size: 1.35rem; }
}
.melliflous-360 .kpi .label {
	color: var(--ink-gray-7, #4b5563);
	font-size: 0.85rem;
}
.melliflous-360 .kpi .value {
	margin-top: 4px;
	font-size: 1.05rem;
	font-weight: 700;
	line-height: 1.3;
	overflow-wrap: anywhere;
}
.melliflous-360 .btn-row {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-top: 12px;
}
.melliflous-360 .btn-row .btn,
.melliflous-360 .btn-primary,
.melliflous-360 .btn-default {
	min-height: 44px;
}
.melliflous-360 .legend {
	display: flex;
	flex-wrap: wrap;
	gap: 16px;
	margin: 8px 0;
}
.melliflous-360 .swatch::before {
	content: "";
	display: inline-block;
	width: 12px;
	height: 12px;
	margin-right: 6px;
	border-radius: 999px;
	vertical-align: -1px;
}
.melliflous-360 .swatch.primary::before {
	background: #1f4d3a;
}
.melliflous-360 .swatch.secondary::before {
	background: #e07a1f;
}
.melliflous-360 .month-row {
	display: grid;
	grid-template-columns: 4.2rem 1fr;
	gap: 8px;
	align-items: center;
	margin-top: 6px;
}
.melliflous-360 .month-label {
	font-size: 0.85rem;
	color: var(--ink-gray-7, #4b5563);
}
.melliflous-360 .bar-track {
	display: flex;
	flex-direction: column;
	gap: 3px;
}
.melliflous-360 .bar-line {
	display: flex;
	align-items: center;
	gap: 8px;
	min-height: 14px;
}
.melliflous-360 .bar {
	display: block;
	height: 10px;
	border-radius: 999px;
	min-width: 0;
}
.melliflous-360 .bar.primary {
	background: #1f4d3a;
}
.melliflous-360 .bar.secondary {
	background: #e07a1f;
}
.melliflous-360 .bar-value {
	font-size: 0.8rem;
	color: var(--ink-gray-7, #4b5563);
}
.melliflous-360 .table-wrap {
	overflow-x: auto;
	margin-top: 8px;
}
.melliflous-360 table {
	width: 100%;
	border-collapse: collapse;
}
.melliflous-360 th,
.melliflous-360 td {
	padding: 6px 8px;
	border-bottom: 1px solid var(--border-color, #e5e7eb);
	text-align: left;
	font-size: 0.95rem;
	white-space: nowrap;
}
.melliflous-360 a.who {
	color: inherit;
	text-decoration: none;
}
.melliflous-360 .pill.is-on {
	box-shadow: inset 0 0 0 2px #fff, 0 0 0 2px #1c1917;
}
.melliflous-360 .pill.ghost {
	background: #fff;
	color: #1c1917;
	border: 1px solid #eadfd8;
}
.melliflous-360 .pill.ghost.is-on {
	background: #6b1d2a;
	color: #fff;
}
.melliflous-360 .mis-filters {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	align-items: flex-end;
	margin-top: 12px;
}
.melliflous-360 .mis-filters .filter-slot {
	min-width: 10rem;
}
.melliflous-360 .search-input {
	min-height: 32px;
	min-width: 12rem;
}
.melliflous-360 .status-chip {
	display: inline-block;
	padding: 2px 8px;
	border-radius: 999px;
	font-weight: 700;
	font-size: 0.8rem;
}
.melliflous-360 .status-chip.is-on { background: #e7f6ee; color: #135c36; }
.melliflous-360 .status-chip.is-off { background: #fde8e8; color: #8d1d1d; }
.melliflous-360 .cell-red { color: #c0392b; font-weight: 700; }
.melliflous-360 .rag {
	display: inline-block;
	min-width: 3.2rem;
	padding: 2px 8px;
	border-radius: 999px;
	font-weight: 700;
	text-align: center;
}
.melliflous-360 .rag.tone-green { background: #e7f6ee; color: #135c36; }
.melliflous-360 .rag.tone-amber { background: #fff4e5; color: #9a4d00; }
.melliflous-360 .rag.tone-red { background: #fde8e8; color: #8d1d1d; }
.melliflous-360 .rag.tone-neutral { background: #e7e5e4; color: #44403c; }
.melliflous-360 tr.mis-row { cursor: pointer; }
.melliflous-360 tr.mis-row:hover { background: #faf7f5; }
.melliflous-360 th.sortable { cursor: pointer; }
.melliflous-360 .mini-spark {
	display: flex;
	align-items: flex-end;
	gap: 2px;
	height: 28px;
	width: 52px;
}
.melliflous-360 .mini-spark span {
	display: block;
	width: 6px;
	height: 4px;
	border-radius: 2px 2px 0 0;
	background: #c0392b;
}
@media (max-width: 720px) {
	.melliflous-360 .mis-filters { flex-direction: column; align-items: stretch; }
}
`;

	function installStyles() {
		const id = "melliflous-distributor-360";
		try {
			if (window.frappe && frappe.dom && typeof frappe.dom.set_style === "function") {
				frappe.dom.set_style(PAGE_STYLE, id);
				return;
			}
		} catch (ignored) {
			/* a plain style tag below still applies the rules */
		}
		const parent = document.head || document.documentElement;
		if (!parent) return;
		let node = document.getElementById(id);
		if (!node) {
			node = document.createElement("style");
			node.id = id;
			parent.appendChild(node);
		}
		node.textContent = PAGE_STYLE;
	}

	installStyles();

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
				'<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 19h16v2H4zm2-3 4-5 3 3 5-7 2 1.4-7 9.6-3-3-3 3.8z"/></svg>',
			secondary:
				'<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 7h16v2H4zm0 4h10v2H4zm0 4h16v2H4z"/></svg>',
			stock:
				'<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 7 12 3l9 4-9 4zm0 3.2V17l9 4 9-4v-6.8l-9 4z"/></svg>',
			billing:
				'<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M6 2h9l5 5v15H6zm8 1.5V8h4.5zM8 12h8v2H8zm0 4h6v2H8z"/></svg>',
			counters:
				'<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 18V6h4v12zm6 0V10h4v8zm6 0V4h4v14z"/></svg>',
			money:
				'<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 3a9 9 0 1 0 .01 18.01A9 9 0 0 0 12 3m1 14v1h-2v-1c-1.7-.3-3-1.4-3-3h2c0 .6.7 1 2 1s2-.4 2-1-1-1-2.5-1.3C8.2 12.1 7 11 7 9.2 7 7.4 8.4 6.2 11 6V5h2v1c1.5.2 2.6 1.1 2.9 2.5h-2c-.2-.5-.6-.8-1.4-.8-1 0-1.5.4-1.5 1s.6.9 2.2 1.2C15.8 10.4 17 11.5 17 13.3c0 1.9-1.5 3.2-4 3.7"/></svg>',
			visit:
				'<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7m0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5"/></svg>',
			quote:
				'<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M6 4h9l5 5v11H6zm8 1.5V9h3.5zM8 13h8v2H8zm0 4h5v2H8z"/></svg>',
		};
		const node = el("span", "kpi-icon");
		node.innerHTML = paths[name] || "";
		const drawn = node.querySelector("svg");
		if (drawn) {
			drawn.setAttribute("width", "18");
			drawn.setAttribute("height", "18");
		}
		return node;
	}

	function render(page, wrapper) {
		installStyles();
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

		const modeRow = el("div", "btn-row");
		const allButton = pill(__("All distributors"), "stock", () => showAll());
		const oneButton = pill(__("This distributor"), "visit", () => showOne());
		modeRow.appendChild(allButton);
		modeRow.appendChild(oneButton);
		root.appendChild(modeRow);

		const filters = {
			activity: "All",
			search: "",
			territory: "",
			account_manager: "",
			sales_person: "",
			rag: "",
		};
		const picked = new Set();
		let misPayload = null;
		let sortKey = "name";
		let sortDir = 1;
		let viewMode = "all";

		const filterBar = el("div", "mis-filters");
		filterBar.hidden = true;
		const activityRow = el("div", "btn-row");
		const activityButtons = {};
		["All", "Active", "Inactive"].forEach((label) => {
			const button = pill(__(label), "ghost", () => {
				filters.activity = label;
				paintActivity();
				schedule();
			});
			activityButtons[label] = button;
			activityRow.appendChild(button);
		});
		filterBar.appendChild(activityRow);
		const search = el("input", "form-control search-input");
		search.type = "search";
		search.placeholder = __("Search distributors");
		search.addEventListener("input", () => {
			filters.search = search.value;
			schedule();
		});
		filterBar.appendChild(search);
		const territorySlot = el("div", "filter-slot");
		const managerSlot = el("div", "filter-slot");
		const personSlot = el("div", "filter-slot");
		filterBar.appendChild(territorySlot);
		filterBar.appendChild(managerSlot);
		filterBar.appendChild(personSlot);
		const rag = el("select", "form-control");
		[
			["", __("Any achievement")],
			["green", __("Green, 90% or more")],
			["amber", __("Amber, 60–89%")],
			["red", __("Red, under 60%")],
		].forEach((option) => {
			const node = el("option", "", option[1]);
			node.value = option[0];
			rag.appendChild(node);
		});
		rag.addEventListener("change", () => {
			filters.rag = rag.value;
			schedule();
		});
		filterBar.appendChild(rag);
		filterBar.appendChild(
			pill(__("Export Excel / CSV"), "quote", () => exportDistributors(misPayload))
		);
		const bulkButton = pill(__("Apply recommended to selected"), "target", () => applyRecommended());
		filterBar.appendChild(bulkButton);
		root.appendChild(filterBar);
		function paintActivity() {
			Object.keys(activityButtons).forEach((label) => {
				activityButtons[label].classList.toggle("is-on", filters.activity === label);
			});
		}
		paintActivity();

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
			const territoryControl = frappe.ui.form.make_control({
				parent: territorySlot,
				df: {
					fieldtype: "Link",
					options: "Territory",
					fieldname: "territory",
					label: __("Territory"),
					change() {
						filters.territory = territoryControl.get_value() || "";
						schedule();
					},
				},
				render_input: true,
			});
			const managerControl = frappe.ui.form.make_control({
				parent: managerSlot,
				df: {
					fieldtype: "Link",
					options: "User",
					fieldname: "account_manager",
					label: __("Salesman / account manager"),
					change() {
						filters.account_manager = managerControl.get_value() || "";
						schedule();
					},
				},
				render_input: true,
			});
			const personControl = frappe.ui.form.make_control({
				parent: personSlot,
				df: {
					fieldtype: "Link",
					options: "Sales Person",
					fieldname: "sales_person",
					label: __("Sales Person"),
					change() {
						filters.sales_person = personControl.get_value() || "";
						schedule();
					},
				},
				render_input: true,
			});
			territoryControl.refresh();
			managerControl.refresh();
			personControl.refresh();
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
		actions.appendChild(pill(__("Set Target"), "target", () => openSetTarget(state)));
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
		growthRow.hidden = true;
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
			if (viewMode !== "one") return false;
			if (!state || state.customer !== customer) return false;
			return (state.company || "") === selectedCompany();
		}

		function paintChrome() {
			const all = viewMode === "all";
			filterBar.hidden = !all;
			actions.hidden = all;
			allButton.classList.toggle("is-on", all);
			oneButton.classList.toggle("is-on", !all);
			bulkButton.hidden = !canSetTargets();
		}

		function showAll() {
			viewMode = "all";
			rememberView("all");
			silence = true;
			if (distributorControl.set_value) distributorControl.set_value("");
			window.setTimeout(() => {
				silence = false;
				loadAll();
			}, 0);
		}

		function showOne() {
			viewMode = "one";
			rememberView("");
			if (!selectedDistributor()) {
				paintChrome();
				body.replaceChildren();
				body.appendChild(el("p", "hint", __("Pick a distributor.")));
				return;
			}
			load();
		}

		function pageQuery() {
			const search = new URLSearchParams(window.location.search || "");
			if (search.get("view")) return search;
			const hash = window.location.hash || "";
			const query = hash.includes("?") ? hash.slice(hash.indexOf("?")) : "";
			return new URLSearchParams(query);
		}

		function rememberView(view) {
			try {
				const url = new URL(window.location.href);
				if (view) url.searchParams.set("view", view);
				else url.searchParams.delete("view");
				window.history.replaceState(null, "", `${url.pathname}${url.search}`);
			} catch (ignored) {
				/* the page still switches without rewriting the address */
			}
		}

		function load() {
			const customer = selectedDistributor();
			if (!customer) {
				loadAll();
				return;
			}
			viewMode = "one";
			paintChrome();
			body.replaceChildren();
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
			const quiet = signals.no_submitted_invoices;
			if (quiet) {
				card.appendChild(el("p", "", __(EMPTY_BILLING)));
			}
			if (signals.target_amount) {
				const targetLine = el(
					"p",
					"",
					__("{0} of {1} this month ({2}%).", [
						moneyText(data.primary_mtd, currency),
						moneyText(signals.target_amount, currency),
						String(signals.achievement_pct),
					])
				);
				card.appendChild(targetLine);
				if (signals.target_source) {
					const tone = signals.target_source === "Manual" ? "blue" : "green";
					card.appendChild(el("span", `qpill tone-${tone}`, signals.target_source));
				}
				card.appendChild(progress(signals.achievement_pct, signals.primary_tone));
			} else if (!quiet) {
				card.appendChild(el("p", "hint", __("No target is set for this month.")));
			}
			const recommendation = data.recommendation || {};
			const recommended = el(
				"p",
				"",
				__("Recommended {0}", [moneyText(signals.recommended_amount ?? recommendation.amount, currency)])
			);
			recommended.title = recommendation.basis || signals.recommendation_basis || "";
			card.appendChild(recommended);
			if (recommended.title) card.appendChild(el("p", "hint", recommended.title));
			card.appendChild(sparkline((data.chart || []).slice(-6)));
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

		function canSetTargets() {
			try {
				if (frappe.model && frappe.model.can_create) {
					return !!frappe.model.can_create("Customer Primary Target");
				}
			} catch (ignored) {
				/* the server still refuses a Sales User */
			}
			return true;
		}

		function loadAll() {
			viewMode = "all";
			paintChrome();
			const current = ++requestId;
			body.replaceChildren();
			body.appendChild(el("p", "", __("Loading…")));
			note.hidden = true;
			frappe
				.call({
					method: `${API}.distributor_mis`,
					args: {
						company: selectedCompany(),
						activity: filters.activity,
						search: filters.search,
						territory: filters.territory,
						account_manager: filters.account_manager,
						sales_person: filters.sales_person,
						rag: filters.rag,
					},
				})
				.then((response) => {
					if (current !== requestId) return;
					misPayload = response.message || {};
					drawMis(misPayload);
				})
				.catch((error) => {
					if (current !== requestId) return;
					body.replaceChildren();
					show(errorText(error), true);
					body.appendChild(el("p", "", __("The distributor book could not be loaded.")));
				});
		}

		function drawMis(data) {
			paintChrome();
			body.replaceChildren();
			const summary = data.summary || {};
			const currency = data.currency;
			const grid = el("div", "kpi-grid");
			grid.appendChild(
				kpiCard(
					"counters",
					__("Distributors"),
					String(summary.distributors || 0),
					"neutral",
					__("{0} active · {1} inactive", [String(summary.active || 0), String(summary.inactive || 0)])
				)
			);
			const primary = kpiCard(
				"primary",
				__("Primary MTD"),
				`${moneyText(summary.primary_mtd, currency)} / ${moneyText(summary.target, currency)}`,
				summary.achievement_tone || "neutral",
				summary.achievement_pct == null ? __("No targets set") : `${summary.achievement_pct}%`
			);
			if (summary.target) primary.appendChild(progress(summary.achievement_pct, summary.achievement_tone));
			grid.appendChild(primary);
			grid.appendChild(
				kpiCard("money", __("Outstanding"), moneyText(summary.outstanding, currency), Number(summary.overdue) > 0 ? "red" : "green")
			);
			grid.appendChild(
				kpiCard(
					"money",
					__("Overdue"),
					moneyText(summary.overdue, currency),
					Number(summary.overdue) > 0 ? "red" : "green"
				)
			);
			grid.appendChild(
				kpiCard(
					"billing",
					__("Not billed in 30+ days"),
					String(summary.not_billed_30 || 0),
					Number(summary.not_billed_30) > 0 ? "red" : "green"
				)
			);
			grid.appendChild(
				kpiCard("visit", __("Visits this month"), String(summary.visits_mtd || 0), summary.visits_mtd ? "green" : "neutral")
			);
			grid.appendChild(
				kpiCard("quote", __("Open quotations"), moneyText(summary.open_quotations, currency), "amber")
			);
			grid.appendChild(
				kpiCard("primary", __("Collections MTD"), moneyText(summary.collections_mtd, currency), "green")
			);
			body.appendChild(grid);
			body.appendChild(
				el(
					"p",
					"hint",
					__(
						"Primary and collections count submitted documents only. Draft invoices are excluded. Achievement is green from 90%, amber from 60%, and red below that. A last bill older than 30 days is red."
					)
				)
			);
			body.appendChild(misTable(sortedRows(data.rows || []), currency));
		}

		function sortedRows(rows) {
			const copy = rows.slice();
			copy.sort((left, right) => compareMis(left, right, sortKey) * sortDir);
			return copy;
		}

		function compareMis(left, right, key) {
			const a = misSortValue(left, key);
			const b = misSortValue(right, key);
			if (a == null && b == null) return 0;
			if (a == null) return 1;
			if (b == null) return -1;
			if (typeof a === "number" && typeof b === "number") return a - b;
			return String(a).localeCompare(String(b));
		}

		function misSortValue(row, key) {
			if (key === "target" || key === "achievement_pct" || key === "days_since_billing") {
				return row[key] == null || row[key] === "" ? null : Number(row[key]);
			}
			if (key === "primary_mtd" || key === "outstanding" || key === "overdue" || key === "open_quotations" || key === "recommended") {
				return Number(row[key]) || 0;
			}
			return row[key] || "";
		}

		function misTable(rows, currency) {
			const wrap = el("div", "table-wrap");
			if (!rows.length) {
				wrap.appendChild(el("p", "hint", __("No distributors match these filters.")));
				return wrap;
			}
			const table = el("table", "mis-table");
			const head = el("tr");
			const selectAll = el("input");
			selectAll.type = "checkbox";
			selectAll.addEventListener("click", (event) => event.stopPropagation());
			selectAll.checked = rows.length > 0 && rows.every((row) => picked.has(row.distributor));
			selectAll.addEventListener("change", () => {
				rows.forEach((row) => {
					if (selectAll.checked) picked.add(row.distributor);
					else picked.delete(row.distributor);
				});
				drawMis(misPayload);
			});
			const selectCell = el("th");
			selectCell.appendChild(selectAll);
			head.appendChild(selectCell);
			const columns = [
				["name", __("Distributor")],
				["status", __("Status")],
				["primary_mtd", __("MTD primary")],
				["target", __("Target")],
				["recommended", __("Recommended")],
				["source", __("Source")],
				["achievement_pct", __("Achievement")],
				["days_since_billing", __("Last billing")],
				["outstanding", __("Outstanding")],
				["overdue", __("Overdue")],
				["last_visit", __("Last visit")],
				["next_visit_due", __("Next visit due")],
				["open_quotations", __("Open quotations")],
				["spark", __("6 months")],
			];
			columns.forEach((column) => {
				const cell = el("th", column[0] === "spark" || column[0] === "source" ? "" : "sortable", headerLabel(column));
				if (column[0] !== "spark" && column[0] !== "source") {
					cell.addEventListener("click", () => {
						if (sortKey === column[0]) sortDir = -sortDir;
						else {
							sortKey = column[0];
							sortDir = 1;
						}
						drawMis(misPayload);
					});
				}
				head.appendChild(cell);
			});
			if (canSetTargets()) head.appendChild(el("th", "", __("Target")));
			table.appendChild(head);
			rows.forEach((row) => table.appendChild(misRow(row, currency)));
			wrap.appendChild(table);
			return wrap;
		}

		function headerLabel(column) {
			if (sortKey !== column[0]) return column[1];
			return `${column[1]} ${sortDir > 0 ? "↑" : "↓"}`;
		}

		function misRow(row, currency) {
			const tr = el("tr", "mis-row");
			tr.addEventListener("click", () => openDistributor(row));
			const checkCell = el("td");
			const box = el("input");
			box.type = "checkbox";
			box.checked = picked.has(row.distributor);
			box.addEventListener("click", (event) => event.stopPropagation());
			box.addEventListener("change", () => {
				if (box.checked) picked.add(row.distributor);
				else picked.delete(row.distributor);
			});
			checkCell.appendChild(box);
			tr.appendChild(checkCell);
			tr.appendChild(el("td", "", row.name || row.distributor));
			const status = el("span", row.active ? "status-chip is-on" : "status-chip is-off", row.status || "");
			status.title = row.rule || "";
			const statusCell = el("td");
			statusCell.appendChild(status);
			tr.appendChild(statusCell);
			tr.appendChild(el("td", "", moneyText(row.primary_mtd, currency)));
			tr.appendChild(el("td", "", row.target == null ? "—" : moneyText(row.target, currency)));
			const recommendedCell = el("td", "", moneyText(row.recommended, currency));
			recommendedCell.title = row.recommendation_basis || "";
			tr.appendChild(recommendedCell);
			tr.appendChild(sourceCell(row.target_source));
			const ragCell = el("td");
			const ragText = row.achievement_pct == null ? "—" : `${row.achievement_pct}%`;
			ragCell.appendChild(el("span", `rag tone-${row.rag || "neutral"}`, ragText));
			tr.appendChild(ragCell);
			tr.appendChild(billingCell(row));
			tr.appendChild(el("td", "", moneyText(row.outstanding, currency)));
			const overdueCell = el("td", Number(row.overdue) > 0 ? "cell-red" : "", moneyText(row.overdue, currency));
			tr.appendChild(overdueCell);
			tr.appendChild(el("td", "", row.last_visit ? prettyDate(row.last_visit) : "—"));
			tr.appendChild(el("td", "", row.next_visit_due ? prettyDate(row.next_visit_due) : "—"));
			tr.appendChild(el("td", "", moneyText(row.open_quotations, currency)));
			const sparkCell = el("td");
			sparkCell.appendChild(miniSpark(row.sparkline || []));
			tr.appendChild(sparkCell);
			if (canSetTargets()) {
				const action = el("td");
				const button = pill(__("Set Target"), "target", (event) => {
					event.stopPropagation();
					openSetTarget(row);
				});
				action.appendChild(button);
				tr.appendChild(action);
			}
			return tr;
		}

		function sourceCell(source) {
			const cell = el("td");
			if (!source) {
				cell.textContent = "—";
				return cell;
			}
			const tone = source === "Manual" ? "blue" : "green";
			cell.appendChild(el("span", `qpill tone-${tone}`, source));
			return cell;
		}

		function billingCell(row) {
			let text = __("Never");
			if (row.last_billing) {
				text = `${prettyDate(row.last_billing)} · ${row.days_since_billing}d`;
			}
			return el("td", row.billing_stale ? "cell-red" : "", text);
		}

		function miniSpark(values) {
			const wrap = el("div", "mini-spark");
			const max = Math.max(1, ...values.map((value) => Math.abs(Number(value) || 0)));
			values.forEach((value) => {
				const bar = el("span");
				const height = Math.max(4, (Math.abs(Number(value) || 0) / max) * 28);
				bar.style.height = `${height}px`;
				wrap.appendChild(bar);
			});
			return wrap;
		}

		function openDistributor(row) {
			viewMode = "one";
			rememberView("");
			silence = true;
			if (distributorControl.set_value) distributorControl.set_value(row.distributor);
			window.setTimeout(() => {
				silence = false;
				load();
			}, 0);
		}

		function openSetTarget(row) {
			const customer = row && (row.distributor || row.customer);
			if (!customer) {
				show(__("Pick a distributor first."), true);
				return;
			}
			if (!window.frappe || !frappe.ui || !frappe.ui.Dialog) {
				show(__("The target dialog is not available on this desk."), true);
				return;
			}
			const basis =
				row.recommendation_basis ||
				(row.recommendation && row.recommendation.basis) ||
				(row.signals && row.signals.recommendation_basis) ||
				"";
			const dialog = new frappe.ui.Dialog({
				title: __("Set Target"),
				fields: [
					{
						fieldname: "mode",
						fieldtype: "Select",
						label: __("Choice"),
						options: "Use recommended\nEnter manually",
						default: row.target_source === "Manual" ? "Enter manually" : "Use recommended",
						reqd: 1,
					},
					{
						fieldname: "basis",
						fieldtype: "Small Text",
						label: __("Why this recommendation"),
						read_only: 1,
						default: basis,
					},
					{
						fieldname: "amount",
						fieldtype: "Currency",
						label: __("Amount"),
						depends_on: "eval:doc.mode=='Enter manually'",
						default: row.target || (row.signals && row.signals.target_amount) || "",
					},
					{
						fieldname: "target_month",
						fieldtype: "Date",
						label: __("Month"),
						reqd: 1,
						default: frappe.datetime.month_start(),
					},
					{
						fieldname: "note",
						fieldtype: "Small Text",
						label: __("Note"),
						description: __(
							"Optional. Saving updates this month's target and keeps earlier months. Each change stays on the target."
						),
					},
				],
				primary_action_label: __("Set Target"),
				primary_action(values) {
					dialog.disable_primary_action();
					frappe
						.call({
							method: `${API}.set_distributor_target`,
							args: {
								customer: customer,
								company: row.company || selectedCompany(),
								source: values.mode === "Enter manually" ? "Manual" : "Recommended",
								amount: values.amount,
								target_month: values.target_month,
								note: values.note || "",
							},
						})
						.then((response) => {
							dialog.hide();
							const saved = response.message || {};
							show(
								__("Target {0} set to {1}.", [
									saved.name || "",
									moneyText(saved.target_amount, saved.currency || (row && row.currency)),
								])
							);
							load();
						})
						.catch((error) => {
							dialog.enable_primary_action();
							show(errorText(error), true);
						});
				},
			});
			dialog.show();
		}

		function applyRecommended() {
			const names = Array.from(picked);
			if (!names.length) {
				show(__("Select at least one distributor."), true);
				return;
			}
			if (!window.confirm(__("Apply the recommended target to {0} distributors for this month?", [String(names.length)]))) {
				return;
			}
			frappe
				.call({
					method: `${API}.apply_recommended_targets`,
					args: {
						customers: JSON.stringify(names),
						company: selectedCompany(),
						target_month: frappe.datetime.month_start(),
					},
				})
				.then((response) => {
					const saved = response.message || {};
					const applied = (saved.applied || []).length;
					const skipped = (saved.skipped || []).length;
					show(__("Applied the recommended target to {0}. Skipped {1}.", [String(applied), String(skipped)]));
					picked.clear();
					loadAll();
				})
				.catch((error) => show(errorText(error), true));
		}

		function exportDistributors(data) {
			const rows = sortedRows((data && data.rows) || []);
			const header = [
				"Distributor",
				"Status",
				"Rule",
				"MTD primary",
				"Target",
				"Recommended",
				"Source",
				"Achievement %",
				"Last billing",
				"Days since billing",
				"Outstanding",
				"Overdue",
				"Last visit",
				"Next visit due",
				"Open quotations",
				"Basis",
			];
			const lines = [header.map(csvEscape).join(",")];
			rows.forEach((row) => {
				lines.push(
					[
						row.name,
						row.status,
						row.rule,
						row.primary_mtd,
						row.target,
						row.recommended,
						row.target_source,
						row.achievement_pct,
						row.last_billing,
						row.days_since_billing,
						row.outstanding,
						row.overdue,
						row.last_visit,
						row.next_visit_due,
						row.open_quotations,
						row.recommendation_basis,
					]
						.map(csvEscape)
						.join(",")
				);
			});
			const blob = new Blob([`\uFEFF${lines.join("\n")}`], { type: "text/csv;charset=utf-8" });
			const link = el("a");
			link.href = URL.createObjectURL(blob);
			link.download = "distributors.csv";
			link.click();
		}

		function csvEscape(value) {
			const text = value == null ? "" : String(value);
			if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
			return text;
		}

		const options = frappe.route_options || {};
		const openedAll = pageQuery().get("view") === "all" || options.view === "all";
		if (options.company) companyControl.set_value(options.company);
		else {
			const presetCompany = frappe.defaults.get_user_default("company");
			if (presetCompany) companyControl.set_value(presetCompany);
		}
		if (!openedAll && options.distributor) distributorControl.set_value(options.distributor);
		if (frappe.route_options) {
			delete frappe.route_options.distributor;
			delete frappe.route_options.company;
			delete frappe.route_options.view;
		}
		if (!selectedDistributor()) loadAll();
	}

	frappe.pages["distributor-360"].on_page_load = function (wrapper) {
		installStyles();
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
