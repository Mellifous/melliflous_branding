# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Delete the Quick Actions workspace this app imported, and its sidebar link.

The home cards stay. A Quick Actions workspace that belongs to another module
is left in place. Migrate will not import the workspace again: the JSON file
is gone.
"""

from melliflous_branding.quick_actions_workspace import remove_quick_actions_workspace


def execute():
	remove_quick_actions_workspace()
