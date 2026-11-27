# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Pure branding rules. No Frappe import, so the rules can be tested without a site."""

from __future__ import annotations

import html
import re

FALLBACK_TITLE = "Melliflous Group"
HOME_SCREEN_NAME = "Melliflous Group"
HOME_SCREEN_SHORT_NAME = "Melliflous"
SITE_ICON = "/files/melliflous_icon_512.png"
BUNDLED_ICON = "/assets/melliflous_branding/images/melliflous_icon_512.png"
MANIFEST_PATH = "/assets/melliflous_branding/manifest.json"
PWA_MARKER = "data-melliflous-pwa"

# English tile labels as v16 renders them. Department colours apply when that
# label is actually on screen (Desktop Icons grid, or a module folder on newer
# builds). App-screen tiles are mapped separately: ERPNext is one tile.
TILE_TONES: dict[str, str] = {
	"Accounts": "green",
	"Selling": "orange",
	"Field Sales": "orange",
	"CRM": "purple",
	"Frappe CRM": "purple",
	"Stock": "blue",
	"Buying": "teal",
	"Manufacturing": "brown",
	"HR": "pink",
	"Frappe HR": "pink",
	"Payroll": "yellow",
	"India Compliance": "red",
	"GST": "red",
	"GST India": "red",
	"ERPNext": "brand",
	"Distributor 360": "brand",
}


def display_title(company: str | None, fallback: str = FALLBACK_TITLE) -> str:
	"""Header and browser-tab title. A blank company falls back to the group name."""
	name = (company or "").strip()
	return name or fallback


def picker_visible(companies: list[str]) -> bool:
	"""The switcher is only for someone who can work in more than one company."""
	return len([company for company in companies if (company or "").strip()]) > 1


def choose_company(saved: str | None, companies: list[str]) -> str | None:
	"""The company to show. Keep a saved default that is still allowed.

	A single allowed company is shown even when nothing is saved. Several
	allowed companies and no saved default stay unset, so the header uses the
	group name until the user picks one.
	"""
	names = [company for company in companies if (company or "").strip()]
	saved = (saved or "").strip()
	if saved and saved in names:
		return saved
	if len(names) == 1:
		return names[0]
	return None


def companies_for_user(permission_names: list[str], readable_companies: list[str]) -> list[str]:
	"""Companies the picker may offer.

	User Permissions on Company restrict the list. With none, the user is
	unrestricted and sees every company they can read. Names are de-duplicated
	and sorted so the control is stable.
	"""
	permitted = _unique(permission_names)
	if permitted:
		known = set(_unique(readable_companies))
		# An empty readable list means we could not list Company (for example the
		# user cannot read the DocType). Keep the permission names in that case.
		if known:
			permitted = [name for name in permitted if name in known]
		return sorted(permitted, key=str.casefold)
	return sorted(_unique(readable_companies), key=str.casefold)


def tone_for(label: str | None, tones: dict[str, str] | None = None) -> str | None:
	"""Colour key for a desk tile label, or None when the tile stays neutral."""
	if not label:
		return None
	table = tones or TILE_TONES
	text = " ".join(label.split())
	if not text:
		return None
	if text in table:
		return table[text]
	folded = text.casefold()
	for key, tone in table.items():
		if key.casefold() == folded:
			return tone
	return None


def pwa_head_snippet(icon: str = SITE_ICON) -> str:
	"""Tags iOS reads when Add to Home Screen is used on a desk page."""
	primary = html.escape(icon or SITE_ICON, quote=True)
	fallback = html.escape(BUNDLED_ICON, quote=True)
	manifest = html.escape(MANIFEST_PATH, quote=True)
	title = html.escape(HOME_SCREEN_NAME, quote=True)
	marker = PWA_MARKER
	return (
		f'<link rel="apple-touch-icon" sizes="512x512" href="{primary}" {marker}="1">'
		f'<link rel="apple-touch-icon" sizes="512x512" href="{fallback}" {marker}="1">'
		f'<link rel="manifest" href="{manifest}" {marker}="1">'
		f'<meta name="apple-mobile-web-app-title" content="{title}" {marker}="1">'
	)


def inject_head_markup(document: str, title: str, icon: str = SITE_ICON) -> str:
	"""Insert the PWA tags and replace the shell <title> on a desk HTML response."""
	if not document or PWA_MARKER in document:
		return document
	safe_title = html.escape(display_title(title), quote=False)
	updated = re.sub(
		r"<title>.*?</title>",
		f"<title>{safe_title}</title>",
		document,
		count=1,
		flags=re.IGNORECASE | re.DOTALL,
	)
	snippet = pwa_head_snippet(icon)
	if "</head>" in updated:
		return updated.replace("</head>", snippet + "</head>", 1)
	return snippet + updated


def _unique(names: list[str]) -> list[str]:
	seen: set[str] = set()
	ordered: list[str] = []
	for name in names:
		cleaned = (name or "").strip()
		if not cleaned or cleaned in seen:
			continue
		seen.add(cleaned)
		ordered.append(cleaned)
	return ordered
