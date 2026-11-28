// Desk branding for Melliflous Group.
// v16 home is the apps screen. Its header title "Desktop" is a node with class
// desktop-navbar-title (hidden on a wide desk, centred on a phone). The browser
// tab is set from frappe.utils.set_title("Desktop"). Both are replaced here.
// The company control is that same title when the user can open more than one
// Company, and a bar on the page head everywhere else in the desk.

(function () {
	if (window.melliflous_branding) {
		return;
	}

	const FALLBACK = "Melliflous Group";
	const SWITCHER_STYLE_ID = "melliflous-context-style";
	const NARROW_QUERY = "(max-width: 900px)";
	// Injected from the script because app_include_css stays cached, and the
	// desk navbar hides or clips anything that is not the home logo or the title.
	// Phones get one chip. The selects move into a bottom sheet so they cannot
	// push the navbar past the screen.
	const SWITCHER_CSS = [
		"body.desktop-page .desktop-navbar,body.desktop-page .navbar-container{display:flex;align-items:center;gap:8px;max-width:100%;overflow:visible;box-sizing:border-box;height:auto;min-height:var(--desktop-navbar-height,49px);padding-inline:8px;}",
		"body.desktop-page .desktop-navbar>.navbar-home{flex:0 0 auto;}",
		"body.desktop-page .melliflous-context{display:flex !important;flex-wrap:wrap;align-items:center;gap:8px;position:static !important;left:auto !important;right:auto !important;flex:1 1 auto;width:auto !important;min-width:0;max-width:100% !important;height:auto !important;overflow:visible !important;transform:none !important;visibility:visible !important;opacity:1 !important;}",
		"body.desktop-page .melliflous-context:not(.is-compact) select.melliflous-company-switch,body.desktop-page .melliflous-context:not(.is-compact) select.melliflous-division-switch{flex:1 1 8rem;width:auto;min-width:0;max-width:16rem;}",
		".melliflous-context.is-compact>.melliflous-context-pill,.melliflous-context.is-compact>.melliflous-context-label,.melliflous-context.is-compact>select{display:none !important;}",
		".melliflous-context.is-compact>.melliflous-context-chip{display:flex !important;}",
		".melliflous-context:not(.is-compact)>.melliflous-context-chip{display:none !important;}",
		"@media (max-width:900px){.melliflous-context>.melliflous-context-label,.melliflous-context>.melliflous-company-switch,.melliflous-context>.melliflous-division-switch,.melliflous-context>.melliflous-context-pill{display:none !important;}.melliflous-context.is-compact>.melliflous-context-chip,.melliflous-sheet-fields .melliflous-context-label{display:flex !important;}.melliflous-sheet-fields select{display:block !important;width:100% !important;min-width:0 !important;max-width:none !important;min-height:48px;font-size:16px;}}",
		".melliflous-context-chip{display:flex;align-items:center;gap:8px;width:100%;min-width:0;min-height:44px;margin:0;padding:6px 8px;border:0;border-radius:8px;background:transparent;color:#1c1917;box-shadow:none;text-align:left;}",
		".melliflous-chip-pill,.melliflous-context-pill{background:#e7e5e4;color:#1c1917;box-shadow:none;}",
		".melliflous-chip-copy{display:flex;flex-direction:column;min-width:0;flex:1 1 auto;}",
		".melliflous-chip-company,.melliflous-chip-division{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}",
		".melliflous-chip-company{color:#1c1917;font-weight:700;}",
		".melliflous-chip-division{color:#57534e;font-weight:600;}",
		".melliflous-chip-caret{border-right-color:#57534e;border-bottom-color:#57534e;}",
		"body .desktop-navbar .melliflous-company-label,body .navbar .melliflous-company-label{color:#1c1917;}",
		"body .desktop-navbar .melliflous-division-label,body .navbar .melliflous-division-label{color:#57534e;}",
		".melliflous-context-sheet{position:fixed;inset:0;z-index:1080;}",
		".melliflous-context-sheet[hidden]{display:none !important;}",
		".melliflous-sheet-panel{position:absolute;left:0;right:0;bottom:0;max-height:min(86vh,560px);overflow:auto;padding:12px 16px calc(16px + env(safe-area-inset-bottom));background:#fffaf3;border-radius:22px 22px 0 0;}",
		".melliflous-sheet-done{width:100%;min-height:48px;margin-top:14px;border:0;border-radius:14px;background:#c8102e;color:#fff;font-weight:800;}",
	].join("");
	let chosen = null;
	let chosenDivision = null;
	let select = null;
	let divisionSelect = null;
	let saving = false;
	let divisionLoad = null;

	function inject_switcher_style() {
		if (document.getElementById(SWITCHER_STYLE_ID)) {
			return;
		}
		const node = document.createElement("style");
		node.id = SWITCHER_STYLE_ID;
		node.textContent = SWITCHER_CSS;
		document.head.appendChild(node);
		if (frappe.dom && typeof frappe.dom.set_style === "function") {
			frappe.dom.set_style(SWITCHER_CSS, SWITCHER_STYLE_ID);
		}
	}

	function boot() {
		return (frappe.boot && frappe.boot.melliflous_branding) || {};
	}

	function company_title() {
		const data = boot();
		const company = chosen != null ? chosen : data.company || "";
		const name = String(company || "").trim();
		return name || data.fallback || data.title || FALLBACK;
	}

	function is_home() {
		if (!frappe.get_route) {
			return false;
		}
		const route = frappe.get_route() || [];
		const first = route[0] || "";
		return first === "" || first === "desktop";
	}

	function is_desktop_label(title) {
		const plain = String(title == null ? "" : title)
			.replace(/<[^>]*>/g, "")
			.trim();
		if (plain === "Desktop") {
			return true;
		}
		try {
			return typeof __ === "function" && plain === __("Desktop");
		} catch (error) {
			return false;
		}
	}

	function install_title_hook() {
		if (!frappe.utils || !frappe.utils.set_title || frappe.utils.set_title.__melliflous) {
			return;
		}
		const original = frappe.utils.set_title;
		function wrapped(title) {
			if (is_desktop_label(title)) {
				title = company_title();
			}
			return original.call(frappe.utils, title);
		}
		wrapped.__melliflous = true;
		frappe.utils.set_title = wrapped;
	}

	function notify(message, indicator) {
		if (typeof frappe.show_alert === "function") {
			frappe.show_alert({ message: message, indicator: indicator });
			return;
		}
		if (frappe.ui && typeof frappe.ui.toast === "function") {
			frappe.ui.toast({
				message: message,
				type: indicator === "red" ? "error" : "success",
			});
		}
	}

	function remember(company) {
		chosen = company;
		const data = boot();
		data.company = company;
		data.title = company;
		if (frappe.boot) {
			frappe.boot.melliflous_branding = data;
		}
		if (frappe.defaults && frappe.defaults.set_user_default_local) {
			frappe.defaults.set_user_default_local("company", company);
		}
		if (frappe.boot && frappe.boot.user && frappe.boot.user.defaults) {
			frappe.boot.user.defaults.company = company;
		}
		if (frappe.sys_defaults) {
			frappe.sys_defaults.company = company;
		}
		if (frappe.boot && frappe.boot.sysdefaults) {
			frappe.boot.sysdefaults.company = company;
		}
	}

	function refresh_title() {
		const title = company_title();
		document.querySelectorAll("p.desktop-navbar-title").forEach((node) => {
			node.textContent = title;
			node.classList.add("melliflous-title");
		});
		if (is_home() && document.title !== title && frappe.utils && frappe.utils.set_title) {
			frappe.utils.set_title(title);
		}
	}

	function ensure_select() {
		if (select && select.isConnected) {
			return select;
		}
		select = document.querySelector("select.melliflous-company-switch:not(.melliflous-division-switch)");
		if (select) {
			return select;
		}
		select = document.createElement("select");
		select.className = "melliflous-company-switch";
		select.setAttribute("aria-label", __("Company"));
		select.addEventListener("change", on_change);
		return select;
	}

	function fill_select(node) {
		const companies = boot().companies || [];
		const signature = companies.join("\n");
		const selected = chosen != null ? chosen : boot().company || "";
		if (node.dataset.companies === signature && node.value === (selected || "")) {
			return;
		}
		node.dataset.companies = signature;
		node.replaceChildren();
		if (!selected) {
			const blank = document.createElement("option");
			blank.value = "";
			blank.textContent = __("Select company");
			node.appendChild(blank);
		}
		companies.forEach((name) => {
			const option = document.createElement("option");
			option.value = name;
			option.textContent = name;
			node.appendChild(option);
		});
		node.value = selected || "";
	}

	function ensure_division_select() {
		if (divisionSelect && divisionSelect.isConnected) {
			return divisionSelect;
		}
		divisionSelect = document.querySelector("select.melliflous-division-switch");
		if (divisionSelect) {
			return divisionSelect;
		}
		divisionSelect = document.createElement("select");
		divisionSelect.className = "melliflous-division-switch";
		divisionSelect.setAttribute("aria-label", __("Division"));
		divisionSelect.addEventListener("change", on_division);
		return divisionSelect;
	}

	function same_company(left, right) {
		return String(left || "").trim() === String(right || "").trim();
	}

	function divisions_for(company) {
		return (boot().divisions || []).filter((row) => row && same_company(row.company, company));
	}

	function load_divisions(company) {
		if (divisionLoad || !frappe.call) {
			return;
		}
		divisionLoad = frappe
			.call({
				method: "melliflous_branding.division_records.desk_divisions",
				args: { company: company || "" },
			})
			.then((response) => {
				const message = (response && response.message) || {};
				const data = boot();
				data.divisions = message.divisions || [];
				if (message.division) {
					data.division = message.division;
				}
				if (frappe.boot) {
					frappe.boot.melliflous_branding = data;
				}
				mount();
			})
			.catch(() => {
				divisionLoad = null;
			});
	}

	function fill_division(node, company) {
		const rows = divisions_for(company);
		const selected = chosenDivision != null ? chosenDivision : boot().division || "";
		node.dataset.filling = "1";
		node.replaceChildren();
		rows.forEach((row) => {
			const option = document.createElement("option");
			option.value = row.name;
			option.textContent = row.division_name || row.name;
			node.appendChild(option);
		});
		if (!rows.length) {
			const blank = document.createElement("option");
			blank.value = "";
			blank.textContent = __("No division");
			node.appendChild(blank);
		}
		node.value = rows.some((row) => row.name === selected) ? selected : (rows[0] && rows[0].name) || "";
		node.dataset.filling = "";
	}

	function paint_pills(bar, company) {
		let companyPill = bar.querySelector(".melliflous-company-pill");
		let divisionPill = bar.querySelector(".melliflous-division-pill");
		if (!companyPill) {
			companyPill = document.createElement("span");
			companyPill.className = "melliflous-context-pill melliflous-company-pill";
			bar.prepend(companyPill);
		}
		if (!divisionPill) {
			divisionPill = document.createElement("span");
			divisionPill.className = "melliflous-context-pill melliflous-division-pill";
			companyPill.after(divisionPill);
		}
		companyPill.textContent = company || __("Company");
		companyPill.style.background = "";
		companyPill.hidden = true;
		const rows = divisions_for(company);
		const selected = divisionSelect ? divisionSelect.value : "";
		const match = rows.find((row) => row.name === selected);
		divisionPill.textContent = match
			? match.abbreviation || match.division_name || match.name
			: __("Division");
		divisionPill.style.background = "";
		divisionPill.hidden = false;
		paint_chip(company, match);
	}

	function is_narrow() {
		const query = window.matchMedia && window.matchMedia(NARROW_QUERY).matches;
		const phone = document.body && document.body.classList.contains("has-mobile-nav");
		return Boolean(query || phone);
	}

	function ensure_chip(bar) {
		let chip = bar.querySelector(".melliflous-context-chip");
		if (chip) {
			return chip;
		}
		chip = document.createElement("button");
		chip.type = "button";
		chip.className = "melliflous-context-chip";
		chip.setAttribute("aria-haspopup", "dialog");
		chip.setAttribute("aria-controls", "melliflous-context-sheet");
		chip.setAttribute("aria-expanded", "false");
		const pill = document.createElement("span");
		pill.className = "melliflous-chip-pill";
		const copy = document.createElement("span");
		copy.className = "melliflous-chip-copy";
		const companyLine = document.createElement("span");
		companyLine.className = "melliflous-chip-company";
		const divisionLine = document.createElement("span");
		divisionLine.className = "melliflous-chip-division";
		copy.append(companyLine, divisionLine);
		const caret = document.createElement("span");
		caret.className = "melliflous-chip-caret";
		caret.setAttribute("aria-hidden", "true");
		chip.append(pill, copy, caret);
		chip.addEventListener("click", open_sheet);
		bar.appendChild(chip);
		return chip;
	}

	function ensure_sheet() {
		let sheet = document.getElementById("melliflous-context-sheet");
		if (sheet) {
			return sheet;
		}
		sheet = document.createElement("div");
		sheet.id = "melliflous-context-sheet";
		sheet.className = "melliflous-context-sheet";
		sheet.hidden = true;
		const backdrop = document.createElement("button");
		backdrop.type = "button";
		backdrop.className = "melliflous-sheet-backdrop";
		backdrop.setAttribute("aria-label", __("Close"));
		backdrop.addEventListener("click", close_sheet);
		const panel = document.createElement("div");
		panel.className = "melliflous-sheet-panel";
		panel.setAttribute("role", "dialog");
		panel.setAttribute("aria-modal", "true");
		panel.setAttribute("aria-labelledby", "melliflous-sheet-title");
		const handle = document.createElement("div");
		handle.className = "melliflous-sheet-handle";
		const title = document.createElement("h2");
		title.id = "melliflous-sheet-title";
		title.className = "melliflous-sheet-title";
		title.textContent = __("Company and division");
		const fields = document.createElement("div");
		fields.className = "melliflous-sheet-fields";
		const done = document.createElement("button");
		done.type = "button";
		done.className = "melliflous-sheet-done";
		done.textContent = __("Done");
		done.addEventListener("click", close_sheet);
		panel.append(handle, title, fields, done);
		sheet.append(backdrop, panel);
		document.body.appendChild(sheet);
		return sheet;
	}

	function open_sheet() {
		if (!is_narrow()) {
			return;
		}
		const sheet = ensure_sheet();
		sheet.hidden = false;
		const chip = document.querySelector(".melliflous-context-chip");
		if (chip) {
			chip.setAttribute("aria-expanded", "true");
		}
		const first = sheet.querySelector("select");
		if (first) {
			first.focus();
		}
	}

	function close_sheet() {
		const sheet = document.getElementById("melliflous-context-sheet");
		if (sheet) {
			sheet.hidden = true;
		}
		const chip = document.querySelector(".melliflous-context-chip");
		if (chip) {
			chip.setAttribute("aria-expanded", "false");
		}
	}

	function paint_chip(company, match) {
		const chip = document.querySelector(".melliflous-context-chip");
		if (!chip) {
			return;
		}
		const pill = chip.querySelector(".melliflous-chip-pill");
		const companyLine = chip.querySelector(".melliflous-chip-company");
		const divisionLine = chip.querySelector(".melliflous-chip-division");
		const abbreviation = match ? match.abbreviation || match.division_name || "DV" : "DV";
		pill.textContent = abbreviation;
		pill.style.background = "";
		companyLine.textContent = company || __("Company");
		divisionLine.textContent = match ? match.division_name || match.name : __("Division");
		chip.setAttribute(
			"aria-label",
			__("Company and division") + ": " + companyLine.textContent + ", " + divisionLine.textContent
		);
	}

	function layout_switcher(bar) {
		if (!bar) {
			return;
		}
		const narrow = is_narrow();
		document.body.classList.toggle("melliflous-narrow", narrow);
		const chip = ensure_chip(bar);
		const sheet = ensure_sheet();
		const fields = sheet.querySelector(".melliflous-sheet-fields");
		const companyLabel = document.querySelector(".melliflous-company-label");
		const divisionLabel = document.querySelector(".melliflous-division-label");
		bar.classList.toggle("is-compact", narrow);
		const nodes = [companyLabel, select, divisionLabel, divisionSelect];
		if (narrow) {
			chip.hidden = false;
			nodes.forEach((node) => {
				if (node && fields && node.parentElement !== fields) {
					fields.appendChild(node);
				}
			});
		} else {
			chip.hidden = true;
			close_sheet();
			nodes.forEach((node) => {
				if (node && node.parentElement !== bar) {
					bar.appendChild(node);
				}
			});
		}
		const company = select ? select.value : boot().company || "";
		const rows = divisions_for(company);
		const selected = divisionSelect ? divisionSelect.value : "";
		const match = rows.find((row) => row.name === selected);
		paint_chip(company, match);
	}

	function save_context(company, division, previousCompany, previousDivision) {
		if (!company || saving) {
			return;
		}
		saving = true;
		if (select) select.disabled = true;
		if (divisionSelect) divisionSelect.disabled = true;
		frappe
			.call({
				method: "melliflous_branding.api.set_desk_context",
				args: { company: company, division: division || "" },
			})
			.then((response) => {
				if (!response || response.exc) {
					throw new Error("set_desk_context failed");
				}
				window.location.reload();
			})
			.catch(() => {
				if (select) select.value = previousCompany || "";
				if (divisionSelect) divisionSelect.value = previousDivision || "";
				notify(__("Could not set the company and division"), "red");
				saving = false;
				if (select) select.disabled = false;
				if (divisionSelect) divisionSelect.disabled = false;
			});
	}

	function on_change() {
		const next = select ? select.value : "";
		const previous = chosen != null ? chosen : boot().company || "";
		if (!next || next === previous) {
			return;
		}
		save_context(next, "", previous, chosenDivision != null ? chosenDivision : boot().division || "");
	}

	function on_division() {
		if (divisionSelect && divisionSelect.dataset.filling) {
			return;
		}
		const company = select ? select.value : boot().company || "";
		const next = divisionSelect ? divisionSelect.value : "";
		const previous = chosenDivision != null ? chosenDivision : boot().division || "";
		if (!next || next === previous) {
			return;
		}
		save_context(company, next, company, previous);
	}

	function visible_page_head() {
		const heads = Array.from(document.querySelectorAll(".page-head"));
		for (const head of heads) {
			if (head.closest(".hide, .hidden")) {
				continue;
			}
			if (head.offsetParent !== null || head.getClientRects().length) {
				return head;
			}
		}
		return null;
	}

	function clear_empty_slots(keep) {
		document.querySelectorAll(".melliflous-company-slot").forEach((slot) => {
			if (slot !== keep) {
				slot.remove();
			}
		});
	}

	function top_bar() {
		return (
			document.querySelector(".desktop-navbar") ||
			document.querySelector("header.navbar .container") ||
			document.querySelector("header.navbar")
		);
	}

	function mount() {
		inject_switcher_style();
		const data = boot();
		const companyNames = data.companies || [];
		if (!(data.divisions || []).length) {
			load_divisions(data.company || companyNames[0] || "");
		}
		if (!companyNames.length && !(data.divisions || []).length) {
			if (select) {
				select.remove();
				select = null;
			}
			clear_empty_slots(null);
			refresh_title();
			return;
		}

		const node = ensure_select();
		fill_select(node);
		const divisionNode = ensure_division_select();
		const company = node.value || data.company || "";
		fill_division(divisionNode, company);

		const bar = context_bar(node, divisionNode, company);
		const navbar = top_bar();
		if (navbar) {
			bar.classList.add("melliflous-context-navbar", "desktop-navbar-title");
			const home = navbar.querySelector(":scope > .navbar-home");
			navbar.querySelectorAll("p.desktop-navbar-title").forEach((title) => title.remove());
			if (home) {
				home.after(bar);
			} else if (bar.parentElement !== navbar) {
				navbar.appendChild(bar);
			}
			clear_empty_slots(null);
			refresh_title();
			layout_switcher(bar);
			return;
		}

		node.classList.remove("desktop-navbar-title");
		const head = visible_page_head();
		if (!head) {
			return;
		}
		const container = head.querySelector(".container") || head;
		let slot = container.querySelector(":scope > .melliflous-company-slot");
		if (!slot) {
			slot = document.createElement("div");
			slot.className = "melliflous-company-slot";
			const row = container.querySelector(".page-head-content");
			if (row) {
				row.before(slot);
			} else {
				container.prepend(slot);
			}
		}
		slot.appendChild(bar);
		clear_empty_slots(slot);
		layout_switcher(bar);
	}

	function context_bar(companyNode, divisionNode, company) {
		let bar = companyNode.closest(".melliflous-context") || document.querySelector(".melliflous-context");
		if (!bar) {
			bar = document.createElement("div");
			bar.className = "melliflous-context";
		}
		let companyLabel = document.querySelector(".melliflous-company-label");
		if (!companyLabel) {
			companyLabel = document.createElement("span");
			companyLabel.className = "melliflous-context-label melliflous-company-label";
			companyLabel.textContent = __("Company");
			bar.appendChild(companyLabel);
		} else {
			companyLabel.classList.add("melliflous-company-label");
		}
		if (!bar.contains(companyNode) && !is_narrow()) bar.appendChild(companyNode);
		let divisionLabel = document.querySelector(".melliflous-division-label");
		if (!divisionLabel) {
			divisionLabel = document.createElement("span");
			divisionLabel.className = "melliflous-context-label melliflous-division-label";
			divisionLabel.textContent = __("Division");
			bar.appendChild(divisionLabel);
		}
		if (!bar.contains(divisionNode) && !is_narrow()) bar.appendChild(divisionNode);
		paint_pills(bar, company);
		return bar;
	}

	function tone_for(label) {
		const tones = boot().tones || {};
		const text = String(label || "")
			.replace(/\s+/g, " ")
			.trim();
		if (!text) {
			return null;
		}
		if (tones[text]) {
			return tones[text];
		}
		const folded = text.toLowerCase();
		for (const key in tones) {
			if (Object.prototype.hasOwnProperty.call(tones, key) && key.toLowerCase() === folded) {
				return tones[key];
			}
		}
		return null;
	}

	function paint_tiles(root) {
		const scope = root && root.querySelectorAll ? root : document.querySelector(".desktop-container");
		if (!scope || !scope.querySelectorAll) {
			return;
		}
		scope.querySelectorAll(".desktop-icon, .module-folder-app").forEach((tile) => {
			const label_node = tile.matches(".module-folder-app")
				? tile.querySelector(".module-folder-label")
				: tile.querySelector(".icon-title");
			const tone = tone_for(label_node ? label_node.textContent : "");
			if (tone) {
				tile.setAttribute("data-melliflous-tone", tone);
			} else {
				tile.removeAttribute("data-melliflous-tone");
			}
		});
	}

	function watch_tiles() {
		const root = document.querySelector(".desktop-container");
		if (!root || root.dataset.melliflousWatch === "1") {
			paint_tiles(root);
			return;
		}
		root.dataset.melliflousWatch = "1";
		const observer = new MutationObserver(() => paint_tiles(root));
		observer.observe(root, { childList: true, subtree: true });
		paint_tiles(root);
	}

	function ensure_pwa_tags() {
		if (document.head.querySelector("[data-melliflous-pwa]")) {
			return;
		}
		const data = boot();
		const icon = data.icon || "/files/melliflous_icon_512.png";
		const fallback = data.fallback_icon || "/assets/melliflous_branding/images/melliflous_icon_512.png";
		const manifest = data.manifest || "/assets/melliflous_branding/manifest.json";
		const name = data.home_screen_name || FALLBACK;
		[icon, fallback].forEach((href) => {
			const link = document.createElement("link");
			link.rel = "apple-touch-icon";
			link.sizes = "512x512";
			link.href = href;
			link.setAttribute("data-melliflous-pwa", "1");
			document.head.appendChild(link);
		});
		const manifest_link = document.createElement("link");
		manifest_link.rel = "manifest";
		manifest_link.href = manifest;
		manifest_link.setAttribute("data-melliflous-pwa", "1");
		document.head.appendChild(manifest_link);
		if (!document.querySelector('meta[name="apple-mobile-web-app-title"]')) {
			const meta = document.createElement("meta");
			meta.name = "apple-mobile-web-app-title";
			meta.content = name;
			meta.setAttribute("data-melliflous-pwa", "1");
			document.head.appendChild(meta);
		}
	}

	function schedule() {
		mount();
		watch_tiles();
		refresh_title();
		if (window.requestAnimationFrame) {
			requestAnimationFrame(() => {
				mount();
				watch_tiles();
			});
		}
	}

	function start() {
		inject_switcher_style();
		install_title_hook();
		ensure_pwa_tags();
		schedule();
		$(document).on("desktop_screen.melliflous", schedule);
		$(document).on("page-change.melliflous", schedule);
		if (window.matchMedia) {
			const query = window.matchMedia(NARROW_QUERY);
			const on_width = function () {
				schedule();
			};
			if (query.addEventListener) {
				query.addEventListener("change", on_width);
			} else if (query.addListener) {
				query.addListener(on_width);
			}
		}
		document.addEventListener("keydown", function (event) {
			if (event.key === "Escape") {
				close_sheet();
			}
		});
		if (frappe.router && frappe.router.on) {
			frappe.router.on("change", schedule);
		}
	}

	install_title_hook();
	window.melliflous_branding = { company_title, mount, paint_tiles };

	if (window.jQuery) {
		jQuery(start);
	} else if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", start);
	} else {
		start();
	}
})();
