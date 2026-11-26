// This file is what Frappe evals for the page. It does not call into the desk
// bundle: that file is cached separately, and a stale copy left the title up
// with an empty body. Folders are drawn immediately. The server creates
// Home/Team Files on the first call, and any failure is written into the page.
(function () {
	const FILES = "melliflous_branding.team_files";
	const FOLDERS = ["Sales", "Accounts", "HR", "Plant", "Marketing"];
	const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

	function el(tag, className, text) {
		const node = document.createElement(tag);
		if (className) node.className = className;
		if (text != null) node.textContent = text;
		return node;
	}

	function plain(text) {
		return String(text || "")
			.replace(/<[^>]*>/g, "")
			.trim();
	}

	function errorText(error) {
		const payload = (error && (error.responseJSON || error)) || {};
		if (payload._server_messages) {
			try {
				const messages = JSON.parse(payload._server_messages);
				const first = JSON.parse(messages[0]);
				if (first && first.message) return plain(first.message);
			} catch (ignored) {
				/* use the fallback below */
			}
		}
		if (payload.exception) {
			const parts = String(payload.exception).split(":");
			const last = plain(parts[parts.length - 1]);
			if (last) return last;
		}
		if (payload.message) return plain(payload.message);
		if (error && error.message) return plain(error.message);
		return __("Something went wrong. Please try again.");
	}

	function contentHost(page, wrapper) {
		if (page && page.main && page.main[0]) return page.main[0];
		return (
			wrapper.querySelector(".layout-main-section") ||
			wrapper.querySelector(".page-content") ||
			wrapper
		);
	}

	function prettyDate(iso) {
		if (!iso) return "";
		const parts = String(iso).split("-");
		if (parts.length < 3) return String(iso);
		return `${Number(parts[2])} ${MONTHS[Number(parts[1]) - 1] || ""} ${parts[0]}`;
	}

	function fileHref(name, inline) {
		const params = new URLSearchParams({ name: name, inline: inline ? "1" : "0" });
		return `/api/method/${FILES}.download?${params}`;
	}

	function render(page, wrapper) {
		const host = contentHost(page, wrapper);
		const root = el("div", "melliflous-quick");
		host.replaceChildren(root);

		const note = el("div", "banner");
		note.hidden = true;
		root.appendChild(note);
		function show(message, isError) {
			note.hidden = false;
			note.classList.toggle("is-error", !!isError);
			note.textContent = message;
		}

		const zone = el("div", "dropzone");
		zone.appendChild(el("p", "", __("Drop a file here, or choose one.")));
		root.appendChild(zone);
		const folderLabel = el("label", "", __("Folder"));
		const folder = el("select", "form-control");
		const general = el("option", "", __("General"));
		general.value = "";
		folder.appendChild(general);
		FOLDERS.forEach((tag) => {
			const option = el("option", "", __(tag));
			option.value = tag;
			folder.appendChild(option);
		});
		zone.appendChild(folderLabel);
		zone.appendChild(folder);
		const choose = el("button", "btn btn-primary btn-save", __("Choose files"));
		choose.type = "button";
		const picker = el("input");
		picker.type = "file";
		picker.multiple = true;
		picker.hidden = true;
		zone.appendChild(choose);
		zone.appendChild(picker);
		root.appendChild(el("p", "hint", __("Everyone on the desk can open these files.")));

		const searchLabel = el("label", "", __("Search"));
		const search = el("input", "form-control");
		search.type = "search";
		search.placeholder = __("Name or folder");
		root.appendChild(searchLabel);
		root.appendChild(search);

		const chips = el("div", "chips");
		root.appendChild(chips);
		root.appendChild(el("h2", "", __("Files")));
		const list = el("div");
		root.appendChild(list);

		let activeTag = "All";
		let timer = 0;
		let requestId = 0;

		function drawChips() {
			chips.replaceChildren();
			["All", "General"].concat(FOLDERS).forEach((tag) => {
				const button = el("button", "btn btn-default", __(tag));
				button.type = "button";
				button.classList.toggle("is-on", tag === activeTag);
				button.addEventListener("click", () => {
					activeTag = tag;
					drawChips();
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
						frappe
							.call({ method: `${FILES}.delete_file`, args: { name: row.name } })
							.then((response) => {
								show((response.message && response.message.message) || __("Deleted."));
								load();
							})
							.catch((error) => {
								remove.disabled = false;
								show(errorText(error), true);
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
			return frappe
				.call({ method: `${FILES}.list_files`, args: { search: search.value, tag: activeTag } })
				.then((response) => {
					if (current !== requestId) return;
					drawFiles((response.message && response.message.files) || []);
				})
				.catch((error) => {
					if (current !== requestId) return;
					show(errorText(error), true);
					if (!list.childNodes.length) {
						list.appendChild(el("p", "", __("The file list could not be loaded.")));
					}
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
				if (!response.ok) throw new Error(errorText(payload));
				return payload.message;
			});
		}

		async function uploadAll(fileList) {
			const files = Array.from(fileList || []).filter((file) => file && file.name);
			if (!files.length) return;
			if (files.length > 20) {
				show(__("Choose up to 20 files at a time."), true);
				return;
			}
			note.hidden = true;
			choose.disabled = true;
			let failed = "";
			for (let index = 0; index < files.length; index += 1) {
				show(__("Uploading {0} of {1}…", [String(index + 1), String(files.length)]));
				try {
					await uploadOne(files[index]);
				} catch (error) {
					failed = errorText(error);
					break;
				}
			}
			choose.disabled = false;
			picker.value = "";
			await load();
			if (failed) show(failed, true);
			else show(__("Uploaded."));
		}

		choose.addEventListener("click", () => picker.click());
		picker.addEventListener("change", () => uploadAll(picker.files));
		["dragenter", "dragover"].forEach((name) => {
			zone.addEventListener(name, (event) => {
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

		drawChips();
		// Creates Home/Team Files and the tag folders when they are missing.
		frappe
			.call({ method: `${FILES}.form_options` })
			.then(() => load())
			.catch((error) => {
				show(errorText(error), true);
				list.appendChild(el("p", "", __("The file list could not be loaded.")));
			});
	}

	window.melliflous_mount_team_files = function (page, wrapper) {
		render(page, wrapper || (page && page.wrapper && page.wrapper[0]) || page.parent);
	};

	frappe.pages["team-files"].on_page_load = function (wrapper) {
		try {
			const page = frappe.ui.make_app_page({
				parent: wrapper,
				title: __("Team Files"),
				single_column: true,
			});
			render(page, wrapper);
		} catch (error) {
			const host =
				wrapper.querySelector(".layout-main-section") ||
				wrapper.querySelector(".page-content") ||
				wrapper;
			const box = el("div", "melliflous-quick");
			const banner = el("div", "banner is-error", errorText(error));
			box.appendChild(banner);
			host.appendChild(box);
		}
	};
})();
