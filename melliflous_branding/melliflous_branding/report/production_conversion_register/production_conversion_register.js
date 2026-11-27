frappe.query_reports["Production Conversion Register"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("company"),
		},
		{
			fieldname: "division",
			label: __("Division"),
			fieldtype: "Link",
			options: "Division",
			default: frappe.defaults.get_user_default("division"),
			get_query() {
				const company = frappe.query_report.get_filter_value("company");
				return { filters: company ? { company, is_active: 1 } : { is_active: 1 } };
			},
		},
		{
			fieldname: "recipe",
			label: __("Recipe"),
			fieldtype: "Link",
			options: "Recipe",
			get_query() {
				const company = frappe.query_report.get_filter_value("company");
				return { filters: company ? { company } : {} };
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "include_cancelled",
			label: __("Include cancelled"),
			fieldtype: "Check",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		const shown = default_formatter(value, row, column, data);
		if (!data || value == null || value === "") {
			return shown;
		}
		if (column.fieldname === "loss_vs_expected" && Number(value) > 0) {
			return `<span style="color:#8d1d1d;font-weight:700">${shown}</span>`;
		}
		if (column.fieldname === "yield_pct" && Number(value) < 100) {
			return `<span style="color:#9a6700;font-weight:700">${shown}</span>`;
		}
		return shown;
	},
};
