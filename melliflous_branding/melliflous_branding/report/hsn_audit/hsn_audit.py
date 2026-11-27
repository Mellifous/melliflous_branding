# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""HSN Audit. Read only. Applying a suggestion is the HSN Audit page, and only for System Manager."""

from melliflous_branding.hsn_records import report_rows


def execute(filters=None):
	return report_rows(filters or {})
