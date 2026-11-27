frappe.ui.form.on("Distributor Complaint", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.complaint_date) {
			frm.set_value("complaint_date", frappe.datetime.get_today());
		}
		set_credit_note_query(frm);
	},
	refresh(frm) {
		set_credit_note_query(frm);
	},
	distributor(frm) {
		set_credit_note_query(frm);
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
				if (!frm.doc.assigned_to && message.account_manager) {
					frm.set_value("assigned_to", message.account_manager);
				}
				if (message.distributor_profile) {
					frm.set_value("distributor_profile", message.distributor_profile);
				}
			},
		});
	},
});

function set_credit_note_query(frm) {
	frm.set_query("credit_note", () => {
		const filters = { docstatus: 1, is_return: 1 };
		if (frm.doc.distributor) {
			filters.customer = frm.doc.distributor;
		}
		if (frm.doc.company) {
			filters.company = frm.doc.company;
		}
		return { filters };
	});
}
