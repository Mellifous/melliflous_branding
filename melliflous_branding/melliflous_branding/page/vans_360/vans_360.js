frappe.pages["vans-360"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Vans 360"), single_column: true });
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

function render(host, data) {
	const overview = data.overview || {};
	const cards = ["sales", "target", "percent", "run_rate", "vans_logged_today", "strike", "missed_van_days", "mismatches", "new_outlets"]
		.map((key) => `<div><strong>${frappe.utils.escape_html(key.replaceAll("_", " "))}</strong><div>${frappe.utils.escape_html(String(overview[key] ?? ""))}</div></div>`)
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
