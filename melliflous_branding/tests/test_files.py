# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt

import json
import unittest
from pathlib import Path

from melliflous_branding import hooks
from melliflous_branding.files import (
	TEAM_FOLDER,
	as_bytes,
	can_delete_file,
	clean_tag,
	content_type_for,
	files_for_team,
	folder_for_tag,
	format_size,
	is_team_folder,
	list_folders,
	local_private_file_url,
	must_be_private,
	present_files,
	valid_file_id,
	wants_inline,
)

PACKAGE = Path(__file__).resolve().parents[1]


def team_row(**overrides):
	row = {
		"name": "abc123def0",
		"file_name": "price-list.pdf",
		"file_size": 1536,
		"owner": "aj@example.com",
		"creation": "2026-11-26 09:30:00",
		"folder": TEAM_FOLDER,
		"is_private": 1,
		"is_folder": 0,
		"file_url": "/private/files/price-list.pdf",
		"attached_to_doctype": None,
	}
	row.update(overrides)
	return row


class TestTeamFolderRules(unittest.TestCase):
	def test_only_the_team_folder_and_its_tags_count(self):
		self.assertTrue(is_team_folder(TEAM_FOLDER))
		self.assertTrue(is_team_folder("Home/Team Files/Plant"))
		self.assertFalse(is_team_folder("Home"))
		self.assertFalse(is_team_folder("Home/Attachments"))
		self.assertFalse(is_team_folder("Home/Team Files/Secret"))
		self.assertFalse(is_team_folder("Home/Team Files/Sales/extra"))
		self.assertFalse(is_team_folder("Home/Team Files/../Attachments"))
		self.assertFalse(is_team_folder("Home/Team Files/sales"))

	def test_tag_is_a_fixed_list(self):
		self.assertEqual(clean_tag(""), "")
		self.assertEqual(clean_tag(" general "), "")
		self.assertEqual(clean_tag("accounts"), "Accounts")
		self.assertEqual(folder_for_tag("HR"), "Home/Team Files/HR")
		self.assertEqual(folder_for_tag(None), TEAM_FOLDER)
		for bad in ("../Home", "Home/Attachments", "Sales/extra", "All", 12):
			with self.assertRaises(ValueError):
				clean_tag(bad)

	def test_list_folders_never_leaves_team_files(self):
		self.assertEqual(
			list_folders("All"),
			[
				TEAM_FOLDER,
				"Home/Team Files/Sales",
				"Home/Team Files/Accounts",
				"Home/Team Files/HR",
				"Home/Team Files/Plant",
				"Home/Team Files/Marketing",
			],
		)
		self.assertEqual(list_folders("General"), [TEAM_FOLDER])
		self.assertEqual(list_folders("Marketing"), ["Home/Team Files/Marketing"])
		with self.assertRaises(ValueError):
			list_folders("../Home")

	def test_files_in_the_folder_are_forced_private(self):
		self.assertTrue(must_be_private(TEAM_FOLDER, 0))
		self.assertTrue(must_be_private("Home/Team Files/Sales", 0))
		self.assertTrue(must_be_private("Home/Team Files/Sales", "0"))
		self.assertFalse(must_be_private(TEAM_FOLDER, 1))
		self.assertFalse(must_be_private("Home/Attachments", 0))


