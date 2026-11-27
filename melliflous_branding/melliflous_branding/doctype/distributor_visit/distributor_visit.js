frappe.ui.form.on("Distributor Visit", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.visit_date) {
			frm.set_value("visit_date", frappe.datetime.get_today());
		}
	},
	distributor(frm) {
		if (!frm.doc.distributor) {
			return;
		}
		frappe.call({
			method: "melliflous_branding.distributor_records.profile_defaults",
			args: { customer: frm.doc.distributor },
			callback(response) {
				const message = response.message || {};
				if (!frm.doc.company && message.company) {
					frm.set_value("company", message.company);
				}
				if (!frm.doc.sales_person && message.sales_person) {
					frm.set_value("sales_person", message.sales_person);
				}
				if (!frm.doc.salesman && message.salesman) {
					frm.set_value("salesman", message.salesman);
				}
				if (message.distributor_profile) {
					frm.set_value("distributor_profile", message.distributor_profile);
				}
			},
		});
	},
});

frappe.ui.form.on("Distributor Visit Stock", {
	item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item || row.uom) {
			return;
		}
		frappe.db.get_value("Item", row.item, "stock_uom").then((response) => {
			const uom = response.message && response.message.stock_uom;
			if (uom) {
				frappe.model.set_value(cdt, cdn, "uom", uom);
			}
		});
	},
});
