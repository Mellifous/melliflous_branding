// List Actions > Delete for Sales Invoice. The role permission is off.
// Only the Invoice Admin list (and Administrator) get this item, and it
// asks for a reason before the server will delete.
frappe.listview_settings["Sales Invoice"] = {
	onload(listview) {
		const original = listview.get_actions_menu_items && listview.get_actions_menu_items.bind(listview);
		listview.can_delete = false;
		if (!original) return;
		listview.get_actions_menu_items = () => {
			const items = original().filter((item) => {
				const label = ((item && item.label) || "").replace(/\s+/g, " ").trim();
				return label !== __("Delete") && label !== "Delete";
			});
			const manage = !!(window.frappe && frappe.boot && frappe.boot.melliflous_invoice_admin);
			if (manage) {
				items.push({
					label: __("Delete"),
					standard: true,
					action() {
						const names = listview.get_checked_items(true);
						if (!names.length) {
							frappe.msgprint(__("Select an invoice first."));
							return;
						}
						const dialog = new frappe.ui.Dialog({
							title: __("Delete"),
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
										listview.refresh();
									})
									.catch(() => dialog.enable_primary_action());
							},
						});
						dialog.show();
					},
				});
			}
			return items;
		};
	},
};
