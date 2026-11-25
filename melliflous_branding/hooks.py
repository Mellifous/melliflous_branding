app_name = "melliflous_branding"
app_title = "Melliflous Branding"
app_publisher = "Melliflous"
app_description = "Desk branding for Melliflous Group on Frappe v16"
app_email = "developers@melliflous.com"
app_license = "MIT"

# This app is not a destination. It stays off the apps screen on purpose.
required_apps = ["frappe"]

# Includes in <head> of desk.html (styles in head, script at the end of body).
app_include_css = "/assets/melliflous_branding/css/melliflous_branding.css"
app_include_js = "/assets/melliflous_branding/js/melliflous_branding.js"

# Desk boot. sessions.get calls extend_bootinfo on every boot, including a
# cached one. boot.get_bootinfo still calls boot_session. Register both.
extend_bootinfo = ["melliflous_branding.boot.boot_session"]
boot_session = ["melliflous_branding.boot.boot_session"]

# iOS reads apple-touch-icon from the document HTML. Desk has no head-include
# hook, so the tags are inserted into the /desk response here.
after_request = ["melliflous_branding.boot.inject_pwa_head"]
