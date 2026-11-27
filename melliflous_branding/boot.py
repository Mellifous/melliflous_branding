# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Desk boot payload and the PWA tags injected into /desk HTML."""

from __future__ import annotations

import frappe

from melliflous_branding.branding import (
	BUNDLED_ICON,
	FALLBACK_TITLE,
	HOME_SCREEN_NAME,
	MANIFEST_PATH,
	SITE_ICON,
	TILE_TONES,
	choose_company,
	display_title,
	inject_head_markup,
	picker_visible,
)
from melliflous_branding.companies import get_permitted_companies
from melliflous_branding.distributors import place_distributor_360_app
from melliflous_branding.simple_records import apply_simple_boot


def boot_session(bootinfo):
	"""Add the company switcher payload. Registered on extend_bootinfo and boot_session.

	`frappe.sessions.get` calls `extend_bootinfo` with `bootinfo=` on every desk
	boot, including a cached bootinfo. `frappe.boot.get_bootinfo` still calls
	`boot_session` positionally. One function serves both.
	"""
	try:
		bootinfo.melliflous_branding = branding_boot()
	except Exception:
		frappe.logger("melliflous_branding").exception("Could not build the branding boot payload")
		bootinfo.melliflous_branding = _empty_boot()
	# The apps grid is boot.app_data. Frappe fills it from the first
	# add_to_apps_screen entry of each installed app. Quick Actions is not a tile.
	# Distributor 360 is added here, on every boot including a cached one, and a
	# cached Quick Actions row is removed in the same pass.
	try:
		user = getattr(frappe.session, "user", None)
		try:
			roles = frappe.get_roles(user) if user else []
		except Exception:
			roles = []
		bootinfo.app_data = place_distributor_360_app(getattr(bootinfo, "app_data", None), user, roles)
	except Exception:
		frappe.logger("melliflous_branding").exception("Could not add Distributor 360 to the apps screen")
	# Simple mode filters the grid and the sidebars on every boot, including a
	# cached one, so a pull that did not migrate still hides the extra modules.
	try:
		apply_simple_boot(bootinfo)
	except Exception:
		frappe.logger("melliflous_branding").exception("Could not apply the simple desk")
	try:
		from melliflous_branding.invoice_admin_records import apply_invoice_boot

		apply_invoice_boot(bootinfo)
	except Exception:
		frappe.logger("melliflous_branding").exception("Could not apply invoice admin")


def branding_boot() -> dict:
	companies = get_permitted_companies()
	saved = None
	if frappe.session.user and frappe.session.user != "Guest":
		saved = frappe.defaults.get_user_default("company")
		if isinstance(saved, (list, tuple)):
			saved = next((value for value in saved if value), None)
	chosen = choose_company(None if saved is None else str(saved), companies)
	scope = {"divisions": [], "division": None}
	try:
		from melliflous_branding.division_records import divisions_for_boot

		scope = divisions_for_boot(chosen)
	except Exception:
		frappe.logger("melliflous_branding").exception("Could not load divisions")
	return {
		"companies": companies,
		"company": chosen,
		"divisions": scope["divisions"],
		"division": scope["division"],
		"title": display_title(chosen),
		"show_picker": picker_visible(companies) or bool(scope["divisions"]),
		"fallback": FALLBACK_TITLE,
		"tones": TILE_TONES,
		"icon": SITE_ICON,
		"fallback_icon": BUNDLED_ICON,
		"manifest": MANIFEST_PATH,
		"home_screen_name": HOME_SCREEN_NAME,
	}


def inject_pwa_head(response=None, request=None):
	"""Put the apple touch icon, manifest, and home-screen title into desk HTML.

	Desk has no head-include hook. `after_request` is how Frappe itself adds
	markup to an HTML response, and iOS reads these tags from the document
	rather than from tags inserted later by script.
	"""
	try:
		if not _is_desk_html(request, response):
			return
		html = response.get_data(as_text=True)
		if not html:
			return
		title = FALLBACK_TITLE
		try:
			title = branding_boot()["title"]
		except Exception:
			frappe.logger("melliflous_branding").exception("Using the fallback desk title")
		updated = inject_head_markup(html, title)
		if updated != html:
			response.set_data(updated)
	except Exception:
		frappe.logger("melliflous_branding").exception("Could not inject the desk PWA head")


def _is_desk_html(request, response) -> bool:
	if request is None or response is None:
		return False
	if getattr(request, "method", "") != "GET":
		return False
	if getattr(response, "status_code", 0) != 200:
		return False
	if getattr(response, "mimetype", "") != "text/html":
		return False
	path = getattr(request, "path", "") or ""
	return path == "/desk" or path.startswith("/desk/")


def _empty_boot() -> dict:
	return {
		"companies": [],
		"company": None,
		"divisions": [],
		"division": None,
		"title": FALLBACK_TITLE,
		"show_picker": False,
		"fallback": FALLBACK_TITLE,
		"tones": TILE_TONES,
		"icon": SITE_ICON,
		"fallback_icon": BUNDLED_ICON,
		"manifest": MANIFEST_PATH,
		"home_screen_name": HOME_SCREEN_NAME,
	}
