frappe.ui.form.on("Recipe", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_user_default("company"));
		}
		if (frm.is_new() && !frm.doc.division) {
			frm.set_value("division", frappe.defaults.get_user_default("division"));
		}
	},
	refresh(frm) {
		frm.set_query("division", () => ({
			filters: { company: frm.doc.company || "", is_active: 1 },
		}));
		frm.set_query("item", () => ({ filters: { is_stock_item: 1, disabled: 0 } }));
		frm.set_query("sub_recipe", "sub_assemblies", () => ({
			filters: { is_active: 1, name: ["!=", frm.doc.name || ""] },
		}));
		show_blend(frm);
		if (frm.doc.bom) {
			frm.add_custom_button(__("Open BOM"), () => {
				frappe.set_route("Form", "BOM", frm.doc.bom);
			});
		}
		frm.add_custom_button(__("Convert Stock"), () => {
			frappe.route_options = { recipe: frm.doc.name };
			frappe.set_route("convert-stock");
		});
	},
	company(frm) {
		if (frm.doc.division) {
			frappe.db.get_value("Division", frm.doc.division, "company").then((response) => {
				const company = response.message && response.message.company;
				if (company && company !== frm.doc.company) {
					frm.set_value("division", "");
				}
			});
		}
	},
	qty: show_blend,
	process_loss_percentage: show_blend,
});

frappe.ui.form.on("Recipe Ingredient", {
	percentage: show_blend,
	item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code) {
			return;
		}
		frappe.db.get_value("Item", row.item_code, "stock_uom").then((response) => {
			const uom = response.message && response.message.stock_uom;
			if (uom && uom !== row.uom) {
				frappe.model.set_value(cdt, cdn, "uom", uom);
			}
		});
	},
});

frappe.ui.form.on("Recipe Sub Assembly", {
	sub_recipe(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.sub_recipe) {
			return;
		}
		frappe.db.get_value("Recipe", row.sub_recipe, ["item", "uom"]).then((response) => {
			const value = response.message || {};
			if (value.uom) {
				frappe.model.set_value(cdt, cdn, "uom", value.uom);
			}
		});
	},
});

function show_blend(frm) {
	const rows = frm.doc.ingredients || [];
	rows.forEach((row) => {
		if (!row.percentage) {
			return;
		}
		const qty =
			(Number(frm.doc.qty) || 0) *
			((Number(row.percentage) || 0) / 100) *
			(1 + (Number(frm.doc.process_loss_percentage) || 0) / 100);
		const shown = Math.round((qty + Number.EPSILON) * 1e6) / 1e6;
		if (Number(row.qty) !== shown) {
			frappe.model.set_value(row.doctype, row.name, "qty", shown);
		}
	});
	const percents = rows.map((row) => Number(row.percentage) || 0).filter((value) => value > 0);
	if (!frm.dashboard || !frm.dashboard.set_headline_alert || !percents.length) {
		return;
	}
	const total = Math.round(percents.reduce((sum, value) => sum + value, 0) * 1000) / 1000;
	const ok = Math.abs(total - 100) <= 0.001;
	frm.dashboard.set_headline_alert(
		__("Ingredients add up to {0}%.", [total]),
		ok ? "green" : "red"
	);
}
