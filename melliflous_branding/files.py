# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Rules for Team Files. No Frappe import, so the checks can be tested on their own."""

from __future__ import annotations

TEAM_FOLDER = "Home/Team Files"
TAGS = ("Sales", "Accounts", "HR", "Plant", "Marketing")
GENERAL = "General"
PRIVATE_PREFIX = "/private/files/"

IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})
PREVIEW_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf"}
CONTENT_TYPES = {
	".png": "image/png",
	".jpg": "image/jpeg",
	".jpeg": "image/jpeg",
	".gif": "image/gif",
	".webp": "image/webp",
	".pdf": "application/pdf",
	".txt": "text/plain; charset=utf-8",
	".csv": "text/csv; charset=utf-8",
	".doc": "application/msword",
	".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
	".xls": "application/vnd.ms-excel",
	".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
	".ppt": "application/vnd.ms-powerpoint",
	".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
	".mp4": "video/mp4",
	".mp3": "audio/mpeg",
	".zip": "application/zip",
}


def is_truthy_flag(value) -> bool:
	return value in (1, True, "1")


def is_team_folder(folder: str | None) -> bool:
	"""The team folder itself, or one of its known tag folders. Nothing else."""
	text = (folder or "").strip().rstrip("/")
	if text == TEAM_FOLDER:
		return True
	prefix = TEAM_FOLDER + "/"
	if not text.startswith(prefix):
		return False
	return text[len(prefix) :] in TAGS


def clean_tag(value: str | None) -> str:
	"""A known tag, or blank for the team folder itself.

	Raises ValueError for anything else, including path pieces.
	"""
	if value is None:
		return ""
	if not isinstance(value, str):
		raise ValueError("Choose a folder from the list, or leave it blank.")
	text = value.strip()
	if not text or text.casefold() == GENERAL.casefold():
		return ""
	for tag in TAGS:
		if tag.casefold() == text.casefold():
			return tag
	raise ValueError("Choose a folder from the list, or leave it blank.")


def folder_for_tag(value: str | None) -> str:
	tag = clean_tag(value)
	if not tag:
		return TEAM_FOLDER
	return f"{TEAM_FOLDER}/{tag}"


def list_folders(tag: str | None) -> list[str]:
	"""Folders a list or search is allowed to read. Never anything outside Team Files."""
	if tag is None or (isinstance(tag, str) and (not tag.strip() or tag.strip().casefold() == "all")):
		return [TEAM_FOLDER, *[f"{TEAM_FOLDER}/{name}" for name in TAGS]]
	if isinstance(tag, str) and tag.strip().casefold() == GENERAL.casefold():
		return [TEAM_FOLDER]
	return [folder_for_tag(tag)]


def tag_from_folder(folder: str | None) -> str:
	text = (folder or "").strip().rstrip("/")
	prefix = TEAM_FOLDER + "/"
	if text.startswith(prefix) and text[len(prefix) :] in TAGS:
		return text[len(prefix) :]
	return ""


def tag_label(tag: str | None) -> str:
	return tag or GENERAL


def must_be_private(folder: str | None, is_folder) -> bool:
	"""Files saved into Team Files stay private. Folders are left alone."""
	if is_truthy_flag(is_folder):
		return False
	return is_team_folder(folder)


def local_private_file_url(file_url: str | None) -> str:
	"""A single file inside /private/files, or blank when the URL is not that."""
	text = (file_url or "").strip()
	if not text.startswith(PRIVATE_PREFIX):
		return ""
	name = text[len(PRIVATE_PREFIX) :]
	if not name or name in {".", ".."}:
		return ""
	if any(piece in name for piece in ("/", "\\", "..", "\x00", "%", "?", "#")):
		return ""
	return PRIVATE_PREFIX + name


def valid_file_id(name: str | None) -> bool:
	text = (name or "").strip()
	if not text or text != name or len(text) > 40:
		return False
	return all(character.isalnum() or character in {"-", "_"} for character in text)


def safe_display_name(file_name: str | None) -> str:
	text = (file_name or "").replace("\\", "/").split("/")[-1].replace("\x00", "").strip()
	if not text or text in {".", ".."}:
		return "file"
	return text