class TestWhoCanSeeAFile(unittest.TestCase):
	def test_private_url_must_be_one_file_in_private_files(self):
		self.assertEqual(local_private_file_url("/private/files/price-list.pdf"), "/private/files/price-list.pdf")
		for bad in (
			"/files/price-list.pdf",
			"/private/files/../site_config.json",
			"/private/files/a/b.pdf",
			"/private/files/..",
			"https://example.com/private/files/a.pdf",
			"/private/files/a.pdf?x=1",
			"/private/files/%2e%2e",
			"",
		):
			self.assertEqual(local_private_file_url(bad), "")

	def test_outside_files_attached_files_and_public_files_are_dropped(self):
		rows = [
			team_row(),
			team_row(name="attach01", attached_to_doctype="Salary Slip"),
			team_row(name="public01", is_private=0, file_url="/files/public.pdf"),
			team_row(name="other01", folder="Home/Attachments", file_url="/private/files/secret.pdf"),
			team_row(name="remote01", file_url="https://example.com/private/files/a.pdf"),
			team_row(name="folder01", is_folder=1),
		]
		kept = files_for_team(rows)
		self.assertEqual([row["name"] for row in kept], ["abc123def0"])

	def test_search_and_tag_filter(self):
		rows = [
			team_row(file_name="van-route.pdf"),
			team_row(
				name="sales01",
				file_name="orders.xlsx",
				folder="Home/Team Files/Sales",
				file_url="/private/files/orders.xlsx",
			),
		]
		self.assertEqual(len(files_for_team(rows, search="van")), 1)
		self.assertEqual(len(files_for_team(rows, search="sales")), 1)
		self.assertEqual(len(files_for_team(rows, tag="General")), 1)
		self.assertEqual(files_for_team(rows, tag="Sales")[0]["name"], "sales01")
		self.assertEqual(files_for_team(rows, search="nothing"), [])

	def test_the_page_does_not_receive_the_file_url(self):
		shown = present_files(
			[team_row(), team_row(name="other01", folder="Home", file_url="/private/files/other.pdf")],
			None,
			"All",
			"priya@example.com",
			False,
			{"aj@example.com": "AJ"},
		)
		self.assertEqual(len(shown), 1)
		self.assertEqual(shown[0]["uploader"], "AJ")
		self.assertEqual(shown[0]["tag_label"], "General")
		self.assertEqual(shown[0]["size_label"], "1.5 KB")
		self.assertFalse(shown[0]["can_delete"])
		self.assertTrue(shown[0]["can_preview"])
		self.assertNotIn("file_url", shown[0])
		self.assertNotIn("folder", shown[0])
		self.assertNotIn("attached_to_doctype", shown[0])

	def test_delete_is_the_uploader_or_a_system_manager(self):
		self.assertTrue(can_delete_file("AJ@example.com", "aj@example.com", False))
		self.assertFalse(can_delete_file("aj@example.com", "priya@example.com", False))
		self.assertTrue(can_delete_file("aj@example.com", "priya@example.com", True))
		self.assertFalse(can_delete_file("", "priya@example.com", False))

	def test_preview_is_images_and_pdf_only(self):
		self.assertTrue(wants_inline("1", "photo.PNG"))
		self.assertTrue(wants_inline("yes", "note.pdf"))
		self.assertFalse(wants_inline("1", "page.html"))
		self.assertFalse(wants_inline("1", "logo.svg"))
		self.assertFalse(wants_inline("0", "note.pdf"))
		self.assertEqual(content_type_for("page.html"), "application/octet-stream")
		self.assertEqual(content_type_for("photo.jpg"), "image/jpeg")

	def test_file_ids_and_sizes(self):
		self.assertTrue(valid_file_id("abc123def0"))
		self.assertFalse(valid_file_id("../secret"))
		self.assertFalse(valid_file_id("abc 123"))
		self.assertFalse(valid_file_id(" abc"))
		self.assertEqual(format_size(0), "0 B")
		self.assertEqual(format_size(1024), "1 KB")
		self.assertEqual(format_size(1024 * 1024), "1 MB")
		self.assertEqual(as_bytes(None), b"")
		self.assertEqual(as_bytes("hi"), b"hi")
		self.assertEqual(as_bytes(b"hi"), b"hi")


class TestShippedDesk(unittest.TestCase):
	def test_hooks_create_the_folder_and_keep_files_private(self):
		self.assertEqual(hooks.after_install, "melliflous_branding.install.after_install")
		self.assertIn("melliflous_branding.install.after_migrate", hooks.after_migrate)
		self.assertEqual(
			hooks.doc_events["File"]["before_validate"],
			"melliflous_branding.team_files.keep_team_file_private",
		)
		patches = (PACKAGE / "patches.txt").read_text()
		self.assertIn("melliflous_branding.patches.v0_3.ensure_team_files", patches)

	def test_quick_actions_links_chat_and_files(self):
		workspace = json.loads(
			(PACKAGE / "melliflous_branding" / "workspace" / "quick_actions" / "quick_actions.json").read_text()
		)
		shortcuts = {row["label"]: row for row in workspace["shortcuts"]}
		self.assertEqual(shortcuts["Team Chat"]["type"], "URL")
		self.assertEqual(shortcuts["Team Chat"]["url"], "/raven")
		self.assertEqual(shortcuts["Team Files"]["type"], "Page")
		self.assertEqual(shortcuts["Team Files"]["link_to"], "team-files")
		labels = [block["data"]["shortcut_name"] for block in json.loads(workspace["content"])]
		self.assertEqual(labels[:2], ["Team Chat", "Team Files"])
		self.assertIn("team-files", {row.get("link_to") for row in workspace["links"]})

		page = json.loads(
			(PACKAGE / "melliflous_branding" / "page" / "team_files" / "team_files.json").read_text()
		)
		self.assertEqual(page["name"], "team-files")
		self.assertEqual(page["title"], "Team Files")

		sidebar = json.loads(
			(
				PACKAGE / "melliflous_branding" / "sidebar" / "melliflous_branding" / "melliflous_branding.json"
			).read_text()
		)
		items = {row["label"]: row for row in sidebar["items"]}
		self.assertEqual(items["Team Chat"]["url"], "/raven")
		self.assertEqual(items["Team Chat"]["open_in_new_tab"], 0)
		self.assertEqual(items["Team Files"]["link_to"], "team-files")
