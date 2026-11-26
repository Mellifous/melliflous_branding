# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Team Files: a private folder the whole desk can open, inside Frappe's File list.

Uploads go through Frappe's upload_file. Every method checks the caller is a
desk user, and every read stays inside Home/Team Files.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from melliflous_branding.access import is_system_manager, require_desk_user
from melliflous_branding.files import (
	TAGS,
	TEAM_FOLDER,
	as_bytes,
	can_delete_file,
	content_type_for,
	files_for_team,
	folder_for_tag,
	is_team_folder,
	list_folders,
	local_private_file_url,
	must_be_private,
	present_files,
	safe_display_name,
	valid_file_id,
	wants_inline,
)

_OUTSIDE = "That file is not in Team Files."


def keep_team_file_private(doc, method=None):
	"""before_validate: a file placed in Team Files cannot be saved as public."""
	if must_be_private(getattr(doc, "folder", None), getattr(doc, "is_folder", 0)):
		doc.is_private = 1


def ensure_team_folders() -> str:
	"""Create Home/Team Files and the tag folders when they are missing."""
	_ensure_folder("Home", None, is_home=True)
	_ensure_folder("Team Files", "Home")
	for tag in TAGS:
		_ensure_folder(tag, TEAM_FOLDER)
	return TEAM_FOLDER


@frappe.whitelist()
def form_options() -> dict:
	require_desk_user()
	ensure_team_folders()
	return {"tags": list(TAGS), "folder": TEAM_FOLDER}


@frappe.whitelist()
def list_files(search: str | None = None, tag: str | None = None) -> dict:
	user = require_desk_user()
	ensure_team_folders()
	try:
		folders = list_folders(tag)
	except ValueError as error:
		frappe.throw(_(str(error)))
	rows = frappe.get_all(
		"File",
		filters={"is_folder": 0, "folder": ["in", folders]},
		fields=[
			"name",
			"file_name",
			"file_size",
			"owner",
			"creation",
			"folder",
			"is_private",
			"is_folder",
			"file_url",
			"attached_to_doctype",
		],
		order_by="creation desc",
		limit=500,
	)
	payload = [dict(row) for row in rows]
	return {
		"files": present_files(payload, search, tag, user, is_system_manager(), _uploader_names(payload)),
	}


@frappe.whitelist(methods=["POST"])
def upload(tag: str | None = None) -> dict:
	"""Store one upload in Team Files, private, not attached to any other record.

	The browser posts the file the same way as Frappe's upload_file. Folder,
	privacy, and attachment fields from the request are ignored.
	"""
	user = require_desk_user()
	if not frappe.has_permission("File", "create"):
		frappe.throw(_("You are not allowed to upload files."), frappe.PermissionError)
	try:
		folder = folder_for_tag(tag)
	except ValueError as error:
		frappe.throw(_(str(error)))
	if not is_team_folder(folder):
		frappe.throw(_(_OUTSIDE), frappe.PermissionError)
	ensure_team_folders()

	uploaded = getattr(getattr(frappe, "request", None), "files", None)
	if not uploaded or "file" not in uploaded:
		frappe.throw(_("Choose a file."))

	for key in (
		"doctype",
		"docname",
		"fieldname",
		"file_url",
		"library_file_name",
		"method",
		"optimize",
	):
		frappe.form_dict.pop(key, None)
	frappe.form_dict.folder = folder
	frappe.form_dict.is_private = 1

	from frappe.handler import upload_file as frappe_upload_file

	doc = frappe_upload_file()
	if doc is None:
		frappe.throw(_("The upload did not finish. Please try again."))
	row = frappe.db.get_value(
		"File",
		doc.name,
		[
			"name",
			"file_name",
			"file_size",
			"owner",
			"creation",
			"folder",
			"is_private",
			"is_folder",
			"file_url",
			"attached_to_doctype",
		],
		as_dict=True,
	)
	stored = dict(row) if row else None
	if not stored or (stored.get("folder") or "").strip() != folder or not files_for_team([stored]):
		frappe.throw(_("That file could not be stored in Team Files."))
	names = _uploader_names([stored])
	shown = present_files([stored], None, None, user, is_system_manager(), names)
	if not shown:
		frappe.throw(_("That file could not be stored in Team Files."))
	return {"file": shown[0], "message": _("Uploaded.")}