def extension_of(file_name: str | None) -> str:
	name = safe_display_name(file_name).lower()
	if "." not in name or name.startswith("."):
		return ""
	return "." + name.rsplit(".", 1)[-1]


def content_type_for(file_name: str | None) -> str:
	return CONTENT_TYPES.get(extension_of(file_name), "application/octet-stream")


def is_image(file_name: str | None) -> bool:
	return extension_of(file_name) in IMAGE_EXTENSIONS


def can_preview(file_name: str | None) -> bool:
	return extension_of(file_name) in PREVIEW_EXTENSIONS


def wants_inline(value, file_name: str | None) -> bool:
	if not can_preview(file_name):
		return False
	return str(value or "").strip().lower() in {"1", "true", "yes"}


def file_size_bytes(size) -> int:
	try:
		number = int(size or 0)
	except (TypeError, ValueError):
		return 0
	return max(number, 0)


def format_size(size) -> str:
	number = file_size_bytes(size)
	if number < 1024:
		return f"{number} B"
	if number < 1024 * 1024:
		value, unit = number / 1024, "KB"
	else:
		value, unit = number / (1024 * 1024), "MB"
	text = f"{value:.1f}".rstrip("0").rstrip(".")
	return f"{text} {unit}"


def added_on(value) -> str:
	text = str(value or "")
	return text[:10] if len(text) >= 10 else text


def search_match(file_name: str | None, tag: str | None, query: str | None) -> bool:
	text = (query or "").strip().casefold()
	if not text:
		return True
	haystack = f"{file_name or ''} {tag_label(tag)}".casefold()
	return text in haystack


def can_delete_file(owner: str | None, actor: str | None, system_manager: bool) -> bool:
	if system_manager:
		return True
	left = (owner or "").strip().casefold()
	right = (actor or "").strip().casefold()
	return bool(left) and left == right


def files_for_team(rows: list[dict], search: str | None = None, tag: str | None = None) -> list[dict]:
	"""Keep only private, unattached files that live in the requested team folder."""
	allowed = set(list_folders(tag))
	found: list[dict] = []
	for row in rows:
		folder = (row.get("folder") or "").strip()
		if folder not in allowed or not is_team_folder(folder):
			continue
		if is_truthy_flag(row.get("is_folder")):
			continue
		if (row.get("attached_to_doctype") or "").strip():
			continue
		if not is_truthy_flag(row.get("is_private")):
			continue
		if not local_private_file_url(row.get("file_url")):
			continue
		row_tag = tag_from_folder(folder)
		if not search_match(row.get("file_name"), row_tag, search):
			continue
		found.append(row)
	return found


def public_file(row: dict, actor: str | None, system_manager: bool, uploader: str | None) -> dict:
	"""What the desk page is allowed to see. No file URL and no folder path."""
	tag = tag_from_folder(row.get("folder"))
	file_name = safe_display_name(row.get("file_name"))
	return {
		"name": row.get("name") or "",
		"file_name": file_name,
		"size": file_size_bytes(row.get("file_size")),
		"size_label": format_size(row.get("file_size")),
		"uploader": (uploader or "").strip() or (row.get("owner") or ""),
		"added": added_on(row.get("creation")),
		"tag": tag,
		"tag_label": tag_label(tag),
		"can_delete": can_delete_file(row.get("owner"), actor, system_manager),
		"can_preview": can_preview(file_name),
		"is_image": is_image(file_name),
	}


def present_files(
	rows: list[dict],
	search: str | None,
	tag: str | None,
	actor: str | None,
	system_manager: bool,
	uploaders: dict[str, str] | None = None,
) -> list[dict]:
	names = uploaders or {}
	shown = []
	for row in files_for_team(rows, search, tag):
		owner = row.get("owner") or ""
		shown.append(public_file(row, actor, system_manager, names.get(owner, owner)))
	return shown


def as_bytes(content) -> bytes:
	if content is None:
		return b""
	if isinstance(content, bytes):
		return content
	return str(content).encode("utf-8")
