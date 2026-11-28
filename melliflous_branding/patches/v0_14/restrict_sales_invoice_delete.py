# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Sales Invoice Delete stays with the Invoice Admin list.

Turns off the level-0 Delete tick, including Accounts Manager where it was
ticked by hand, and adds akash@skgourmetspices.com to that list when the user
exists and is a System Manager.
"""

from melliflous_branding.invoice_admin_records import ensure_invoice_admin, revoke_sales_invoice_delete


def execute():
	revoke_sales_invoice_delete()
	ensure_invoice_admin()
