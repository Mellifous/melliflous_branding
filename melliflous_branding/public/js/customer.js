// Billing status on the Customer form. The pill is red for Blocked and Blacklisted.
// Disabled stays a separate checkbox. Aadhaar rows do not keep a number.
frappe.ui.form.on("Customer", {
	refresh(frm) {
		const status = frm.doc.custom_billing_status;
		if (status === "Blocked" || status === "Blacklisted") {
			frm.page.set_indicator(__(status), "red");
		}
	},
	custom_billing_status(frm) {
		if ((frm.doc.custom_billing_status || "Active") === "Active" && frm.doc.custom_block_reason) {
			frm.set_value("custom_block_reason", "");
		}
	},
});

frappe.ui.form.on("Customer Document", {
	document_type(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.document_type === "Aadhaar" && row.document_no) {
			frappe.model.set_value(cdt, cdn, "document_no", "");
			frappe.show_alert({
				message: __("Aadhaar numbers are not stored. Attach a masked copy."),
				indicator: "orange",
			});
		}
	},
});
