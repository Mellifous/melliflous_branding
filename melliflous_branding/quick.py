# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Plain rules for the Quick Actions pages. No Frappe import."""

from __future__ import annotations

from datetime import date, timedelta

PROTECTED_USERS = frozenset({"administrator", "guest"})

# Friendly job names and the desk roles they stand for. A role is applied only
# when that Role exists on the site, so a missing HRMS role does not block save.
ROLE_CHOICES: tuple[dict, ...] = (
	{
		"key": "owner",
		"label": "Owner / Admin",
		"roles": ("System Manager",),
		"profiles": ("Owner", "Admin"),
	},
	{
		"key": "accounts",
		"label": "Accounts",
		"roles": ("Accounts Manager", "Accounts User"),
		"profiles": ("Accounts", "Accounts Manager"),
	},
	{
		"key": "hr",
		"label": "HR",
		"roles": ("HR Manager", "HR User"),
		"profiles": ("HR", "HR Manager"),
	},
	{
		"key": "sales_manager",
		"label": "Sales Manager",
		"roles": ("Sales Manager", "Sales User"),
		"profiles": ("Sales Manager",),
	},
	{
		"key": "sales_rep",
		"label": "Sales Rep / Van",
		"roles": ("Sales User",),
		"profiles": ("Sales", "Sales User", "Van Sales"),
	},
	{
		"key": "plant",
		"label": "Plant / Stock",
		"roles": ("Stock Manager", "Stock User", "Manufacturing Manager", "Manufacturing User"),
		"profiles": ("Stock", "Stock Manager", "Plant"),
	},
	{
		"key": "crm",
		"label": "CRM Sales",
		"roles": ("Sales User",),
		"profiles": ("CRM", "CRM Sales"),
	},
)

PRIORITIES = ("Low", "Medium", "High")
LEAD_SOURCES = ("Field Visit", "Walk-in", "Phone", "Referral", "Website")
DEFAULT_SOURCE = "Field Visit"
LINKABLE_DOCTYPES = (
	"Customer",
	"Supplier",
	"CRM Lead",
	"Lead",
	"Sales Order",
	"Sales Invoice",
	"Quotation",
	"Item",
	"Issue",
	"Task",
	"Employee",
)


def is_protected_user(name: str | None) -> bool:
	return (name or "").strip().lower() in PROTECTED_USERS


def split_name(full_name: str | None) -> tuple[str, str]:
	parts = [part for part in (full_name or "").split() if part]
	if not parts:
		return "", ""
	if len(parts) == 1:
		return parts[0], ""
	return parts[0], " ".join(parts[1:])


def role_choice(key: str | None) -> dict | None:
	wanted = (key or "").strip()
	for choice in ROLE_CHOICES:
		if choice["key"] == wanted:
			return choice
	return None


def managed_roles() -> frozenset[str]:
	names: set[str] = set()
	for choice in ROLE_CHOICES:
		names.update(choice["roles"])
	return frozenset(names)


def roles_to_assign(key: str, existing_roles: set[str] | frozenset[str]) -> list[str]:
	"""Roles from this job that are actually installed. Empty when none are."""
	choice = role_choice(key)
	if not choice:
		return []
	return [role for role in choice["roles"] if role in existing_roles]


def safe_role_profile(key: str, profiles: dict[str, set[str]]) -> str | None:
	"""A Role Profile whose roles are exactly some of this job's roles, or nothing.

	A profile that grants extra roles is skipped so saving a person cannot
	quietly give them access the friendly label does not name.
	"""
	choice = role_choice(key)
	if not choice:
		return None
	wanted = set(choice["roles"])
	for name in choice["profiles"]:
		have = profiles.get(name)
		if have and set(have) <= wanted:
			return name
	return None


def guess_role(user_roles: set[str] | frozenset[str]) -> str | None:
	"""Best friendly job for someone who already has desk roles."""
	if "System Manager" in user_roles:
		return "owner"
	if "HR Manager" in user_roles or "HR User" in user_roles:
		return "hr"
	if "Accounts Manager" in user_roles or "Accounts User" in user_roles:
		return "accounts"
	if (
		"Stock Manager" in user_roles
		or "Stock User" in user_roles
		or "Manufacturing Manager" in user_roles
		or "Manufacturing User" in user_roles
	):
		return "plant"
	if "Sales Manager" in user_roles:
		return "sales_manager"
	if "Sales User" in user_roles:
		return "sales_rep"
	return None


def role_label(key: str | None) -> str:
	choice = role_choice(key or "")
	return choice["label"] if choice else ""


def clean_companies(ticked: list[str] | None, default: str | None) -> tuple[list[str], str]:
	"""Unique ticked companies, and a default that is one of them.

	Raises ValueError when nothing is ticked.
	"""
	seen: set[str] = set()
	names: list[str] = []
	for company in ticked or []:
		name = (company or "").strip()
		if not name or name in seen:
			continue
		seen.add(name)
		names.append(name)
	if not names:
		raise ValueError("Tick at least one company.")
	chosen = (default or "").strip()
	if chosen not in seen:
		chosen = names[0]
	return names, chosen


def clean_priority(value: str | None) -> str:
	text = (value or "").strip().lower()
	if not text:
		return "Medium"
	for priority in PRIORITIES:
		if priority.lower() == text:
			return priority
	raise ValueError("Priority must be Low, Medium, or High.")


def clean_source(value: str | None) -> str:
	text = (value or "").strip().lower()
	if not text:
		return DEFAULT_SOURCE
	for source in LEAD_SOURCES:
		if source.lower() == text:
			return source
	raise ValueError("Choose a source from the list.")


def next_day(today: date) -> str:
	return (today + timedelta(days=1)).isoformat()


def choose_lead_doctype(available: set[str] | frozenset[str]) -> str:
	if "CRM Lead" in available:
		return "CRM Lead"
	if "Lead" in available:
		return "Lead"
	return ""


def phone_links(mobile: str | None) -> dict[str, str]:
	"""tel: and WhatsApp links. A 10-digit Indian mobile gets the 91 prefix."""
	digits = "".join(character for character in (mobile or "") if character.isdigit())
	if not digits:
		return {"tel": "", "whatsapp": ""}
	international = f"91{digits}" if len(digits) == 10 else digits
	return {"tel": f"tel:+{international}", "whatsapp": f"https://wa.me/{international}"}


def is_overdue(due: str | None, today: str) -> bool:
	return bool(due) and due < today
