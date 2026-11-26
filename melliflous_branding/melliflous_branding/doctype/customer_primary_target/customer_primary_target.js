frappe.ui.form.on("Customer Primary Target", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_user_default("company"));
		}
	},
	refresh(frm) {
		if (frm.is_new() || !frm.doc.status || !frm.dashboard || !frm.dashboard.set_headline_alert) {
			return;
		}
		const pct = Number(frm.doc.achievement_pct || 0);
		let color = "red";
		if (pct >= 100) {
			color = "green";
		} else if (pct >= 70) {
			color = "orange";
		}
		frm.dashboard.set_headline_alert(
			`${__(frm.doc.status)}: ${pct.toFixed(2)}%`,
			color
		);
	},
	company(frm) {
		if (!frm.doc.company) {
			return;
		}
		frappe.db.get_value("Company", frm.doc.company, "default_currency").then((response) => {
			const value = response.message && response.message.default_currency;
			if (value && value !== frm.doc.currency) {
				frm.set_value("currency", value);
			}
		});
	},
	period_type(frm) {
		fill_period(frm);
	},
	target_month(frm) {
		fill_period(frm);
	},
	target_quarter(frm) {
		fill_period(frm);
	},
	customer(frm) {
		if (!frm.doc.customer || (frm.doc.sales_person && frm.doc.sales_user)) {
			return;
		}
		frappe.call({
			method: "melliflous_branding.target_records.sales_person_for_customer",
			args: { customer: frm.doc.customer },
			callback(response) {
				const message = response.message || {};
				if (!frm.doc.sales_person && message.sales_person) {
					frm.set_value("sales_person", message.sales_person);
				}
				if (!frm.doc.sales_user && message.sales_user) {
					frm.set_value("sales_user", message.sales_user);
				}
			},
		});
	},
	sales_person(frm) {
		if (!frm.doc.sales_person || frm.doc.sales_user) {
			return;
		}
		frappe.call({
			method: "melliflous_branding.target_records.user_for_sales_person",
			args: { sales_person: frm.doc.sales_person },
			callback(response) {
				if (response.message && !frm.doc.sales_user) {
					frm.set_value("sales_user", response.message);
				}
			},
		});
	},
});

function fill_period(frm) {
	const quarterly = frm.doc.period_type === "Quarterly";
	const day = quarterly ? frm.doc.target_quarter || frm.doc.from_date : frm.doc.target_month || frm.doc.from_date;
	if (!day) {
		return;
	}
	if (!quarterly) {
		const bounds = month_bounds(day);
		frm.set_value("from_date", bounds[0]);
		frm.set_value("to_date", bounds[1]);
		return;
	}
	frappe.call({
		method: "melliflous_branding.target_records.period_dates",
		args: { period_type: "Quarterly", day: day },
		callback(response) {
			if (!response.message) {
				return;
			}
			frm.set_value("from_date", response.message.from_date);
			frm.set_value("to_date", response.message.to_date);
		},
	});
}

function month_bounds(value) {
	const parts = String(value).slice(0, 10).split("-");
	const year = parseInt(parts[0], 10);
	const month = parseInt(parts[1], 10);
	const last = new Date(Date.UTC(year, month, 0)).getUTCDate();
	return [pad_date(year, month, 1), pad_date(year, month, last)];
}

function pad_date(year, month, day) {
	return year + "-" + pad(month) + "-" + pad(day);
}

function pad(number) {
	return number < 10 ? "0" + number : String(number);
}
