frappe.query_reports["Distributor Follow-up"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("company"),
		},
		{
			fieldname: "account_manager",
			label: __("Account Manager"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "sales_person",
			label: __("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person",
		},
		{
			fieldname: "no_order_days",
			label: __("No order in days"),
			fieldtype: "Int",
			default: 30,
		},
		{
			fieldname: "include_inactive",
			label: __("Include inactive"),
			fieldtype: "Check",
		},
		{
			fieldname: "reason",
			label: __("Reason"),
			fieldtype: "Select",
			options: "\nVisit\nOrder\nTarget\nComplaint\nReceivable",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		if (!data) {
			return default_formatter(value, row, column, data);
		}
		const formatted = default_formatter(value, row, column, data);
		if (column.fieldname === "achievement_pct" && data.achievement_pct != null && Number(data.achievement_pct) < 70) {
			return `<span class="indicator-pill red">${formatted}</span>`;
		}
		if (column.fieldname === "reasons" && data.reasons) {
			const text = frappe.utils.escape_html ? frappe.utils.escape_html(String(data.reasons)) : formatted;
			return `<span class="text-danger">${text}</span>`;
		}
		return formatted;
	},
};
