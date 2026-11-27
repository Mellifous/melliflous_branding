# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Production / Conversion Register. One row per recipe stock entry."""

from __future__ import annotations

from melliflous_branding.recipe_records import run_register


def execute(filters=None):
	return run_register(filters)
