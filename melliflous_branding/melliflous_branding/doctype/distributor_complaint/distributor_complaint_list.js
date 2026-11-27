frappe.listview_settings["Distributor Complaint"] = {
	get_indicator(doc) {
		const colours = {
			Open: "red",
			"In Progress": "orange",
			Resolved: "green",
			Closed: "gray",
		};
		const colour = colours[doc.status] || "gray";
		return [__(doc.status || "Open"), colour, "status,=," + (doc.status || "Open")];
	},
};
