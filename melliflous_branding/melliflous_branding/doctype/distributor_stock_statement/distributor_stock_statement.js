frappe.ui.form.on("Distributor Stock Statement", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_user_default("company"));
		}
		if (frm.is_new() && !frm.doc.statement_month) {
			frm.set_value("statement_month", frappe.datetime.month_start());
		}
	},
	refresh(frm) {
		if (!frm.doc.distributor || !frm.doc.company || !frm.doc.statement_month) {
			return;
		}
		frm.add_custom_button(__("Fill Items"), () => fill_items(frm));
	},
	distributor(frm) {
		pull_profile(frm);
	},
});

frappe.ui.form.on("Distributor Stock Statement Item", {
	opening_qty(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "opening_edited", 1);
		refresh_closing(cdt, cdn);
	},
	secondary_qty(frm, cdt, cdn) {
		refresh_closing(cdt, cdn);
	},
	rate(frm, cdt, cdn) {
		refresh_closing(cdt, cdn);
	},
	closing_edited(frm, cdt, cdn) {
		refresh_closing(cdt, cdn);
	},
	closing_qty(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.closing_edited) {
			return;
		}
		set_values(cdt, cdn, row.closing_qty);
	},
});

function pull_profile(frm) {
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
			if (message.distributor_profile) {
				frm.set_value("distributor_profile", message.distributor_profile);
			}
		},
	});
}

function fill_items(frm) {
	const replace = () => {
		frappe
			.call({
				method: "melliflous_branding.distributor_records.prefill_statement",
				args: {
					distributor: frm.doc.distributor,
					company: frm.doc.company,
					statement_month: frm.doc.statement_month,
				},
			})
			.then((response) => {
				const items = (response.message && response.message.items) || [];
				frm.clear_table("items");
				items.forEach((row) => frm.add_child("items", row));
				frm.refresh_field("items");
				if (!items.length) {
					frappe.show_alert({
						message: __("Nothing to fill. Add items by hand."),
						indicator: "orange",
					});
				}
			})
			.catch((error) => {
				frappe.msgprint({
					title: __("Could not fill items"),
					message: error_text(error),
					indicator: "red",
				});
			});
	};
	if ((frm.doc.items || []).length) {
		frappe.confirm(
			__("Replace the rows with last month's closing and this month's invoices?"),
			replace
		);
		return;
	}
	replace();
}

function refresh_closing(cdt, cdn) {
	const row = locals[cdt][cdn];
	if (row.closing_edited) {
		set_values(cdt, cdn, row.closing_qty);
		return;
	}
	const closing = round_qty(
		(Number(row.opening_qty) || 0) + (Number(row.primary_qty) || 0) - (Number(row.secondary_qty) || 0)
	);
	frappe.model.set_value(cdt, cdn, "closing_qty", closing);
	set_values(cdt, cdn, closing);
}

function set_values(cdt, cdn, closing) {
	const row = locals[cdt][cdn];
	const rate = Number(row.rate) || 0;
	frappe.model.set_value(cdt, cdn, "closing_value", round_money((Number(closing) || 0) * rate));
	frappe.model.set_value(cdt, cdn, "secondary_value", round_money((Number(row.secondary_qty) || 0) * rate));
}

function round_qty(value) {
	return Math.round(value * 1000) / 1000;
}

function round_money(value) {
	return Math.round(value * 100) / 100;
}

function error_text(error) {
	const payload = (error && (error.responseJSON || error)) || {};
	if (payload._server_messages) {
		try {
			const messages = JSON.parse(payload._server_messages);
			const first = JSON.parse(messages[0]);
			if (first && first.message) {
				return String(first.message).replace(/<[^>]*>/g, "").trim();
			}
		} catch (ignored) {
			/* use the fallback below */
		}
	}
	if (payload.message) {
		return String(payload.message).replace(/<[^>]*>/g, "").trim();
	}
	if (error && error.message) {
		return String(error.message);
	}
	return __("Something went wrong. Please try again.");
}
