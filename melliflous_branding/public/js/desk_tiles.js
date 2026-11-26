// Quick Actions tiles. A separate file so a cached copy of quick_actions.js
// cannot keep the old list rows as the only entry points. The workspace that
// actually opens is /desk/melliflous-branding/quick-actions, route
// ["Workspaces", "Quick Actions"].
(function () {
	function el(tag, className, text) {
		const node = document.createElement(tag);
		if (className) node.className = className;
		if (text != null) node.textContent = text;
		return node;
	}

	function onQuickActions() {
		const route = (window.frappe && frappe.get_route && frappe.get_route()) || [];
		if (route[0] === "Workspaces" && route[route.length - 1] === "Quick Actions") return true;
		return (window.location.pathname || "").indexOf("/quick-actions") !== -1;
	}

	function workspaceBody() {
		const workspace = window.frappe && frappe.workspace;
		if (workspace && workspace._page && workspace._page.name === "Quick Actions" && workspace.body) {
			const node = workspace.body.get ? workspace.body.get(0) : workspace.body;
			if (node) return node;
		}
		const page = document.getElementById("page-Workspaces");
		if (page) {
			const section = page.querySelector(".layout-main-section");
			if (section) return section;
		}
		return null;
	}

	function tile(href, label, hint, color) {
		const link = el("a", "melliflous-tile");
		link.href = href;
		link.style.display = "flex";
		link.style.flexDirection = "column";
		link.style.justifyContent = "flex-end";
		link.style.minHeight = "140px";
		link.style.padding = "16px";
		link.style.borderRadius = "18px";
		link.style.background = color;
		link.style.color = "#fff";
		link.style.textDecoration = "none";
		link.style.boxSizing = "border-box";
		const title = el("span", "melliflous-tile-label", label);
		title.style.fontSize = "1.35rem";
		title.style.fontWeight = "700";
		const sub = el("span", "melliflous-tile-hint", hint);
		sub.style.marginTop = "4px";
		sub.style.fontSize = "1rem";
		link.appendChild(title);
		link.appendChild(sub);
		return link;
	}

	function buildTiles() {
		const wrap = el("div", "melliflous-tiles");
		const narrow = window.innerWidth < 560;
		wrap.style.display = "grid";
		wrap.style.gridTemplateColumns = narrow ? "1fr" : "1fr 1fr";
		wrap.style.gap = "12px";
		wrap.style.margin = "8px 16px 16px";
		wrap.appendChild(tile("/raven", __("Team Chat"), __("Message the team"), "#1f4d3a"));
		wrap.appendChild(tile("/desk/team-files", __("Team Files"), __("Share a file"), "#0e8f8a"));
		return wrap;
	}

	function hideShortcutRows(body) {
		const wanted = { "Team Chat": true, "Team Files": true };
		body.querySelectorAll(".ce-block, .shortcut-widget-box, .widget").forEach((node) => {
			if (node.closest(".melliflous-tiles")) return;
			const named = (node.getAttribute("shortcut_name") || node.getAttribute("aria-label") || "").trim();
			const title = node.querySelector(".widget-title-text, .widget-title");
			const label = named || (title ? title.textContent.replace(/\s+/g, " ").trim() : "");
			if (!wanted[label]) return;
			const block = node.closest(".ce-block") || node;
			block.style.display = "none";
		});
	}

	function placeTiles() {
		if (!onQuickActions()) return;
		const body = workspaceBody();
		if (!body) return;
		if (!body.querySelector(".melliflous-tiles")) {
			const tiles = buildTiles();
			const editor = body.querySelector(".editor-js-container, .editor, #editorjs");
			if (editor && editor.parentElement) editor.parentElement.insertBefore(tiles, editor);
			else body.prepend(tiles);
		}
		hideShortcutRows(body);
	}

	let timer = 0;
	function schedule() {
		window.clearTimeout(timer);
		timer = window.setTimeout(placeTiles, 50);
	}

	if (window.MutationObserver && document.body) {
		new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
	}
	if (window.jQuery) {
		window.jQuery(document).on("page-change", schedule);
	}
	schedule();
})();
