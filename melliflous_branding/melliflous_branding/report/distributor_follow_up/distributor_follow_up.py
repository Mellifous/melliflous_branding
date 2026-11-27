# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Distributor Follow-up."""

from __future__ import annotations

from melliflous_branding.distributor_records import run_follow_up


def execute(filters=None):
	return run_follow_up(filters or {})
