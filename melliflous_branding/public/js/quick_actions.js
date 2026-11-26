// Simple screens for Quick Actions. Loaded on every desk page, used by the
// four standard pages. Server methods check permission again.
window.melliflous_quick = (function () {
	const TEAM = "melliflous_branding.team";
	const TASKS = "melliflous_branding.tasks";
	const LEADS = "melliflous_branding.leads";
	const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

	function call(method, args) {
		return frappe.call({ method, args: args || {} });
	}

	function el(tag, className, text) {
		const node = document.createElement(tag);
		if (className) node.className = className;
		if (text != null) node.textContent = text;
		return node;
	}

	function field(parent, label, control) {
		parent.appendChild(el("label", "", label));
		parent.appendChild(control);
		return control;
	}

	function input(type) {
		const node = el("input", "form-control");
		node.type = type || "text";
		return node;
	}

	function select(placeholder) {
		const node = el("select", "form-control");
		if (placeholder) {
			const option = el("option", "", placeholder);
			option.value = "";
			node.appendChild(option);
		}
		return node;
	}

	function addOption(node, value, label) {
		const option = el("option", "", label);
		option.value = value;
		node.appendChild(option);
		return option;
	}

	function banner(parent) {
		const node = el("div", "banner");
		node.hidden = true;
		parent.prepend(node);
		return {
			show(message, isError) {
				node.hidden = false;
				node.classList.toggle("is-error", !!isError);
				node.textContent = message;
			},
			clear() {
				node.hidden = true;
				node.textContent = "";
			},
		};
	}

	function tomorrow() {
		const day = new Date();
		day.setDate(day.getDate() + 1);
		const month = String(day.getMonth() + 1).padStart(2, "0");
		const date = String(day.getDate()).padStart(2, "0");
		return `${day.getFullYear()}-${month}-${date}`;
	}

	function prettyDate(iso) {
		if (!iso) return "";
		const parts = String(iso).split("-");
		if (parts.length < 3) return String(iso);
		return `${Number(parts[2])} ${MONTHS[Number(parts[1]) - 1] || ""} ${parts[0]}`;
	}

	function fail(error, note) {
		const message =
			(error && error.message) ||
			(typeof error === "string" ? error : "") ||
			__("Something went wrong. Please try again.");
		note.show(message, true);
	}

	function mountTeam(page) {
		const root = el("div", "melliflous-quick");
		page.main.empty().append(root);
		if (!frappe.user.has_role("System Manager")) {
			root.appendChild(el("p", "", __("Only an owner or admin can add people.")));
			return;
		}
		const note = banner(root);
		const form = el("div");
		root.appendChild(form);
		const name = field(form, __("Full name"), input("text"));
		name.autocomplete = "name";
		const email = field(form, __("Email"), input("email"));
		email.autocomplete = "email";
		email.required = true;
		const mobile = field(form, __("Mobile"), input("tel"));
		mobile.autocomplete = "tel";
		form.appendChild(el("div", "field-label", __("Companies")));
		const ticks = el("div");
		form.appendChild(ticks);
		const defaultCompany = field(form, __("Default company"), select(__("Tick a company first")));
		const role = field(form, __("What they do"), select(__("Choose one")));
		const save = el("button", "btn btn-primary btn-save", __("Save"));
		save.type = "button";
		form.appendChild(save);
		const clear = el("button", "btn btn-default btn-save", __("New person"));
		clear.type = "button";
		form.appendChild(clear);
		root.appendChild(el("h2", "", __("People")));
		const list = el("div");
		root.appendChild(list);

		let companies = [];

		function ticked() {
			return Array.from(ticks.querySelectorAll("input:checked")).map((box) => box.value);
		}

		function refreshDefault(prefer) {
			const chosen = ticked();
			const current = prefer || defaultCompany.value;
			defaultCompany.replaceChildren();
			if (!chosen.length) {
				addOption(defaultCompany, "", __("Tick a company first"));
				return;
			}
			chosen.forEach((company) => addOption(defaultCompany, company, company));
			defaultCompany.value = chosen.includes(current) ? current : chosen[0];
		}

		function fill(member) {
			name.value = member ? member.full_name : "";
			email.value = member ? member.email : "";
			email.readOnly = !!member;
			mobile.value = member ? member.mobile || "" : "";
			ticks.querySelectorAll("input").forEach((box) => {
				box.checked = member ? (member.companies || []).includes(box.value) : false;
			});
			refreshDefault(member && member.default_company);
			role.value = member && member.role ? member.role : "";
			save.textContent = member ? __("Save changes") : __("Save");
			if (member) window.scrollTo({ top: 0, behavior: "smooth" });
		}

		function drawPeople(members) {
			list.replaceChildren();
			if (!members.length) {
				list.appendChild(el("p", "", __("No one yet.")));
				return;
			}
			members.forEach((member) => {
				const card = el("div", "melliflous-card");
				card.appendChild(el("div", "who", member.full_name || member.email));
				const bits = [member.email];
				if (member.role_label) bits.push(member.role_label);
				if (!member.enabled) bits.push(__("Off"));
				card.appendChild(el("div", "meta", bits.join(" · ")));
				if ((member.companies || []).length) {
					card.appendChild(el("div", "meta", member.companies.join(", ")));
				}
				const actions = el("div", "actions");
				const edit = el("button", "btn btn-default", __("Edit"));
				edit.type = "button";
				edit.addEventListener("click", () => fill(member));
				actions.appendChild(edit);
				card.appendChild(actions);
				list.appendChild(card);
			});
		}

		function loadPeople() {
			call(`${TEAM}.list_members`).then((response) => drawPeople(response.message || []));
		}

		clear.addEventListener("click", () => {
			note.clear();
			fill(null);
		});
		save.addEventListener("click", () => {
			note.clear();
			save.disabled = true;
			call(`${TEAM}.save_member`, {
				full_name: name.value,
				email: email.value,
				mobile: mobile.value,
				companies: ticked(),
				default_company: defaultCompany.value,
				role: role.value,
			})
				.then((response) => {
					note.show((response.message && response.message.message) || __("Saved."));
					fill(null);
					loadPeople();
				})
				.catch((error) => fail(error, note))
				.then(() => {
					save.disabled = false;
				});
		});

		call(`${TEAM}.form_options`)
			.then((response) => {
				const data = response.message || {};
				companies = data.companies || [];
				companies.forEach((company) => {
					const label = el("label", "company-tick");
					const box = el("input");
					box.type = "checkbox";
					box.value = company;
					box.addEventListener("change", () => refreshDefault());
					label.appendChild(box);
					label.appendChild(document.createTextNode(company));
					ticks.appendChild(label);
				});
				(data.roles || []).forEach((item) => addOption(role, item.key, item.label));
				loadPeople();
			})
			.catch((error) => fail(error, note));
	}

	function taskCards(parent, groups, onDone) {
		parent.replaceChildren();
		if (!groups.length) {
			parent.appendChild(el("p", "", __("No open tasks.")));
			return;
		}
		groups.forEach((group) => {
			parent.appendChild(el("h2", "", group.person));
			group.tasks.forEach((task) => {
				const card = el("div", "melliflous-card");
				card.appendChild(el("div", "", task.description || __("Task")));
				const when = el("div", task.overdue ? "meta is-overdue" : "meta");
				when.textContent = task.overdue
					? __("Overdue · {0}", [prettyDate(task.date)])
					: __("Due {0}", [prettyDate(task.date) || __("no date")]);
				if (task.priority) when.textContent += ` · ${task.priority}`;
				card.appendChild(when);
				if (task.can_close) {
					const actions = el("div", "actions");
					const done = el("button", "btn btn-primary", __("Mark done"));
					done.type = "button";
					done.addEventListener("click", () => onDone(task, done));
					actions.appendChild(done);
					card.appendChild(actions);
				}
				parent.appendChild(card);
			});
		});
	}

	function mountTasks(page, mineOnly) {
		const root = el("div", "melliflous-quick");
		page.main.empty().append(root);
		const note = banner(root);
		let person;
		let description;
		let due;
		let priority;
		let company;
		let kind;
		let recordSearch;
		let picked = "";
		const matches = el("div", "match-list");
		const pickedLine = el("div", "picked");

		if (!mineOnly) {
			person = field(root, __("Person"), select(__("Choose a person")));
			description = field(root, __("What to do"), el("textarea", "form-control"));
			description.rows = 4;
			due = field(root, __("Due date"), input("date"));
			due.value = tomorrow();
			priority = field(root, __("Priority"), select());
			["Low", "Medium", "High"].forEach((item) => addOption(priority, item, __(item)));
			priority.value = "Medium";
			company = field(root, __("Company (optional)"), select(__("No particular company")));
			kind = field(root, __("Link to a record (optional)"), select(__("No record")));
			recordSearch = field(root, __("Find the record"), input("search"));
			recordSearch.hidden = true;
			recordSearch.previousSibling.hidden = true;
			root.appendChild(matches);
			root.appendChild(pickedLine);
			const save = el("button", "btn btn-primary btn-save", __("Give task"));
			save.type = "button";
			root.appendChild(save);

			let timer = 0;
			kind.addEventListener("change", () => {
				picked = "";
				pickedLine.textContent = "";
				matches.replaceChildren();
				const show = !!kind.value;
				recordSearch.hidden = !show;
				recordSearch.previousSibling.hidden = !show;
				recordSearch.value = "";
			});
			recordSearch.addEventListener("input", () => {
				window.clearTimeout(timer);
				timer = window.setTimeout(() => {
					if (!kind.value) return;
					call(`${TASKS}.search_records`, { doctype: kind.value, text: recordSearch.value }).then(
						(response) => {
							matches.replaceChildren();
							(response.message || []).forEach((row) => {
								const button = el("button", "btn btn-default", row.name);
								button.type = "button";
								button.addEventListener("click", () => {
									picked = row.name;
									pickedLine.textContent = __("Attached: {0}", [row.name]);
									matches.replaceChildren();
								});
								matches.appendChild(button);
							});
						}
					);
				}, 300);
			});
			save.addEventListener("click", () => {
				note.clear();
				save.disabled = true;
				call(`${TASKS}.give_task`, {
					person: person.value,
					description: description.value,
					due_date: due.value,
					priority: priority.value,
					company: company.value,
					reference_type: kind.value,
					reference_name: picked,
				})
					.then((response) => {
						note.show((response.message && response.message.message) || __("Task given."));
						description.value = "";
						picked = "";
						pickedLine.textContent = "";
						kind.value = "";
						recordSearch.value = "";
						load();
					})
					.catch((error) => fail(error, note))
					.then(() => {
						save.disabled = false;
					});
			});
		}

		const heading = el("h2", "", mineOnly ? __("My tasks") : __("Open tasks"));
		root.appendChild(heading);
		const list = el("div");
		root.appendChild(list);

		function load() {
			call(`${TASKS}.list_tasks`, { mine: mineOnly ? 1 : 0 }).then((response) => {
				const data = response.message || {};
				if (!mineOnly && data.groups) {
					heading.textContent =
						person && person.options.length > 1 && !frappe.user.has_role("System Manager")
							? __("Tasks you gave")
							: __("Open tasks");
				}
				taskCards(list, data.groups || [], (task, button) => {
					button.disabled = true;
					call(`${TASKS}.close_task`, { name: task.name })
						.then((response) => {
							note.show((response.message && response.message.message) || __("Marked done."));
							load();
						})
						.catch((error) => {
							button.disabled = false;
							fail(error, note);
						});
				});
			});
		}

		if (!mineOnly) {
			call(`${TASKS}.form_options`)
				.then((response) => {
					const data = response.message || {};
					(data.people || []).forEach((item) => addOption(person, item.email, item.full_name));
					(data.companies || []).forEach((item) => addOption(company, item, item));
					(data.link_types || []).forEach((item) => addOption(kind, item, __(item)));
					if (data.due_date) due.value = data.due_date;
					load();
				})
				.catch((error) => fail(error, note));
		} else {
			load();
		}
	}

	function mountLead(page) {
		const root = el("div", "melliflous-quick");
		page.main.empty().append(root);
		const note = banner(root);
		const name = field(root, __("Name"), input("text"));
		const mobile = field(root, __("Mobile"), input("tel"));
		const shop = field(root, __("Shop or company"), input("text"));
		const city = field(root, __("City"), input("text"));
		const source = field(root, __("Source"), select());
		const assign = field(root, __("Assign to"), select(__("Me")));
		const follow = field(root, __("Next follow-up"), input("date"));
		follow.value = tomorrow();
		const save = el("button", "btn btn-primary btn-save", __("Save lead"));
		save.type = "button";
		root.appendChild(save);
		root.appendChild(el("h2", "", __("My follow-ups today and overdue")));
		const list = el("div");
		root.appendChild(list);

		function load() {
			call(`${LEADS}.my_follow_ups`).then((response) => {
				const rows = (response.message && response.message.follow_ups) || [];
				list.replaceChildren();
				if (!rows.length) {
					list.appendChild(el("p", "", __("Nothing due.")));
					return;
				}
				rows.forEach((row) => {
					const card = el("div", "melliflous-card");
					card.appendChild(el("div", "who", row.title || __("Lead")));
					const bits = [];
					if (row.shop) bits.push(row.shop);
					if (row.city) bits.push(row.city);
					if (bits.length) card.appendChild(el("div", "meta", bits.join(" · ")));
					const when = el("div", row.overdue ? "meta is-overdue" : "meta");
					when.textContent = row.overdue
						? __("Overdue · {0}", [prettyDate(row.date)])
						: __("Due {0}", [prettyDate(row.date)]);
					card.appendChild(when);
					const actions = el("div", "actions");
					if (row.tel) {
						const callLink = el("a", "btn btn-default", __("Call"));
						callLink.href = row.tel;
						actions.appendChild(callLink);
					}
					if (row.whatsapp) {
						const whatsapp = el("a", "btn btn-default", __("WhatsApp"));
						whatsapp.href = row.whatsapp;
						whatsapp.target = "_blank";
						whatsapp.rel = "noopener";
						actions.appendChild(whatsapp);
					}
					const done = el("button", "btn btn-primary", __("Mark done"));
					done.type = "button";
					done.addEventListener("click", () => {
						done.disabled = true;
						call(`${TASKS}.close_task`, { name: row.name })
							.then(() => load())
							.catch((error) => {
								done.disabled = false;
								fail(error, note);
							});
					});
					actions.appendChild(done);
					card.appendChild(actions);
					list.appendChild(card);
				});
			});
		}

		save.addEventListener("click", () => {
			note.clear();
			save.disabled = true;
			call(`${LEADS}.save_lead`, {
				full_name: name.value,
				mobile: mobile.value,
				shop: shop.value,
				city: city.value,
				source: source.value,
				assign_to: assign.value,
				follow_up: follow.value,
			})
				.then((response) => {
					note.show((response.message && response.message.message) || __("Lead saved."));
					name.value = "";
					mobile.value = "";
					shop.value = "";
					city.value = "";
					load();
				})
				.catch((error) => fail(error, note))
				.then(() => {
					save.disabled = false;
				});
		});

		call(`${LEADS}.form_options`)
			.then((response) => {
				const data = response.message || {};
				(data.sources || []).forEach((item) => addOption(source, item, __(item)));
				source.value = "Field Visit";
				(data.people || []).forEach((item) => addOption(assign, item.email, item.full_name));
				if (data.follow_up) follow.value = data.follow_up;
				load();
			})
			.catch((error) => fail(error, note));
	}

	return { mountTeam, mountTasks, mountLead };
})();
