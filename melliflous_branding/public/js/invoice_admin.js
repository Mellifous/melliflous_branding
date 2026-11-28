// Rename and delete stay with Invoice Admin. e-Invoice and e-Way Bill stay manual.
// India Compliance still adds its buttons. This script only hides them for everyone else.
const GST_DELETE_WARNING =
	"Deleting a submitted or cancelled invoice can break the GST invoice series, GSTR-1, and any e-invoice or e-way bill. Continue only if GST has been handled.";

function melliflousInvoiceAdmin(frm) {
	const boot = window.frappe && frappe.boot;
	const manage = !!(boot && boot.melliflous_invoice_admin);
	const canDelete = manage || !!(boot && boot.melliflous_can_delete_invoice);
	const einvoice = !!(boot && boot.melliflous_can_einvoice);
	// Draft and cancelled invoices keep the standard Delete item for Invoice
	// Admin, Accounts Manager, and System Manager. Submitted invoices never
	// get that item from Frappe, because docstatus is 1.
	if (!canDelete && frm.perm && frm.perm[0]) {
		frm.perm[0].delete = 0;
	}
	setTimeout(() => {
		hideInvoiceMenus(manage, canDelete);
		if (!einvoice) hideEInvoiceButtons(frm);
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
	if (cint(frm.doc.docstatus) === 2) {
		frappe.confirm(__(GST_DELETE_WARNING), () => originalTrash());
		return;
	}
	originalTrash();
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
