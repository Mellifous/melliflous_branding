// Simple screens for Quick Actions. Loaded on every desk page, used by the
// standard pages. Server methods check permission again.
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

	const FILES = "melliflous_branding.team_files";

	function plain(text) {
		return String(text || "")
			.replace(/<[^>]*>/g, "")
			.trim();
	}

	function messageFrom(payload) {
		if (payload && payload._server_messages) {
			try {
				const messages = JSON.parse(payload._server_messages);
				const first = JSON.parse(messages[0]);
				if (first && first.message) return plain(first.message);
			} catch (error) {
				/* fall through */
			}
		}
		return __("Something went wrong. Please try again.");
	}

	function fileHref(name, inline) {
		const params = new URLSearchParams({ name: name, inline: inline ? "1" : "0" });
		return `/api/method/${FILES}.download?${params}`;
	}

	function mountFiles(page) {
		const main = page && page.main;
		if (main && main.find && main.find(".melliflous-quick").length) return;
		const root = el("div", "melliflous-quick");
		page.main.empty().append(root);
		const userType = frappe.boot && frappe.boot.user && frappe.boot.user.user_type;
		if (userType && userType !== "System User") {
			root.appendChild(el("p", "", __("You are not allowed to do this.")));
			return;
		}
		const note = banner(root);
		const zone = el("div", "dropzone");
		zone.appendChild(el("p", "", __("Drop a file here, or choose one.")));
		const folder = field(zone, __("Folder"), select());
		addOption(folder, "", __("General"));
		const choose = el("button", "btn btn-primary btn-save", __("Choose files"));
		choose.type = "button";
		const picker = el("input");
		picker.type = "file";
		picker.multiple = true;
		picker.hidden = true;
		zone.appendChild(choose);
		zone.appendChild(picker);
		root.appendChild(zone);
		root.appendChild(el("p", "hint", __("Everyone on the desk can open these files.")));

		const search = field(root, __("Search"), input("search"));
		search.placeholder = __("Name or folder");
		const chips = el("div", "chips");
		root.appendChild(chips);
		root.appendChild(el("h2", "", __("Files")));
		const list = el("div");
		root.appendChild(list);

		let activeTag = "All";
		let timer = 0;
		let requestId = 0;

		function drawChips(tags) {
			chips.replaceChildren();
			const choices = ["All", "General"].concat(tags || []);
			choices.forEach((tag) => {
				const button = el("button", "btn btn-default", __(tag));
				button.type = "button";
				button.classList.toggle("is-on", tag === activeTag);
				button.addEventListener("click", () => {
					activeTag = tag;
					drawChips(tags);
					load();
				});
				chips.appendChild(button);
			});
		}

		function drawFiles(rows) {
			list.replaceChildren();
			if (!rows.length) {
				list.appendChild(
					el(
						"p",
						"",
						search.value.trim() || activeTag !== "All" ? __("Nothing matches.") : __("No files yet.")
					)
				);
				return;
			}
			rows.forEach((row) => {
				const card = el("div", "melliflous-card");
				card.appendChild(el("div", "who", row.file_name || __("File")));
				const bits = [row.tag_label || __("General"), row.size_label || ""];
				if (row.uploader) bits.push(row.uploader);
				if (row.added) bits.push(prettyDate(row.added));
				card.appendChild(el("div", "meta", bits.filter(Boolean).join(" · ")));
				if (row.is_image) {
					const image = el("img", "file-preview");
					image.alt = row.file_name || "";
					image.src = fileHref(row.name, true);
					card.appendChild(image);
				}
				const actions = el("div", "actions");
				const download = el("a", "btn btn-default", __("Download"));
				download.href = fileHref(row.name, false);
				actions.appendChild(download);
				if (row.can_preview) {
					const preview = el("a", "btn btn-default", __("Preview"));
					preview.href = fileHref(row.name, true);
					preview.target = "_blank";
					preview.rel = "noopener";
					actions.appendChild(preview);
				}
				if (row.can_delete) {
					const remove = el("button", "btn btn-default", __("Delete"));
					remove.type = "button";
					remove.addEventListener("click", () => {
						if (!window.confirm(__("Delete this file?"))) return;
						remove.disabled = true;
						call(`${FILES}.delete_file`, { name: row.name })
							.then((response) => {
								note.show((response.message && response.message.message) || __("Deleted."));
								load();
							})
							.catch((error) => {
								remove.disabled = false;
								fail(error, note);
							});
					});
					actions.appendChild(remove);
				}
				card.appendChild(actions);
				list.appendChild(card);
			});
		}

		function load() {
			const current = ++requestId;
			return call(`${FILES}.list_files`, { search: search.value, tag: activeTag })
				.then((response) => {
					if (current !== requestId) return;
					drawFiles((response.message && response.message.files) || []);
				})
				.catch((error) => {
					if (current !== requestId) return;
					fail(error, note);
				});
		}

		function uploadOne(file) {
			const body = new FormData();
			body.append("file", file, file.name);
			body.append("tag", folder.value || "");
			body.append("is_private", "1");
			return fetch(`/api/method/${FILES}.upload`, {
				method: "POST",
				headers: {
					Accept: "application/json",
					"X-Frappe-CSRF-Token": frappe.csrf_token,
				},
				body,
			}).then(async (response) => {
				const payload = await response.json().catch(() => ({}));
				if (!response.ok) throw new Error(messageFrom(payload));
				return payload.message;
			});
		}

		async function uploadAll(fileList) {
			const files = Array.from(fileList || []).filter((file) => file && file.name);
			if (!files.length) return;
			if (files.length > 20) {
				note.show(__("Choose up to 20 files at a time."), true);
				return;
			}
			note.clear();
			choose.disabled = true;
			let failed = "";
			for (let index = 0; index < files.length; index += 1) {
				note.show(__("Uploading {0} of {1}…", [String(index + 1), String(files.length)]));
				try {
					await uploadOne(files[index]);
				} catch (error) {
					failed = (error && error.message) || __("Something went wrong. Please try again.");
					break;
				}
			}
			choose.disabled = false;
			picker.value = "";
			await load();
			if (failed) note.show(failed, true);
			else note.show(__("Uploaded."));
		}

		choose.addEventListener("click", () => picker.click());
		picker.addEventListener("change", () => uploadAll(picker.files));
		["dragenter", "dragover"].forEach((eventName) => {
			zone.addEventListener(eventName, (event) => {
				event.preventDefault();
				zone.classList.add("is-over");
			});
		});
		zone.addEventListener("dragleave", () => zone.classList.remove("is-over"));
		zone.addEventListener("drop", (event) => {
			event.preventDefault();
			zone.classList.remove("is-over");
			uploadAll(event.dataTransfer && event.dataTransfer.files);
		});
		search.addEventListener("input", () => {
			window.clearTimeout(timer);
			timer = window.setTimeout(load, 250);
		});

		call(`${FILES}.form_options`)
			.then((response) => {
				const tags = (response.message && response.message.tags) || [];
				tags.forEach((tag) => addOption(folder, tag, __(tag)));
				drawChips(tags);
				return load();
			})
			.catch((error) => fail(error, note));
	}

	function onQuickHome() {
		if (!window.frappe || !frappe.get_route) return false;
		const route = frappe.get_route() || [];
		if (!route.length) return false;
		const name = route[route.length - 1];
		return name === "Quick Actions" && (route[0] === "Workspaces" || route[0] === "quick-actions");
	}

	function quickActionsSection() {
		const page = document.getElementById("page-Workspaces");
		if (page && !page.classList.contains("hidden")) {
			const section = page.querySelector(".layout-main-section");
			if (section) return section;
		}
		if (!onQuickHome()) return null;
		return (
			Array.from(document.querySelectorAll(".layout-main-section")).find(
				(node) => node.offsetParent !== null
			) || null
		);
	}

	function tileIcon(kind) {
		const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
		svg.setAttribute("viewBox", "0 0 24 24");
		svg.setAttribute("aria-hidden", "true");
		const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
		path.setAttribute("fill", "none");
		path.setAttribute("stroke", "currentColor");
		path.setAttribute("stroke-width", "1.8");
		path.setAttribute("stroke-linecap", "round");
		path.setAttribute("stroke-linejoin", "round");
		path.setAttribute(
			"d",
			kind === "chat"
				? "M5 6.5h14v8.2H8.2L5 17.5z"
				: "M4 7.5h6l2 2h8v8.2H4z"
		);
		svg.appendChild(path);
		return svg;
	}

	function teamTile(href, label, hint, kind) {
		const link = el("a", `melliflous-tile melliflous-tile-${kind}`);
		link.href = href;
		const icon = el("span", "melliflous-tile-icon");
		icon.appendChild(tileIcon(kind));
		link.appendChild(icon);
		link.appendChild(el("span", "melliflous-tile-label", label));
		link.appendChild(el("span", "melliflous-tile-hint", hint));
		return link;
	}

	function teamTiles() {
		const wrap = el("div", "melliflous-tiles");
		wrap.appendChild(teamTile("/raven", __("Team Chat"), __("Message the team"), "chat"));
		wrap.appendChild(
			teamTile("/desk/team-files", __("Team Files"), __("Share a file"), "files")
		);
		return wrap;
	}

	function hideDuplicateRows(section) {
		const wanted = { "Team Chat": true, "Team Files": true };
		section.querySelectorAll(".ce-block, .shortcut-widget-box, .widget").forEach((node) => {
			if (node.closest(".melliflous-tiles")) return;
			const named = (node.getAttribute("shortcut_name") || node.getAttribute("aria-label") || "").trim();
			const title = node.querySelector(".widget-title-text, .widget-title");
			const label = named || (title ? title.textContent.replace(/\s+/g, " ").trim() : "");
			if (!wanted[label]) return;
			(node.closest(".ce-block") || node).classList.add("melliflous-tile-duplicate");
		});
	}

	function decorateQuickHome() {
		const home = onQuickHome();
		document.body.classList.toggle("melliflous-quick-home", home);
		if (!home) return;
		const section = quickActionsSection();
		if (!section) return;
		if (!section.querySelector(".melliflous-tiles")) {
			section.prepend(teamTiles());
		}
		hideDuplicateRows(section);
	}

	function showTeamFiles() {
		const route = (window.frappe && frappe.get_route && frappe.get_route()) || [];
		if (route[0] !== "team-files") return;
		const wrapper = frappe.pages && frappe.pages["team-files"];
		if (!wrapper || wrapper.querySelector(".melliflous-quick")) return;
		if (!(window.melliflous_quick && melliflous_quick.mountFiles)) return;
		const page =
			wrapper.page ||
			frappe.ui.make_app_page({
				parent: wrapper,
				title: __("Team Files"),
				single_column: true,
			});
		melliflous_quick.mountFiles(page);
	}

	let quickHomeTimer = 0;
	function scheduleQuickHome() {
		window.clearTimeout(quickHomeTimer);
		quickHomeTimer = window.setTimeout(decorateQuickHome, 40);
	}

	function scheduleDeskPages() {
		scheduleQuickHome();
		showTeamFiles();
	}

	// A visit while migrate was still importing this page stores an empty script
	// in the browser. Drop it so the next open reads the file from the app.
	try {
		localStorage.removeItem("_page:team-files");
	} catch (error) {
		/* private browsing */
	}

	if (window.frappe && frappe.router && frappe.router.on) {
		frappe.router.on("change", scheduleDeskPages);
	}
	if (window.jQuery) {
		window.jQuery(document).on("page-change", scheduleDeskPages);
	}
	document.addEventListener(
		"click",
		(event) => {
			if (!onQuickHome()) return;
			const box = event.target.closest && event.target.closest('[shortcut_name="Team Chat"]');
			if (!box || (event.target.closest && event.target.closest(".melliflous-tiles"))) return;
			event.preventDefault();
			event.stopPropagation();
			window.location.assign("/raven");
		},
		true
	);
	if (window.MutationObserver && document.body) {
		new MutationObserver(scheduleDeskPages).observe(document.body, {
			childList: true,
			subtree: true,
		});
	}
	scheduleDeskPages();

	return { mountTeam, mountTasks, mountLead, mountFiles };
})();
