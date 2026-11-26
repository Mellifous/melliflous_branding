frappe.query_reports["Customer Target vs Achievement"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("company"),
			reqd: 1,
		},
		{
			fieldname: "period_type",
			label: __("Period Type"),
			fieldtype: "Select",
			options: "\nMonthly\nQuarterly",
			on_change() {
				const report = frappe.query_report;
				const period = report.get_filter_value("period_type");
				const day = report.get_filter_value("from_date") || frappe.datetime.get_today();
				if (!period) {
					return;
				}
				frappe.call({
					method: "melliflous_branding.target_records.period_dates",
					args: { period_type: period, day: day },
					callback(response) {
						if (!response.message) {
							return;
						}
						report.set_filter_value("from_date", response.message.from_date);
						report.set_filter_value("to_date", response.message.to_date);
					},
				});
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
			default: frappe.datetime.month_end(),
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "sales_person",
			label: __("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nAchieved\nNot Achieved\nIn Progress",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		if (!data) {
			return default_formatter(value, row, column, data);
		}
		if (data.is_total) {
			if (column.fieldname === "customer") {
				return `<b>${__("Total")}</b>`;
			}
			return `<b>${default_formatter(value, row, column, data)}</b>`;
		}
		const formatted = default_formatter(value, row, column, data);
		if (column.fieldname === "achievement_pct" || column.fieldname === "status") {
			const color = data.colour || "red";
			if (column.fieldname === "status" && !data.status) {
				return formatted;
			}
			return `<span class="indicator-pill ${color}">${formatted}</span>`;
		}
		return formatted;
	},
};
