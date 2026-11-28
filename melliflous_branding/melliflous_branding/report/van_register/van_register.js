frappe.query_reports["Van Register"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "division", label: __("Division"), fieldtype: "Link", options: "Division" },
		{
			fieldname: "kind",
			label: __("Report"),
			fieldtype: "Select",
			options: "Detailed sales\nVan summary\nSR\nBeat\nCollections\nCash transfers\nNew outlets",
			default: "Detailed sales",
		},
		{
			fieldname: "preset",
			label: __("Period"),
			fieldtype: "Select",
			options: "Today\nWeek\nMTD\nCustom",
			default: "MTD",
		},
	],
};
