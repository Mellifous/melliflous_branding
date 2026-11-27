// Invoice No sits at the top of the Sales Invoice Details tab.
// The value is the document name. The server suggests the next serial and
// rejects a repeat or a number that breaks posting-date order.
const INVOICE_NO_SUGGEST = "melliflous_branding.invoice_number_records.suggest_invoice_no";
const INVOICE_NO_CHECK = "melliflous_branding.invoice_number_records.check_invoice_no";

function prepareInvoiceNumber(frm) {
	if (!frm.fields_dict || !frm.fields_dict.custom_invoice_no) return;
	frm.set_df_property("naming_series", "hidden", 1);
	const locked = cint(frm.doc.docstatus) !== 0;
	frm.set_df_property("custom_invoice_no", "read_only", locked ? 1 : 0);
	if (!frm.is_new() && !frm.doc.custom_invoice_no && frm.doc.name) {
		frm.doc.custom_invoice_no = frm.doc.name;
		frm.refresh_field("custom_invoice_no");
	}
	setTimeout(() => {
		placeInvoiceNumber(frm);
		styleInvoiceNumber(frm);
	}, 0);
	if (locked || frm.doc.amended_from) return;
	if (frm.is_new() && !frm._invoice_no_edited && !(frm.doc.custom_invoice_no || "").trim()) {
		suggestInvoiceNumber(frm);
	}
}

function onInvoiceContextChanged(frm) {
	if (!frm.fields_dict || !frm.fields_dict.custom_invoice_no) return;
	if (cint(frm.doc.docstatus) !== 0 || frm.doc.amended_from) return;
	if (frm.is_new() && !frm._invoice_no_edited) {
		suggestInvoiceNumber(frm);
		return;
	}
	if ((frm.doc.custom_invoice_no || "").trim()) checkInvoiceNumber(frm);
}

function onInvoiceNumberChanged(frm) {
	if (frm._setting_invoice_no) return;
	const value = (frm.doc.custom_invoice_no || "").trim();
	if (!value) {
		frm._invoice_no_edited = false;
		frm._invoice_no_check = null;
		if (frm.is_new() && cint(frm.doc.docstatus) === 0 && !frm.doc.amended_from) suggestInvoiceNumber(frm);
		return;
	}
	frm._invoice_no_edited = true;
	checkInvoiceNumber(frm);
}

function suggestInvoiceNumber(frm) {
	if (!frm.doc.company) return;
	frm._suggest_ticket = (frm._suggest_ticket || 0) + 1;
	const ticket = frm._suggest_ticket;
	frappe
		.call({
			method: INVOICE_NO_SUGGEST,
			args: {
				company: frm.doc.company,
				posting_date: frm.doc.posting_date,
				naming_series: frm.doc.naming_series,
				is_return: frm.doc.is_return ? 1 : 0,
			},
		})
		.then((response) => {
			if (ticket !== frm._suggest_ticket || frm._invoice_no_edited) return;
			const message = (response && response.message) || {};
			if (!message.invoice_no) {
				if (message.warning && frm._invoice_warning !== message.warning) {
					frm._invoice_warning = message.warning;
					frappe.msgprint({ title: __("Invoice number"), message: message.warning, indicator: "orange" });
				}
				if ((frm.doc.custom_invoice_no || "").trim()) setInvoiceNumber(frm, "");
				return;
			}
			frm._invoice_warning = null;
			setInvoiceNumber(frm, message.invoice_no);
		});
}

function checkInvoiceNumber(frm) {
	const value = (frm.doc.custom_invoice_no || "").trim();
	if (!value || !frm.doc.company) return;
	frm._check_ticket = (frm._check_ticket || 0) + 1;
	const ticket = frm._check_ticket;
	frappe
		.call({
			method: INVOICE_NO_CHECK,
			args: {
				invoice_no: value,
				company: frm.doc.company,
				posting_date: frm.doc.posting_date,
				current: frm.is_new() ? "" : frm.doc.name,
				naming_series: frm.doc.naming_series,
				is_return: frm.doc.is_return ? 1 : 0,
			},
		})
		.then((response) => {
			if (ticket !== frm._check_ticket) return;
			if ((frm.doc.custom_invoice_no || "").trim() !== value) return;
			const message = (response && response.message) || {};
			frm._invoice_no_check = message;
			if (message.ok === false && message.message) {
				frappe.msgprint({ title: __("Invoice number"), message: message.message, indicator: "red" });
			}
		});
}

function setInvoiceNumber(frm, value) {
	frm._setting_invoice_no = true;
	const done = () => {
		frm._setting_invoice_no = false;
		styleInvoiceNumber(frm);
	};
	frm.set_value("custom_invoice_no", value).then(done, done);
}

function placeInvoiceNumber(frm) {
	const field = frm.get_field("custom_invoice_no");
	if (!field || !field.$wrapper || !field.$wrapper.length) return;
	const layout = field.$wrapper.closest(".form-layout");
	if (!layout.length) return;
	const body = layout.find(".form-page").first().find(".section-body").first();
	if (!body.length) return;
	let slot = body.children(".melliflous-invoice-no");
	if (!slot.length) {
		slot = $('<div class="form-column col-sm-12 melliflous-invoice-no"></div>');
		body.prepend(slot);
	}
	if (!slot[0].contains(field.$wrapper[0])) slot.append(field.$wrapper);
	field.$wrapper.css({ width: "100%", maxWidth: "100%" });
}

function styleInvoiceNumber(frm) {
	const field = frm.get_field("custom_invoice_no");
	if (!field || !field.$input || !field.$input.length) return;
	field.$input.css({
		fontSize: "18px",
		fontWeight: "700",
		minHeight: "44px",
	});
	field.$input.attr("autocomplete", "off");
	field.$input.attr("autocapitalize", "characters");
	field.$input.attr("enterkeyhint", "done");
}

function blockBadInvoiceNumber(frm) {
	const check = frm._invoice_no_check;
	const value = (frm.doc.custom_invoice_no || "").trim();
	if (!check || check.ok !== false || check.invoice_no !== value || !check.message) return;
	frappe.msgprint({ title: __("Invoice number"), message: check.message, indicator: "red" });
	frappe.validated = false;
}

frappe.ui.form.on("Sales Invoice", {
	refresh: prepareInvoiceNumber,
	company: onInvoiceContextChanged,
	posting_date: onInvoiceContextChanged,
	custom_invoice_no: onInvoiceNumberChanged,
	before_save: blockBadInvoiceNumber,
	after_save: followRenamedInvoice,
});

function followRenamedInvoice(frm) {
	if (!frm.doc || !frm.doc.name || !frappe.get_route) return;
	const route = frappe.get_route() || [];
	if (route[0] === "Form" && route[1] === "Sales Invoice" && route[2] && route[2] !== frm.doc.name) {
		frappe.set_route("Form", "Sales Invoice", frm.doc.name);
	}
}
