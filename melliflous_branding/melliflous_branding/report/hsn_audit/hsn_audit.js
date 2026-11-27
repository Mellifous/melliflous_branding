frappe.query_reports["HSN Audit"] = {
	filters: [
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "problem",
			label: __("Problem"),
			fieldtype: "Select",
			options: "\nMissing HSN\nShort HSN\nFormat\nNot in master\nCategory\nTax rate\nTax missing\nImprecise",
		},
	],
};
