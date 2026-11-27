# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Seed the HSN Category Map reference. Does not change Item, tax templates, or GST Settings."""

from melliflous_branding.hsn_records import ensure_hsn_catalog


def execute():
	ensure_hsn_catalog()
