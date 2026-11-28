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
				.catch(() => dialog.enable_primary_action());
		},
	});
	dialog.show();
}
