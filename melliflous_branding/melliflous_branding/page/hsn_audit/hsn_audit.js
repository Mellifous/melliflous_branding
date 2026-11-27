frappe.pages["hsn-audit"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("HSN Audit"),
		single_column: true,
	});
	if (window.melliflous_hsn) {
		melliflous_hsn.mount_audit(page);
	}
};
