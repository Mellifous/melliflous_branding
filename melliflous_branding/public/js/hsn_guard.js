// HSN and GST warnings. One dialog lists every issue. Nothing is written until
// Apply is clicked, and Apply selected on the audit page is System Manager only.
(function () {
	if (window.melliflous_hsn) {
		return;
	}

	const DOCTYPES = ["Sales Invoice", "Purchase Invoice", "Sales Order", "Delivery Note", "Quotation"];
	const STYLE_ID = "melliflous-hsn-guard";

	function inject_style() {
		if (document.getElementById(STYLE_ID)) {
			return;
		}
		const style = document.createElement("style");
		style.id = STYLE_ID;
		style.textContent = [
			".melliflous-hsn-dialog .modal-dialog { max-width: 640px; }",
			".melliflous-hsn-dialog .modal-body { font-size: 16px; }",
			".melliflous-hsn-issue { padding: 12px 0; border-bottom: 1px solid var(--border-color); }",
			".melliflous-hsn-issue h4 { font-size: 16px; margin: 0 0 4px; line-height: 1.3; }",
			".melliflous-hsn-issue p { margin: 0 0 4px; }",
			".melliflous-hsn-issue.error h4 { color: var(--red-600, #b42318); }",
			".melliflous-hsn-apply, .melliflous-hsn-dialog .btn, .melliflous-hsn-page .btn {",
			" min-height: 44px; font-size: 16px;",
			"}",
			".melliflous-hsn-page { padding-bottom: 24px; }",
			".melliflous-hsn-card {",
			" border: 1px solid var(--border-color); border-radius: 12px; padding: 12px; margin: 0 0 12px;",
			"}",
			".melliflous-hsn-card label { display: flex; gap: 12px; align-items: flex-start; min-height: 44px; font-size: 16px; }",
			".melliflous-hsn-card input { width: 22px; height: 22px; margin-top: 2px; }",
			".melliflous-hsn-note { color: var(--yellow-700, #8a6100); margin-top: 8px; }",
			"@media (max-width: 640px) {",
			" .melliflous-hsn-dialog .modal-dialog { width: calc(100% - 16px); margin: 8px auto; }",
			" .melliflous-hsn-dialog .modal-footer .btn, .melliflous-hsn-apply, .melliflous-hsn-page .btn {",
			"  width: 100%; margin: 4px 0;",
			" }",
			"}",
		].join("\n");
		document.head.appendChild(style);
	}

	function esc(value) {
		return frappe.utils.escape_html(String(value == null ? "" : value));
	}

	function render_issues(issues, suggestion, can_apply) {
		const blocks = (issues || [])
			.map((issue) => {
				const kind = issue.severity === "error" ? "error" : "warning";
				return (
					"<div class='melliflous-hsn-issue " +
					kind +
					"'><h4>" +
					esc(issue.title) +
					"</h4><p>" +
					esc(issue.detail) +
					"</p><p>" +
					esc(issue.suggestion) +
					"</p></div>"
				);
			})
			.join("");
		let apply = "";
		if (can_apply) {
			const template = suggestion.item_tax_template
				? " The item tax template will be set to " + esc(suggestion.item_tax_template) + "."
				: " The tax template is not changed, because there is not one clear GST template for this rate.";
			apply =
				"<button type='button' class='btn btn-primary melliflous-hsn-apply'>" +
				__("Apply and save") +
				"</button><p>" +
				__("Suggested HSN") +
				" " +
				esc(suggestion.hsn) +
				"." +
				template +
				"</p>";
		}
		return apply + blocks;
	}

	function acknowledge(frm, fingerprint) {
		return frappe.call({
			method: "melliflous_branding.hsn_records.acknowledge",
			args: { fingerprint: fingerprint, doctype: frm.doctype },
		});
	}

	function apply_on_form(frm, suggestion) {
		const steps = [];
		if (suggestion.hsn && frm.fields_dict.gst_hsn_code) {
			steps.push(frm.set_value("gst_hsn_code", suggestion.hsn));
		}
		return Promise.all(steps).then(() => {
			if (!suggestion.apply_template || !suggestion.item_tax_template) {
				return;
			}
			const rows = frm.doc.taxes || [];
			if (rows.some((row) => row.item_tax_template === suggestion.item_tax_template)) {
				return;
			}
			const gst_row = rows.find((row) => /gst/i.test(row.item_tax_template || "") || !row.item_tax_template);
			if (gst_row) {
				return frappe.model.set_value(
					gst_row.doctype,
					gst_row.name,
					"item_tax_template",
					suggestion.item_tax_template
				);
			}
			const child = frm.add_child("taxes");
			child.item_tax_template = suggestion.item_tax_template;
			frm.refresh_field("taxes");
		});
	}

	function show_dialog(payload, frm) {
		const issues = payload.issues || [];
		const errors = issues.filter((issue) => issue.severity === "error");
		const suggestion = payload.suggestion;
		const can_apply = frm.doctype === "Item" && suggestion && suggestion.hsn && !errors.length;
		inject_style();
		return new Promise((resolve, reject) => {
			let settled = false;
			function finish(save) {
				if (settled) {
					return;
				}
				settled = true;
				dialog.hide();
				if (save) {
					resolve();
				} else {
					reject();
				}
			}
			const dialog = new frappe.ui.Dialog({
				title: errors.length ? __("Fix these before saving") : __("Check this before saving"),
				size: "large",
				fields: [{ fieldtype: "HTML", fieldname: "body" }],
				primary_action_label: errors.length ? __("Go back") : __("Save anyway"),
				primary_action() {
					if (errors.length) {
						finish(false);
						return;
					}
					acknowledge(frm, payload.fingerprint).then(() => finish(true)).catch(() => finish(true));
				},
			});
			if (!errors.length) {
				dialog.set_secondary_action_label(__("Go back"));
				dialog.set_secondary_action(() => finish(false));
			}
			dialog.$wrapper.addClass("melliflous-hsn-dialog");
			dialog.fields_dict.body.$wrapper.html(render_issues(issues, suggestion, can_apply));
			if (can_apply) {
				dialog.$wrapper.find(".melliflous-hsn-apply").on("click", () => {
					apply_on_form(frm, suggestion)
						.then(() => finish(true))
						.catch(() => finish(false));
				});
			}
			dialog.onhide = () => {
				if (!settled) {
					settled = true;
					reject();
				}
			};
			dialog.show();
		});
	}

	function guard(frm) {
		const item = frm.doctype === "Item";
		if (item && !frm.fields_dict.gst_hsn_code) {
			return;
		}
		return frappe
			.call({
				method: item
					? "melliflous_branding.hsn_records.check_item"
					: "melliflous_branding.hsn_records.check_document",
				args: item ? { item: frm.doc } : { doc: frm.doc },
			})
			.then((response) => {
				const payload = response.message || {};
				if (!payload.issues || !payload.issues.length) {
					return;
				}
				return show_dialog(payload, frm);
			});
	}

	function mount_audit(page) {
		inject_style();
		const $body = $(page.body);
		$body.addClass("melliflous-hsn-page");
		$body.html(
			"<p class='text-muted'>" +
				__("Nothing is changed until a System Manager applies the ticked rows.") +
				"</p>" +
				"<div class='melliflous-hsn-actions'></div>" +
				"<div class='melliflous-hsn-list'></div>"
		);
		const $actions = $body.find(".melliflous-hsn-actions");
		const $list = $body.find(".melliflous-hsn-list");
		let can_apply = false;

		function selected() {
			return $list
				.find("input[data-item]:checked")
				.toArray()
				.map((node) => node.getAttribute("data-item"));
		}

		function draw(rows) {
			if (!rows.length) {
				$list.html("<p>" + __("No HSN problems on enabled items.") + "</p>");
				return;
			}
			const cards = rows
				.map((row) => {
					const checked = row.ambiguous ? "" : "checked";
					const note = row.ambiguous
						? "<p class='melliflous-hsn-note'>" +
							__("Ambiguous. Left unticked. Read the note before you apply it.") +
							"</p>"
						: "";
					return (
						"<article class='melliflous-hsn-card'><label><input type='checkbox' data-item='" +
						esc(row.item_code) +
						"' " +
						checked +
						"><span><strong>" +
						esc(row.item_code) +
						"</strong> " +
						esc(row.item_name) +
						"<br>" +
						esc(row.problem) +
						"</span></label><p>" +
						esc(row.suggestion) +
						"</p>" +
						note +
						"</article>"
					);
				})
				.join("");
			$list.html(cards);
		}

		function load() {
			$list.html("<p>" + __("Checking items…") + "</p>");
			frappe.call({
				method: "melliflous_branding.hsn_records.audit_items",
				callback(response) {
					const payload = response.message || {};
					can_apply = !!payload.can_apply;
					draw(payload.rows || []);
					if (!can_apply) {
						$actions.find(".melliflous-hsn-apply-selected").addClass("hidden");
					}
				},
			});
		}

		$actions.append(
			"<button type='button' class='btn btn-default melliflous-hsn-refresh'>" +
				__("Refresh") +
				"</button> " +
				"<button type='button' class='btn btn-default melliflous-hsn-all'>" +
				__("Select clear rows") +
				"</button> " +
				"<button type='button' class='btn btn-primary melliflous-hsn-apply-selected'>" +
				__("Apply selected") +
				"</button>"
		);
		$actions.find(".melliflous-hsn-refresh, .melliflous-hsn-all").on("click", function () {
			if (this.classList.contains("melliflous-hsn-all")) {
				$list.find("input[data-item]").prop("checked", false);
				$list.find(".melliflous-hsn-card").each(function () {
					if (!$(this).find(".melliflous-hsn-note").length) {
						$(this).find("input").prop("checked", true);
					}
				});
				return;
			}
			load();
		});
		$actions.find(".melliflous-hsn-apply-selected").on("click", () => {
			if (!can_apply) {
				frappe.msgprint(__("Only a System Manager can apply these."));
				return;
			}
			const codes = selected();
			if (!codes.length) {
				frappe.msgprint(__("Tick at least one item."));
				return;
			}
			frappe.confirm(
				__("Apply the suggested HSN on {0} items? A tax template is set only when one GST template matches the rate.", [
					codes.length,
				]),
				() => {
					frappe.call({
						method: "melliflous_branding.hsn_records.apply_selected",
						args: { item_codes: codes },
						callback(response) {
							const payload = response.message || {};
							const changed = (payload.changed || []).length;
							const skipped = payload.skipped || [];
							let message = __("Updated {0} items.", [changed]);
							if (skipped.length) {
								message +=
									" " +
									skipped
										.map((row) => esc(row.item_code) + ": " + esc(row.reason))
										.join("<br>");
							}
							frappe.msgprint(message);
							load();
						},
					});
				}
			);
		});
		load();
	}

	frappe.ui.form.on("Item", {
		before_save(frm) {
			return guard(frm);
		},
	});
	DOCTYPES.forEach((doctype) => {
		frappe.ui.form.on(doctype, {
			before_save(frm) {
				return guard(frm);
			},
		});
	});

	window.melliflous_hsn = { mount_audit };
})();
