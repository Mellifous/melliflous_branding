# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Customer Target vs Achievement."""

from __future__ import annotations

from melliflous_branding.target_records import run_report


def execute(filters=None):
	return run_report(filters or {})
