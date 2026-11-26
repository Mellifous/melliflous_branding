frappe.pages["quick-lead"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Quick Lead"),
		single_column: true,
	});
	melliflous_quick.mountLead(page);
};
