# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Install and migrate hooks. Both are safe to run more than once."""

from __future__ import annotations


def after_install():
	from melliflous_branding.team_files import ensure_team_folders

	ensure_team_folders()


def after_migrate():
	from melliflous_branding.customer_records import ensure_customer_fields
	from melliflous_branding.division_records import ensure_divisions
	from melliflous_branding.invoice_admin_records import ensure_invoice_admin
	from melliflous_branding.distributor_records import ensure_distributor_places
	from melliflous_branding.raven_roles import grant_missing_raven_roles
	from melliflous_branding.simple_records import ensure_simple_desk
	from melliflous_branding.target_records import ensure_target_places
	from melliflous_branding.team_files import ensure_team_folders

	ensure_team_folders()
	grant_missing_raven_roles()
	ensure_target_places()
	ensure_distributor_places()
	ensure_simple_desk()
	ensure_customer_fields()
	ensure_invoice_admin()
	ensure_divisions()
