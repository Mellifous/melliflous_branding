# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""One row each for Administrator and akash on the Invoice Admin list.

Migrate was appending those two users again whenever it could not see the rows
already stored. Blank rows are removed. A second run changes nothing.
"""

from melliflous_branding.invoice_admin_records import sync_invoice_admin_list


def execute():
	sync_invoice_admin_list()