@frappe.whitelist()
def download(name: str | None = None, inline: str | int | None = 0):
	"""Send one team file. Desk users only, and only from the team folder."""
	require_desk_user()
	row = _team_row(name)
	doc = frappe.get_doc("File", row["name"])
	# Re-check the loaded document. get_doc does not apply File.has_permission
	# unless asked, and that check would hide the file from everyone but the
	# uploader. The folder check above is what shares it with the desk.
	if not files_for_team(
		[
			{
				"folder": doc.folder,
				"is_folder": doc.is_folder,
				"is_private": doc.is_private,
				"attached_to_doctype": doc.attached_to_doctype,
				"file_url": doc.file_url,
				"file_name": doc.file_name,
			}
		]
	):
		frappe.throw(_(_OUTSIDE), frappe.PermissionError)
	if not local_private_file_url(doc.file_url):
		frappe.throw(_(_OUTSIDE), frappe.PermissionError)

	file_name = safe_display_name(doc.file_name)
	frappe.local.response.filename = file_name
	frappe.local.response.filecontent = as_bytes(doc.get_content())
	frappe.local.response.type = "download"
	frappe.local.response.content_type = content_type_for(file_name)
	if wants_inline(inline, file_name):
		frappe.local.response.display_content_as = "inline"
	return


@frappe.whitelist(methods=["POST"])
def delete_file(name: str | None = None) -> dict:
	user = require_desk_user()
	row = _team_row(name)
	if not can_delete_file(row.get("owner"), user, is_system_manager()):
		frappe.throw(
			_("Only the person who uploaded this file can delete it."),
			frappe.PermissionError,
		)
	# File.has_permission only allows the owner (or Administrator) to delete a
	# private file. System Manager is allowed here, after the folder check.
	frappe.delete_doc("File", row["name"], ignore_permissions=True)
	return {"message": _("Deleted.")}


def _team_row(name: str | None) -> dict:
	if not valid_file_id(name):
		frappe.throw(_(_OUTSIDE), frappe.PermissionError)
	if not frappe.db.exists("File", name):
		frappe.throw(_(_OUTSIDE), frappe.PermissionError)
	row = frappe.db.get_value(
		"File",
		name,
		[
			"name",
			"file_name",
			"file_url",
			"folder",
			"is_folder",
			"owner",
			"is_private",
			"attached_to_doctype",
			"file_size",
			"creation",
		],
		as_dict=True,
	)
	if not row or not files_for_team([dict(row)]):
		frappe.throw(_(_OUTSIDE), frappe.PermissionError)
	return dict(row)


def _ensure_folder(file_name: str, parent: str | None, is_home: bool = False) -> str:
	name = f"{parent}/{file_name}" if parent else file_name
	current = frappe.db.get_value("File", name, ["name", "is_folder"], as_dict=True)
	if current:
		if not cint(current.is_folder):
			frappe.throw(_("{0} already exists and is not a folder.").format(name))
		return name
	doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"is_folder": 1,
			"folder": parent,
			"is_home_folder": 1 if is_home else 0,
		}
	)
	try:
		doc.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		return name
	return doc.name


def _uploader_names(rows) -> dict[str, str]:
	owners = {row.get("owner") if isinstance(row, dict) else row.owner for row in rows}
	owners.discard(None)
	owners.discard("")
	if not owners:
		return {}
	names = {owner: owner for owner in owners}
	for user in frappe.get_all(
		"User",
		filters={"name": ["in", list(owners)]},
		fields=["name", "full_name"],
		limit=0,
	):
		if user.full_name:
			names[user.name] = user.full_name
	return names
