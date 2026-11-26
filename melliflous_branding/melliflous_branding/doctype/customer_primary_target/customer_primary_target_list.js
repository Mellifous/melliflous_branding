frappe.listview_settings["Customer Primary Target"] = {
	onload(listview) {
		if (!frappe.model.can_create("Customer Primary Target")) {
			return;
		}
		listview.page.add_button(__("Set Targets for Month"), () => open_bulk(listview));
	},
	get_indicator(doc) {
		const pct = Number(doc.achievement_pct || 0);
		let color = "red";
		if (pct >= 100) {
			color = "green";
		} else if (pct >= 70) {
			color = "orange";
		}
		return [__(doc.status || "Not Achieved"), color, "status,=," + (doc.status || "")];
	},
};

function open_bulk(listview) {
	const dialog = new frappe.ui.Dialog({
		title: __("Set Targets for Month"),
		size: "extra-large",
		fields: [
			{
				fieldname: "company",
				fieldtype: "Link",
				options: "Company",
				label: __("Company"),
				reqd: 1,
				default: frappe.defaults.get_user_default("company"),
			},
			{
				fieldname: "month",
				fieldtype: "Date",
				label: __("Month"),
				reqd: 1,
				default: frappe.datetime.month_start(),
				description: __("Any day in the month. The target runs from the first to the last day."),
			},
			{ fieldname: "column_break_filters", fieldtype: "Column Break" },
			{
				fieldname: "sales_person",
				fieldtype: "Link",
				options: "Sales Person",
				label: __("Only customers of"),
			},
			{
				fieldname: "customer_group",
				fieldtype: "Link",
				options: "Customer Group",
				label: __("Customer Group"),
			},
			{ fieldname: "section_filter", fieldtype: "Section Break", label: __("Optional filter") },
			{
				fieldname: "item_group",
				fieldtype: "Link",
				options: "Item Group",
				label: __("Item Group"),
				description: __("Leave blank to count the whole invoice. Child item groups are included."),
			},
			{ fieldname: "column_break_item", fieldtype: "Column Break" },
			{
				fieldname: "brand",
				fieldtype: "Link",
				options: "Brand",
				label: __("Brand"),
			},
			{
				fieldname: "load_customers",
				fieldtype: "Button",
				label: __("Load Customers"),
			},
			{ fieldname: "notice", fieldtype: "HTML" },
			{ fieldname: "section_grid", fieldtype: "Section Break" },
			{
				fieldname: "targets",
				fieldtype: "Table",
				label: __("Customers"),
				cannot_add_rows: false,
				in_place_edit: true,
				data: [],
				fields: [
					{
						fieldname: "customer",
						fieldtype: "Link",
						options: "Customer",
						label: __("Customer"),
						in_list_view: 1,
						columns: 2,
					},
					{
						fieldname: "customer_name",
						fieldtype: "Data",
						label: __("Name"),
						in_list_view: 1,
						read_only: 1,
						columns: 2,
					},
					{
						fieldname: "territory",
						fieldtype: "Data",
						label: __("Territory"),
						in_list_view: 1,
						read_only: 1,
						columns: 2,
					},
					{
						fieldname: "target_amount",
						fieldtype: "Currency",
						label: __("Target Amount"),
						in_list_view: 1,
						columns: 2,
					},
					{
						fieldname: "target_qty",
						fieldtype: "Float",
						label: __("Target Qty"),
						in_list_view: 1,
						columns: 1,
					},
					{
						fieldname: "uom",
						fieldtype: "Link",
						options: "UOM",
						label: __("UOM"),
						in_list_view: 1,
						columns: 1,
					},
					{
						fieldname: "sales_person",
						fieldtype: "Link",
						options: "Sales Person",
						label: __("Sales Person"),
						in_list_view: 1,
						columns: 2,
					},
				],
			},
		],
		primary_action_label: __("Save Targets"),
		primary_action(values) {
			save_bulk(dialog, listview, values);
		},
	});
	dialog._loaded_key = "";
	dialog.show();
	const button = dialog.fields_dict.load_customers;
	const node = button.$input || $(button.input);
	node.on("click", () => load_customers(dialog));
	if (dialog.get_value("company")) {
		load_customers(dialog);
	}
}

function bulk_key(values) {
	return [
		values.company || "",
		values.month || "",
		values.item_group || "",
		values.brand || "",
		values.sales_person || "",
		values.customer_group || "",
	].join("|");
}

function load_customers(dialog) {
	const values = dialog.get_values();
	if (!values || !values.company || !values.month) {
		frappe.msgprint(__("Pick a company and a month."));
		return;
	}
	frappe.call({
		method: "melliflous_branding.target_records.customers_for_month",
		args: {
			company: values.company,
			month: values.month,
			item_group: values.item_group,
			brand: values.brand,
			sales_person: values.sales_person,
			customer_group: values.customer_group,
		},
		callback(response) {
			const message = response.message || {};
			dialog.set_value("targets", message.rows || []);
			dialog._loaded_key = bulk_key(values);
			const notice = dialog.fields_dict.notice.$wrapper;
			if (message.truncated) {
				notice.html(
					`<p class="text-muted">${__(
						"Showing the first 500 customers. Filter by sales person or customer group to narrow the list."
					)}</p>`
				);
			} else {
				notice.html("");
			}
		},
	});
}

function save_bulk(dialog, listview, values) {
	if (dialog._loaded_key && dialog._loaded_key !== bulk_key(values)) {
		frappe.msgprint(__("Load customers again. The month or the filter changed."));
		return;
	}
	dialog.disable_primary_action();
	frappe.call({
		method: "melliflous_branding.target_records.create_monthly_targets",
		args: {
			company: values.company,
			month: values.month,
			item_group: values.item_group,
			brand: values.brand,
			rows: values.targets || [],
		},
		callback(response) {
			dialog.enable_primary_action();
			const message = (response && response.message) || {};
			frappe.show_alert({
				message: __("{0} created, {1} updated", [message.created || 0, message.updated || 0]),
				indicator: "green",
			});
			dialog.hide();
			listview.refresh();
		},
		error() {
			dialog.enable_primary_action();
		},
	});
}
