# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Put Sales Invoice Delete back on the Invoice Admin role only.

Frappe draws ⋯ > Delete from boot.user.can_delete. That list stays empty while
every role has Delete unticked. Invoice Admin gets the tick again. Accounts
Manager and System Manager stay off. akash@skgourmetspices.com is added to the
Invoice Admin list when that User exists, and list members get the role.
"""

from melliflous_branding.invoice_admin_records import ensure_invoice_admin, revoke_sales_invoice_delete


def execute():
	revoke_sales_invoice_delete()
	ensure_invoice_admin()
