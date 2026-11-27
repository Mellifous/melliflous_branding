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
		const tones = {
			achievement_pct: data.achievement_tone,
			days_since_order: data.order_tone,
			next_visit_due: data.visit_tone,
			overdue_amount: data.overdue_tone,
			reasons: data.row_tone,
		};
		const tone = tones[column.fieldname];
		if (!tone || tone === "neutral") {
			return formatted;
		}
		const colour = { green: "green", amber: "orange", red: "red" }[tone] || "gray";
		const text = formatted || "—";
		return `<span class="indicator-pill ${colour}">${text}</span>`;
	},
};
