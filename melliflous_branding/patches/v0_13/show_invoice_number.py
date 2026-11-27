# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Show Invoice No on Sales Invoice and drop a Property Setter that hides it."""

from melliflous_branding.invoice_number_records import ensure_invoice_numbers


def execute():
	ensure_invoice_numbers()
