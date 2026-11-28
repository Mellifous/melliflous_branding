// Rename and delete stay with Invoice Admin. e-Invoice and e-Way Bill stay manual.
// India Compliance still adds its buttons. This script only hides them for everyone else.
const GST_DELETE_WARNING =
	"Deleting a submitted or cancelled invoice can break the GST invoice series, GSTR-1, and any e-invoice or e-way bill. Continue only if GST has been handled.";

function salesInvoiceMenuDelete() {
	const boot = (window.frappe && frappe.boot) || {};
	const roles = (window.frappe && frappe.user_roles) || [];
	const deletable = (boot.user && boot.user.can_delete) || [];
	// The standard ⋯ item exists only when Sales Invoice is in can_delete.
	// That list is filled from the Invoice Admin role's Delete tick. The
	// settings list shows the item as well. Accounts Manager and System
	// Manager do not.
	return !!(
		boot.melliflous_invoice_admin ||
		roles.indexOf("Invoice Admin") !== -1 ||
		deletable.indexOf("Sales Invoice") !== -1
	);
}

function melliflousInvoiceAdmin(frm) {
	const boot = window.frappe && frappe.boot;
	const manage = !!(boot && boot.melliflous_invoice_admin);
	const einvoice = !!(boot && boot.melliflous_can_einvoice);
	const sales = frm.doc && frm.doc.doctype === "Sales Invoice";
	const canDelete = sales ? salesInvoiceMenuDelete() : manage;
	if (!canDelete && frm.perm && frm.perm[0]) {
		frm.perm[0].delete = 0;
	}
	setTimeout(() => {
		hideInvoiceMenus(manage, canDelete);
		if (!einvoice) hideEInvoiceButtons(frm);
		// Frappe draws Delete from boot.user.can_delete before this script runs.
		// If that list is still empty, add the item here. A second "Delete"
		// with the same label is ignored, and the click calls frm.savetrash,
		// which this script wraps so a reason is required.
		if (sales && canDelete && cint(frm.doc.docstatus) !== 1 && frm.page && frm.page.add_menu_item) {
			frm.page.add_menu_item(__("Delete"), () => confirmInvoiceDelete(frm), true);
		}
	}, 0);
	if (!frm._melliflous_invoice_wrapped && (manage || canDelete)) {
		frm._melliflous_invoice_wrapped = true;
		const originalTrash = frm.savetrash && frm.savetrash.bind(frm);
		const originalRename = frm.rename && frm.rename.bind(frm);
		if (canDelete && originalTrash) {
			frm.savetrash = () => confirmInvoiceDelete(frm, originalTrash);
		}
		if (manage && originalRename) {
			frm.rename = () => renameInvoiceWithReason(frm, originalRename);
		}
	}
}

function hideInvoiceMenus(manage, canDelete) {
	if (manage && canDelete) return;
	document.querySelectorAll(".dropdown-menu .dropdown-item, .dropdown-menu li a, .menu-item-label").forEach((node) => {
		const text = (node.textContent || "").replace(/\s+/g, " ").trim();
		const hideRename = text === "Rename" && !manage;
		const hideDelete = text === "Delete" && !canDelete;
		if (hideRename || hideDelete) {
			const item = node.closest("li") || node.closest(".dropdown-item") || node;
			item.remove();
		}
	});
}

function hideEInvoiceButtons(frm) {
	["Generate e-Invoice", "Generate e-Waybill", "e-Invoice", "e-Waybill"].forEach((label) => {
		if (frm.remove_custom_button) frm.remove_custom_button(__(label));
	});
	if (frm.remove_custom_button) {
		frm.remove_custom_button(__("Generate"), "e-Invoice");
		frm.remove_custom_button(__("Generate"), "e-Waybill");
	}
	document.querySelectorAll(".custom-actions .btn, .inner-group-button .dropdown-item, .page-actions .btn").forEach((node) => {
		const text = (node.textContent || "").replace(/\s+/g, " ").trim();
		if (/^Generate e-Invoice$/i.test(text) || /^Generate e-Waybill$/i.test(text) || /^Generate e-Way Bill$/i.test(text)) {
			const item = node.closest("li") || node;
			item.remove();
		}
	});
}

function confirmInvoiceDelete(frm, originalTrash) {
	const irn = (frm.doc.irn || "").trim();
	if (irn) {
		frappe.msgprint(__("This invoice has an IRN. Cancel the e-invoice before deleting it."));
		return;
	}
	if (cint(frm.doc.docstatus) === 1) {
		frappe.msgprint(__("Cancel this invoice before deleting it."));
		return;
	}
	const run = () => {
		if (frm.doc.doctype === "Sales Invoice") {
			askDeletionReason([frm.doc.name], () => frappe.set_route("List", "Sales Invoice"));
			return;
		}
		if (originalTrash) originalTrash();
	};
	if (cint(frm.doc.docstatus) === 2) {
		frappe.confirm(__(GST_DELETE_WARNING), run);
		return;
	}
	run();
}

function askDeletionReason(names, done) {
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
					if (done) done();
				})
				.catch(() => dialog.enable_primary_action());
		},
	});
	dialog.show();
}

function renameInvoiceWithReason(frm, originalRename) {
	if (cint(frm.doc.docstatus) === 0) {
		originalRename();
		return;
	}
	const dialog = new frappe.ui.Dialog({
		title: __("Rename"),
		fields: [
			{ fieldname: "new_name", fieldtype: "Data", label: __("New invoice number"), reqd: 1, default: frm.doc.name },
			{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
		],
		primary_action_label: __("Rename"),
		primary_action(values) {
			dialog.disable_primary_action();
			frappe
				.call({
					method: "melliflous_branding.invoice_admin_records.rename_invoice",
					args: {
						doctype: frm.doc.doctype,
						old: frm.doc.name,
						new: values.new_name,
						reason: values.reason,
					},
				})
				.then((response) => {
					dialog.hide();
					const renamed = response && response.message && response.message.name;
					if (renamed) frappe.set_route("Form", frm.doc.doctype, renamed);
				})
				.catch(() => dialog.enable_primary_action());
		},
	});
	dialog.show();
}

frappe.ui.form.on("Sales Invoice", { refresh: melliflousInvoiceAdmin });
frappe.ui.form.on("Purchase Invoice", { refresh: melliflousInvoiceAdmin });
