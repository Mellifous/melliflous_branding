// List Actions > Delete. Frappe adds the standard item only when
// boot.user.can_delete contains Sales Invoice, which requires the Invoice
// Admin role's level-0 Delete tick. That item deletes with no reason, so
// this script rebuilds the menu and asks for one. The server still allows
// the delete only for the Invoice Admin list.
function melliflousListMayDelete() {
	const boot = (window.frappe && frappe.boot) || {};
	const roles = (window.frappe && frappe.user_roles) || [];
	const deletable = (boot.user && boot.user.can_delete) || [];
	return !!(
		boot.melliflous_invoice_admin ||
		roles.indexOf("Invoice Admin") !== -1 ||
		deletable.indexOf("Sales Invoice") !== -1
	);
}

function melliflousDeleteLabel(label) {
	const text = String(label || "").replace(/\s+/g, " ").trim();
	return text === __("Delete") || text === "Delete" || text === __("Delete", null, "Button in list view actions menu");
}

frappe.listview_settings["Sales Invoice"] = {
	onload(listview) {
		if (!listview.get_actions_menu_items) return;
		const original = listview.get_actions_menu_items.bind(listview);
		listview.get_actions_menu_items = () => {
			const items = original().filter((item) => !melliflousDeleteLabel(item && item.label));
			if (!melliflousListMayDelete()) return items;
			items.push({
				label: __("Delete", null, "Button in list view actions menu"),
				icon: "trash-2",
				theme: "red",
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
									listview.clear_checked_items && listview.clear_checked_items();
									listview.refresh();
								})
								.catch(() => dialog.enable_primary_action());
						},
					});
					dialog.show();
				},
			});
			return items;
		};
		// The Actions menu was built before this onload. Rebuild it so Delete
		// is the reason prompt, and so it is present for Invoice Admin.
		if (listview.page && listview.page.clear_actions_menu && listview.set_actions_menu_items) {
			listview.page.clear_actions_menu();
			listview.set_actions_menu_items();
		}
	},
};
