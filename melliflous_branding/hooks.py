app_name = "melliflous_branding"
app_title = "Melliflous Branding"
app_publisher = "Melliflous"
app_description = "Desk branding for Melliflous Group on Frappe v16"
app_email = "developers@melliflous.com"
app_license = "MIT"

required_apps = ["frappe"]

# Tiles declared for the v16 apps screen. Boot copies only the first entry of an
# installed app into the grid (that is Quick Actions). Distributor 360 is placed
# on the same grid from boot_session, because a second entry here is ignored.
add_to_apps_screen = [
	{
		"name": "melliflous_branding",
		"logo": "/assets/melliflous_branding/images/melliflous_icon_512.png",
		"title": "Quick Actions",
		"route": "/desk/quick-actions",
		"has_permission": "melliflous_branding.access.can_show_quick_actions",
		"sequence_id": 12,
	},
	{
		"name": "distributor_360",
		"logo": "/assets/melliflous_branding/images/distributor_360.png",
		"title": "Distributor 360",
		"route": "/desk/distributor-360",
		"has_permission": "melliflous_branding.access.can_show_distributor_360",
		"sequence_id": 13,
	},
]

# Includes in <head> of desk.html (styles in head, script at the end of body).
# desk_tiles.js is its own file so a cached quick_actions.js cannot hide the tiles.
# The query is bumped when the desk theme changes. The theme is also injected
# from desk_theme.js, because a cached app_include_css file has shipped stale
# rules after a deploy. No bench build is required.
DESK_ASSET_VERSION = "20261127c"
app_include_css = [
	f"/assets/melliflous_branding/css/melliflous_branding.css?v={DESK_ASSET_VERSION}",
	f"/assets/melliflous_branding/css/desk_theme.css?v={DESK_ASSET_VERSION}",
]
app_include_js = [
	f"/assets/melliflous_branding/js/melliflous_branding.js?v={DESK_ASSET_VERSION}",
	f"/assets/melliflous_branding/js/quick_actions.js?v={DESK_ASSET_VERSION}",
	f"/assets/melliflous_branding/js/desk_tiles.js?v={DESK_ASSET_VERSION}",
	f"/assets/melliflous_branding/js/desk_theme.js?v={DESK_ASSET_VERSION}",
	# HSN warnings. Own file so the desk theme and invoice naming stay untouched.
	"/assets/melliflous_branding/js/hsn_guard.js?v=20261127hsn",
]

# Desk boot. sessions.get calls extend_bootinfo on every boot, including a
# cached one. boot.get_bootinfo still calls boot_session. Register both.
extend_bootinfo = ["melliflous_branding.boot.boot_session"]
boot_session = ["melliflous_branding.boot.boot_session"]

# iOS reads apple-touch-icon from the document HTML. Desk has no head-include
# hook, so the tags are inserted into the /desk response here.
after_request = ["melliflous_branding.boot.inject_pwa_head"]

# Home/Team Files is created on install and again on every migrate if it is
# missing. The same migrate gives Raven User to enabled desk users when that
# role exists.
after_install = "melliflous_branding.install.after_install"
after_migrate = ["melliflous_branding.install.after_migrate"]

# A file saved into Team Files is forced private before Frappe writes it.
# Selling documents refuse a Blocked or Blacklisted customer. Unblock first.
doc_events = {
	"File": {
		"before_validate": "melliflous_branding.team_files.keep_team_file_private",
	},
	"Customer": {
		"validate": [
			"melliflous_branding.customer_records.validate_customer",
			"melliflous_branding.division_records.apply_division",
		],
		"on_update": "melliflous_branding.customer_records.remember_billing_change",
	},
	"Sales Invoice": {
		"validate": [
			"melliflous_branding.customer_records.block_selling",
			"melliflous_branding.division_records.apply_division",
			"melliflous_branding.hsn_records.validate_document",
		],
		"before_rename": "melliflous_branding.invoice_admin_records.guard_rename",
		"after_rename": "melliflous_branding.invoice_admin_records.log_rename",
		"on_trash": "melliflous_branding.invoice_admin_records.guard_delete",
	},
	"Purchase Invoice": {
		"validate": [
			"melliflous_branding.division_records.apply_division",
			"melliflous_branding.hsn_records.validate_document",
		],
		"before_rename": "melliflous_branding.invoice_admin_records.guard_rename",
		"after_rename": "melliflous_branding.invoice_admin_records.log_rename",
		"on_trash": "melliflous_branding.invoice_admin_records.guard_delete",
	},
	"Sales Order": {
		"validate": [
			"melliflous_branding.customer_records.block_selling",
			"melliflous_branding.division_records.apply_division",
			"melliflous_branding.hsn_records.validate_document",
		]
	},
	"Quotation": {
		"validate": [
			"melliflous_branding.customer_records.block_selling",
			"melliflous_branding.division_records.apply_division",
			"melliflous_branding.hsn_records.validate_document",
		]
	},
	"Delivery Note": {
		"validate": [
			"melliflous_branding.customer_records.block_selling",
			"melliflous_branding.division_records.apply_division",
			"melliflous_branding.hsn_records.validate_document",
		]
	},
	"Payment Entry": {"validate": "melliflous_branding.division_records.apply_division"},
	"Item": {
		"validate": [
			"melliflous_branding.division_records.apply_division",
			"melliflous_branding.hsn_records.validate_item",
		]
	},
	"Purchase Order": {"validate": "melliflous_branding.division_records.apply_division"},
	"CRM Lead": {"validate": "melliflous_branding.division_records.apply_division"},
	"CRM Deal": {"validate": "melliflous_branding.division_records.apply_division"},
}

doctype_js = {
	"Customer": "public/js/customer.js",
	"Sales Invoice": "public/js/invoice_admin.js",
	"Purchase Invoice": "public/js/invoice_admin.js",
}
doctype_list_js = {"Customer": "public/js/customer_list.js"}

fixtures = [
	{
		"doctype": "Custom Field",
		"filters": [["name", "in", [
			"Customer-custom_billing_status",
			"Customer-custom_block_reason",
			"Customer-custom_blocked_by",
			"Customer-custom_blocked_on",
			"Customer-custom_documents_tab",
			"Customer-custom_customer_documents",
		]]],
	},
	{"doctype": "HSN Category Map"},
]

# Customer primary targets. The daily job rewrites achieved amount, gap, percent,
# and status. Sales User is limited to the targets they own.
scheduler_events = {
	"daily": [
		"melliflous_branding.target_records.refresh_primary_targets",
	],
}

permission_query_conditions = {
	"Customer Primary Target": "melliflous_branding.target_records.get_permission_query_conditions",
	"Distributor Profile": "melliflous_branding.distributor_records.profile_permission_query",
	"Distributor Visit": "melliflous_branding.distributor_records.visit_permission_query",
	"Distributor Stock Statement": "melliflous_branding.distributor_records.statement_permission_query",
	"Distributor Complaint": "melliflous_branding.distributor_records.complaint_permission_query",
	"Distributor Benefit": "melliflous_branding.distributor_records.benefit_permission_query",
}

has_permission = {
	"Customer Primary Target": "melliflous_branding.target_records.has_target_permission",
	"Distributor Profile": "melliflous_branding.distributor_records.has_profile_permission",
	"Distributor Visit": "melliflous_branding.distributor_records.has_visit_permission",
	"Distributor Stock Statement": "melliflous_branding.distributor_records.has_statement_permission",
	"Distributor Complaint": "melliflous_branding.distributor_records.has_complaint_permission",
	"Distributor Benefit": "melliflous_branding.distributor_records.has_benefit_permission",
}
