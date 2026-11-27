# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Write explicit 0 rows for the GST auto-generate checks.

v0_10 already ran on the live site. A Single with no tabSingles row shows the
field default, and those defaults are ticked. This pass runs again after that.
"""

from melliflous_branding.invoice_admin_records import keep_einvoice_manual


def execute():
	keep_einvoice_manual()
