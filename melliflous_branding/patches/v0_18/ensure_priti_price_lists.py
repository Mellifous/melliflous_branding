# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Let Priti create Price Lists. Safe to run again. Other roles are not edited."""

from melliflous_branding.price_list_records import ensure_priti_price_lists


def execute():
	ensure_priti_price_lists()
