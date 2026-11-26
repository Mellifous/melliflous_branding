frappe.pages["give-task"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Give a Task"),
		single_column: true,
	});
	melliflous_quick.mountTasks(page, false);
};
