// Rename and delete stay with Invoice Admin. e-Invoice and e-Way Bill stay manual.
// India Compliance still adds its buttons. This script only hides them for everyone else.
const GST_DELETE_WARNING =
	"Deleting a submitted or cancelled invoice can break the GST invoice series, GSTR-1, and any e-invoice or e-way bill. Continue only if GST has been handled.";

function melliflousInvoiceAdmin(frm) {
	const boot = window.frappe && frappe.boot;
	const manage = !!(boot && boot.melliflous_invoice_admin);
	const einvoice = !!(boot && boot.melliflous_can_einvoice);
	const sales = frm.doc && frm.doc.doctype === "Sales Invoice";
	if (!sales && !manage && frm.perm && frm.perm[0]) {
		frm.perm[0].delete = 0;
	}
	setTimeout(() => {
		hideInvoiceMenus(manage, sales);
		if (!einvoice) hideEInvoiceButtons(frm);
		if (sales) showDeleteInvoiceButton(frm);
	}, 0);
	if (sales && !frm._melliflous_sales_delete_wrapped && frm.savetrash) {
		frm._melliflous_sales_delete_wrapped = true;
		frm.savetrash = () => deleteSalesInvoiceWithReason(frm);
	}
	if (!sales && manage && !frm._melliflous_invoice_wrapped) {
		frm._melliflous_invoice_wrapped = true;
		const originalTrash = frm.savetrash && frm.savetrash.bind(frm);
		const originalRename = frm.rename && frm.rename.bind(frm);
		if (originalTrash) frm.savetrash = () => confirmInvoiceDelete(frm, originalTrash);
		if (originalRename) frm.rename = () => renameInvoiceWithReason(frm, originalRename);
	}
	if (sales && manage && !frm._melliflous_rename_wrapped && frm.rename) {
		frm._melliflous_rename_wrapped = true;
		const originalRename = frm.rename.bind(frm);
		frm.rename = () => renameInvoiceWithReason(frm, originalRename);
	}
}

function showDeleteInvoiceButton(frm) {
	// A saved draft or a cancelled invoice. The server, not boot, decides who sees it.
	if (!frm.doc || frm.is_new()) return;
	const status = cint(frm.doc.docstatus);
	if (status !== 0 && status !== 2) return;
	const ticket = (frm._delete_invoice_ticket || 0) + 1;
	frm._delete_invoice_ticket = ticket;
	frappe
		.call({ method: "melliflous_branding.invoice_admin_records.may_delete_sales_invoice" })
		.then((response) => {
			if (ticket !== frm._delete_invoice_ticket) return;
			if (!frm.doc || cint(frm.doc.docstatus) !== status) return;
			const allowed = response && response.message && cint(response.message.allowed);
			if (!allowed) return;
			const button = frm.add_custom_button(__("Delete Invoice"), () => deleteSalesInvoiceWithReason(frm));
			if (button) button.addClass("btn-danger");
		});
}

function deleteSalesInvoiceWithReason(frm) {
	const irn = ((frm.doc && frm.doc.irn) || "").trim();
	if (irn) {
		frappe.msgprint(__("This invoice has an IRN. Cancel the e-invoice before deleting it."));
		return;
	}
	if (cint(frm.doc.docstatus) === 1) {
		frappe.msgprint(__("Cancel this invoice before deleting it."));
		return;
	}
	const ask = () => askDeletionReason([frm.doc.name], () => frappe.set_route("List", "Sales Invoice"));
	if (cint(frm.doc.docstatus) === 2) {
		frappe.confirm(__(GST_DELETE_WARNING), ask);
		return;
	}
	ask();
}

function hideInvoiceMenus(manage, sales) {
	// Only an item whose whole label is Rename or Delete. "Delete Invoice" and
	// "Delete with reason" stay. Sales Invoice Delete is the custom button.
	document.querySelectorAll(".dropdown-menu li, .dropdown-menu .dropdown-item").forEach((item) => {
		const text = (item.textContent || "").replace(/\s+/g, " ").trim();
		if (text === "Delete Invoice" || text === "Delete with reason") return;
		const hideRename = text === "Rename" && !manage;
		const hideDelete = text === "Delete" && !sales && !manage;
		if (hideRename || hideDelete) item.remove();
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
		if (text === "Delete Invoice" || text === "Delete with reason") return;
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
