frappe.pages["vans-360"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Vans 360"), single_column: true });
	placeVanMark(wrapper);
	const boot = (frappe.boot && frappe.boot.melliflous_branding) || {};
	page.company = page.add_field({
		fieldname: "company",
		label: __("Company"),
		fieldtype: "Link",
		options: "Company",
		default: boot.company || "",
		change: () => load(),
	});
	page.division = page.add_field({
		fieldname: "division",
		label: __("Division"),
		fieldtype: "Link",
		options: "Division",
		default: boot.division || "",
		change: () => load(),
	});
	page.preset = page.add_field({
		fieldname: "preset",
		label: __("Period"),
		fieldtype: "Select",
		options: "Today\nWeek\nMTD\nCustom",
		default: "MTD",
		change: () => load(),
	});
	const body = $('<div class="vans-360"></div>').appendTo(page.main);
	page.add_inner_button(__("Excel"), () => download("csv"));
	page.add_inner_button(__("PDF"), () => download("html"));
	page.add_inner_button(__("Van list"), () => {
		window.location.href = "/desk/melliflous-branding/van";
	});
	page.add_inner_button(__("Daily reports"), () => {
		window.location.href = "/desk/melliflous-branding/van-daily-report";
	});

	function load() {
		frappe.call({
			method: "melliflous_branding.van_records.vans_dashboard",
			args: {
				company: page.company.get_value(),
				division: page.division.get_value(),
				preset: page.preset.get_value(),
			},
			callback(response) {
				render(body, (response && response.message) || {});
			},
		});
	}

	function download(fileFormat) {
		frappe.call({
			method: "melliflous_branding.van_records.van_report_download",
			args: {
				kind: "Detailed sales",
				company: page.company.get_value(),
				division: page.division.get_value(),
				preset: page.preset.get_value(),
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

	load();
};

function placeVanMark(wrapper) {
	const title = wrapper.querySelector(".page-title .title-text, .title-text");
	if (!title || title.querySelector(".vans-360-mark")) return;
	const mark = document.createElement("span");
	mark.className = "vans-360-mark";
	mark.setAttribute("aria-hidden", "true");
	mark.style.cssText = "display:inline-flex;width:28px;height:28px;margin-right:8px;vertical-align:middle;color:#c8102e";
	const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
	svg.setAttribute("viewBox", "0 0 24 24");
	svg.setAttribute("width", "28");
	svg.setAttribute("height", "28");
	svg.setAttribute("fill", "none");
	svg.setAttribute("stroke", "currentColor");
	svg.setAttribute("stroke-width", "1.8");
	svg.setAttribute("stroke-linecap", "round");
	svg.setAttribute("stroke-linejoin", "round");
	const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
	path.setAttribute(
		"d",
		"M3 7h11v8H3V7zm11 2h4l3 3v3h-7V9zM6 18a2 2 0 1 0 .01-4A2 2 0 0 0 6 18zm11 0a2 2 0 1 0 .01-4A2 2 0 0 0 17 18z"
	);
	svg.appendChild(path);
	mark.appendChild(svg);
	title.prepend(mark);
}

function render(host, data) {
	const overview = data.overview || {};
	const cards = ["sales", "target", "percent", "run_rate", "vans_logged_today", "strike", "missed_van_days", "mismatches", "new_outlets"]
		.map((key) => `<div><strong>${frappe.utils.escape_html(key.split("_").join(" "))}</strong><div>${frappe.utils.escape_html(String(overview[key] == null ? "" : overview[key]))}</div></div>`)
		.join("");
	host.html(
		`<section class="vans-cards" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px">${cards}</section>` +
			section("SR leaderboard", data.leaderboard, ["worked_by", "sales", "target", "days"]) +
			section("Exceptions", data.exceptions, ["van", "kind", "date"]) +
			section("Beats", data.beats, ["beat", "van", "last_worked", "overdue"]) +
			section("Reported vs invoiced", data.reported_vs_invoiced, ["date", "van", "reported", "invoiced", "unbilled"]) +
			section("Cash", (data.cash && data.cash.balances) || [], ["holder", "balance"]) +
			section("Transfers", (data.cash && data.cash.transfers) || [], ["posting_date", "from_holder", "to_holder", "amount"])
	);
}

function section(title, rows, keys) {
	const body = (rows || [])
		.slice(0, 40)
		.map((row) => `<tr>${keys.map((key) => `<td>${frappe.utils.escape_html(String(row[key] ?? ""))}</td>`).join("")}</tr>`)
		.join("");
	return `<h3>${frappe.utils.escape_html(title)}</h3><table class="table table-bordered"><thead><tr>${keys
		.map((key) => `<th>${frappe.utils.escape_html(key)}</th>`)
		.join("")}</tr></thead><tbody>${body}</tbody></table>`;
}
