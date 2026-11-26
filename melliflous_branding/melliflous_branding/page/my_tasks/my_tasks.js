frappe.pages["my-tasks"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("My Tasks"),
		single_column: true,
	});
	melliflous_quick.mountTasks(page, true);
};
