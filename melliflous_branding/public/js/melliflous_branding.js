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
	let chosen = null;
	let chosenDivision = null;
	let select = null;
	let divisionSelect = null;
	let saving = false;

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
		select = document.querySelector("select.melliflous-company-switch");
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
		divisionSelect.className = "melliflous-company-switch melliflous-division-switch";
		divisionSelect.setAttribute("aria-label", __("Division"));
		divisionSelect.addEventListener("change", on_division);
		return divisionSelect;
	}

	function divisions_for(company) {
		return (boot().divisions || []).filter((row) => row && row.company === company);
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
		companyPill.style.background = "#C8102E";
		const rows = divisions_for(company);
		const selected = divisionSelect ? divisionSelect.value : "";
		const match = rows.find((row) => row.name === selected);
		divisionPill.textContent = match ? match.division_name || match.name : __("Division");
		divisionPill.style.background = (match && match.colour) || "#1F9D55";
		divisionPill.hidden = !match;
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

	function mount() {
		const data = boot();
		const companyNames = data.companies || [];
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
		if (is_home()) {
			const navbar = document.querySelector(".desktop-navbar");
			if (!navbar) {
				return;
			}
			bar.classList.add("melliflous-context-navbar");
			const home = navbar.querySelector(".navbar-home");
			navbar.querySelectorAll("p.desktop-navbar-title").forEach((title) => title.remove());
			if (home) {
				home.after(bar);
			} else if (bar.parentElement !== navbar) {
				navbar.prepend(bar);
			}
			clear_empty_slots(null);
			refresh_title();
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
	}

	function context_bar(companyNode, divisionNode, company) {
		let bar = companyNode.closest(".melliflous-context");
		if (!bar) {
			bar = document.createElement("div");
			bar.className = "melliflous-context";
		}
		if (!bar.querySelector(".melliflous-context-label")) {
			const companyLabel = document.createElement("span");
			companyLabel.className = "melliflous-context-label";
			companyLabel.textContent = __("Company");
			bar.appendChild(companyLabel);
		}
		if (!bar.contains(companyNode)) bar.appendChild(companyNode);
		if (!bar.querySelector(".melliflous-division-label")) {
			const divisionLabel = document.createElement("span");
			divisionLabel.className = "melliflous-context-label melliflous-division-label";
			divisionLabel.textContent = __("Division");
			bar.appendChild(divisionLabel);
		}
		if (!bar.contains(divisionNode)) bar.appendChild(divisionNode);
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
		install_title_hook();
		ensure_pwa_tags();
		schedule();
		$(document).on("desktop_screen.melliflous", schedule);
		$(document).on("page-change.melliflous", schedule);
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
