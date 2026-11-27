frappe.ui.form.on("Distributor Profile", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.customer) {
			return;
		}
		frm.add_custom_button(__("Distributor 360"), () => {
			frappe.route_options = { distributor: frm.doc.customer, company: frm.doc.company };
			frappe.set_route("distributor-360");
		});
	},
});
