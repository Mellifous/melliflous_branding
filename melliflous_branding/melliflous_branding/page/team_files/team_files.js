frappe.pages["team-files"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Team Files"),
		single_column: true,
	});
	melliflous_quick.mountFiles(page);
};
