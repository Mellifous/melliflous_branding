// Red pill on the Customer list. Billing status is not the Disabled flag.
frappe.listview_settings["Customer"] = frappe.listview_settings["Customer"] || {};
frappe.listview_settings["Customer"].add_fields = ["custom_billing_status"].concat(
	frappe.listview_settings["Customer"].add_fields || []
);
frappe.listview_settings["Customer"].get_indicator = function (doc) {
	if (doc.custom_billing_status === "Blacklisted") {
		return [__("Blacklisted"), "red", "custom_billing_status,=,Blacklisted"];
	}
	if (doc.custom_billing_status === "Blocked") {
		return [__("Blocked"), "red", "custom_billing_status,=,Blocked"];
	}
};
