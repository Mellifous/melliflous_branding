frappe.pages["add-team-member"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Add Team Member"),
		single_column: true,
	});
	melliflous_quick.mountTeam(page);
};
