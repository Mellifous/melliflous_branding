// Loaded by getpage from this file (page/team_files/team_files.js). The same
// mount also lives in the desk bundle, because a Page opened while migrate was
// still running can be cached in the browser with an empty script.
frappe.pages["team-files"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Team Files"),
		single_column: true,
	});

	const mount = function () {
		if (wrapper.querySelector(".melliflous-quick")) return true;
		if (!(window.melliflous_quick && melliflous_quick.mountFiles)) return false;
		melliflous_quick.mountFiles(page);
		return true;
	};

	if (mount()) return;

	let tries = 0;
	const timer = setInterval(function () {
		tries += 1;
		if (mount() || tries > 30) clearInterval(timer);
	}, 100);
};
