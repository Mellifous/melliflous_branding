// Bulk action on the Sales Invoice list. The label is "Delete with reason"
// so a script that removes an item labelled exactly "Delete" leaves it alone.
// Who sees it is decided by the server on load, not by boot.
frappe.listview_settings["Sales Invoice"] = {
	onload(listview) {
		frappe
			.call({ method: "melliflous_branding.invoice_admin_records.may_delete_sales_invoice" })
			.then((response) => {
				const allowed = response && response.message && cint(response.message.allowed);
				if (!allowed || !listview.page || !listview.page.add_actions_menu_item) return;
				listview.page.add_actions_menu_item(
					__("Delete with reason"),
					() => deleteCheckedInvoices(listview),
					true,
					null,
					"trash-2",
					"red"
				);
			});
	},
};

function deleteCheckedInvoices(listview) {
	const docs = listview.get_checked_items ? listview.get_checked_items() : [];
	if (!docs.length) {
		frappe.msgprint(__("Select an invoice first."));
		return;
	}
	if (docs.some((row) => cint(row.docstatus) === 1)) {
		frappe.msgprint(__("Cancel this invoice before deleting it."));
		return;
	}
	const names = docs.map((row) => row.name).filter(Boolean);
	const dialog = new frappe.ui.Dialog({
		title: __("Delete with reason"),
		fields: [
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Reason for deletion"),
				reqd: 1,
			},
			{ fieldname: "server_error", fieldtype: "HTML" },
		],
		primary_action_label: __("Delete"),
		primary_action(values) {
			const reason = ((values && values.reason) || "").replace(/\s+/g, " ").trim();
			if (!reason) {
				frappe.msgprint(__("Enter a reason for deletion."));
				return;
			}
			dialog.disable_primary_action();
			frappe
				.call({
					method: "melliflous_branding.invoice_admin_records.delete_sales_invoices",
					args: { names, reason },
				})
				.then(() => {
					dialog.hide();
					if (listview.clear_checked_items) listview.clear_checked_items();
					listview.refresh();
				})
				.catch((error) => {
					dialog.enable_primary_action();
					const text = serverErrorText(error);
					if (dialog.fields_dict && dialog.fields_dict.server_error) {
						dialog.fields_dict.server_error.$wrapper.html(
							`<div class="text-danger">${frappe.utils.escape_html(text)}</div>`
						);
					}
					frappe.msgprint({ title: __("Could not delete"), message: text, indicator: "red" });
				});
		},
	});
	dialog.show();
}

function serverErrorText(error) {
	const response = (error && (error.responseJSON || error)) || {};
	let raw = response._server_messages || response.exc || response.message || "";
	if (Array.isArray(raw)) raw = raw.map((row) => (typeof row === "string" ? row : JSON.stringify(row))).join("\n");
	if (typeof raw !== "string") raw = String(raw || "");
	let text = raw;
	try {
		const parsed = JSON.parse(raw);
		if (Array.isArray(parsed)) {
			text = parsed
				.map((row) => {
					if (typeof row !== "string") return String(row || "");
					try {
						const item = JSON.parse(row);
						return (item && item.message) || row;
					} catch (parseError) {
						return row;
					}
				})
				.join("\n");
		}
	} catch (parseError) {
		text = raw;
	}
	const holder = document.createElement("div");
	holder.innerHTML = text;
	return (holder.textContent || "").replace(/\s+/g, " ").trim() || __("Could not delete this document.");
}

frappe.listview_settings["Payment Entry"] = {
	onload(listview) {
		frappe
			.call({ method: "melliflous_branding.invoice_admin_records.may_delete_sales_invoice" })
			.then((response) => {
				const allowed = response && response.message && cint(response.message.allowed);
				if (!allowed || !listview.page || !listview.page.add_actions_menu_item) return;
				listview.page.add_actions_menu_item(
					__("Delete with reason"),
					() => deleteCheckedPayments(listview),
					true,
					null,
					"trash-2",
					"red"
				);
			});
	},
};

function deleteCheckedPayments(listview) {
	const docs = listview.get_checked_items ? listview.get_checked_items() : [];
	const cancelled = docs.filter((row) => cint(row.docstatus) === 2);
	if (!cancelled.length) {
		frappe.msgprint(__("Cancel this payment before deleting it."));
		return;
	}
	const names = cancelled.map((row) => row.name).filter(Boolean);
	const dialog = new frappe.ui.Dialog({
		title: __("Delete with reason"),
		fields: [
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Reason for deletion"),
				reqd: 1,
			},
			{ fieldname: "server_error", fieldtype: "HTML" },
		],
		primary_action_label: __("Delete"),
		primary_action(values) {
			const reason = ((values && values.reason) || "").replace(/\s+/g, " ").trim();
			if (!reason) {
				frappe.msgprint(__("Enter a reason for deletion."));
				return;
			}
			dialog.disable_primary_action();
			frappe
				.call({
					method: "melliflous_branding.invoice_admin_records.delete_payment_entries",
					args: { names, reason },
				})
				.then(() => {
					dialog.hide();
					if (listview.clear_checked_items) listview.clear_checked_items();
					listview.refresh();
				})
				.catch((error) => {
					dialog.enable_primary_action();
					const text = serverErrorText(error);
					if (dialog.fields_dict && dialog.fields_dict.server_error) {
						dialog.fields_dict.server_error.$wrapper.html(
							`<div class="text-danger">${frappe.utils.escape_html(text)}</div>`
						);
					}
					frappe.msgprint({ title: __("Could not delete"), message: text, indicator: "red" });
				});
		},
	});
	dialog.show();
}
