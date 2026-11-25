# Melliflous Branding

Desk branding for the Melliflous Group sites on Frappe v16. It does not add a DocType, a workspace, or an apps-screen tile, and it does not patch Frappe. Uninstalling the app removes the hooks and the assets. A user's saved default company is left in place, because that value belongs to the user, not to this app.

Site this was written for: [https://melliflous.m.frappe.cloud](https://melliflous.m.frappe.cloud), on a private bench with Frappe v16, ERPNext v16, HRMS, India Compliance, and Frappe CRM v16. Companies on that site are Melliflous International Multi Trade Pvt Ltd, Melliflous Foods (OPC) Pvt Ltd, Melliflous Beverages, and AJ Enterprises. The app does not hard-code those names. It reads Company from the site.

## What you see

### Header and browser tab

On `/desk`, Frappe's home is the apps screen. The header text **Desktop** is the node `.desktop-navbar-title`, and the browser tab is set with `frappe.utils.set_title("Desktop")`. On a wide screen Frappe hides that header text. On an iPhone (`body.has-mobile-nav`) it is the centred title.

This app replaces both with the user's default company (`Session Defaults` / user default `company`). If that default is missing, or it names a company the user cannot use, the title is **Melliflous Group**. A user who can only use one company sees that company, even when nothing has been saved yet.

The shell HTML for `/desk` is rewritten before it reaches the browser, so the tab is already the company name on first paint. After that, the desk script keeps the title in step when Frappe sets it back to Desktop, including when you return to the home screen.

Other desk pages keep their own tab title (a Sales Invoice stays a Sales Invoice). Only the Desktop title is replaced.

### Company picker

Users who are allowed more than one Company get a company control:

- On the home screen it is the header title. On an iPhone it is the centred title, using a native `<select>` so iOS Safari opens the system picker. The font is at least 16px so focusing it does not zoom the page, and the row is at least 44px tall when it sits on an in-app page.
- On every other desk page it is a bar at the top of the page head, above the breadcrumbs. It stays inside the sticky page head, including on a phone.

Choosing a company calls `melliflous_branding.api.set_default_company`, which writes the same DefaultValue key Session Defaults writes (`frappe.defaults.set_user_default("company", ...)`). The open page updates its boot copy, so a document or report opened afterwards defaults to that company. The header title updates without a reload.

Who sees which companies:

- User Permissions on Company limit the list to those companies, including a permission that applies only to one DocType.
- A user with no Company user permission is unrestricted and sees every Company they can read. Administrator is in this group.
- One or zero companies: no picker.

### iPhone and Add to Home Screen

`/desk` responses get, in the document head:

- `<link rel="apple-touch-icon">` pointing at `/files/melliflous_icon_512.png` (the M already on the site), plus the bundled fallback
- `<link rel="manifest">` for `/assets/melliflous_branding/manifest.json`
- `<meta name="apple-mobile-web-app-title" content="Melliflous Group">`

The manifest name is **Melliflous Group**, `short_name` is **Melliflous**, the icon is the site file (the bundled icon is the second entry), `start_url` is `/desk`, and `display` is `standalone`. `scope` is `/` so a session that bounces through `/login` can stay in the installed app.

Add to Home Screen from `/desk`, while logged in. The home-screen label is the group name. The company name is only the in-desk title. The bundled fallback lives at `/assets/melliflous_branding/images/melliflous_icon_512.png` for a bench where the site file is missing. iOS will not always try the second icon if the first 404s, so the site file should stay public at `/files/melliflous_icon_512.png`.

The script also inserts these tags if the HTML hook did not, which covers a browser that re-reads the live document. The reliable path for iOS is the tags in the original HTML.

### Tile colours

v16's new home shows **one tile per app**, not one tile per department. On this bench that is ERPNext, Frappe HR, CRM, India Compliance, and Frappe Framework.

| Tile label | Colour | Where it shows |
| --- | --- | --- |
| ERPNext | Deep green ring | Apps screen. One tile for the whole app, not a split by department. |
| Frappe HR, HR | Pink | Apps screen, and the HR module tile when modules are on screen. |
| CRM, Frappe CRM | Purple | Apps screen (the CRM app title is "CRM"). |
| India Compliance, GST, GST India | Red | Apps screen, and a GST workspace tile when that label is shown. |
| Accounts | Green | Module tile only. |
| Selling, Field Sales | Orange | Module tile only. |
| Stock | Blue | Module tile only. |
| Buying | Teal | Module tile only. |
| Manufacturing | Brown | Module tile only. |
| Payroll | Yellow | Module tile only. |
| Frappe Framework | None | Left as Frappe draws it. |

Module tiles are on screen in two cases:

- **Desktop Icons**, the older v16 home. Upgraded sites stay on it until a System Manager sets Desktop Settings → Desktop Page to **Apps**. A new site does not use it.
- **Module folder**, on newer v16 builds: an app tile opens a card of its modules (`module-folder`). Those labels get the department colours. The version-16 branch this was checked against draws the apps screen without that folder. The CSS and the painter still match the folder markup, so a bench that has the folder picks the colours up without another release.

Colours key off the English label. A translated tile title will not match, and the tile stays neutral. The logo artwork is not recoloured. A ring and a light pad sit behind it.

## v16 details that shaped this

- The home header title is hidden on a wide desk and shown only on the phone tab-bar layout. The company name is shown in that header on a wide desk as well, because otherwise the replacement would only be visible on a phone and in the tab.
- `body.desktop-page` is added once and never removed, so styles that should affect only the home name the `.desktop-navbar`.
- Frappe's own `boot.py` calls the hook `boot_session`. `frappe.sessions.get` calls `extend_bootinfo` on every boot, including a cached bootinfo, and that is the hook Frappe itself still fills in. This app registers both, with one function that accepts `bootinfo` either as a keyword or as a position.
- Desk HTML has `app_include_css` in `<head>` and `app_include_js` at the end of `<body>`. There is no hook for extra head tags. The apple touch icon is injected with `after_request`, the same hook Frappe uses to append markup to an HTML response (`frappe.flow.launcher.add_to_page`).
- A User Permission marked **Is Default** still wins when a new document picks its Company. That is core behaviour, and it is the same rule Session Defaults loses to. With several Company permissions and none marked default, the saved user default is what new documents and server-side report filters use.
- An open form, and a report that has already built its filters, keep the company they loaded with. Open a new document or report after the switch.
- India Compliance and Frappe CRM are their own apps on the apps screen. Accounts, Selling, Stock, Buying, Manufacturing, and Payroll are modules inside ERPNext or HRMS, so they are not separate home tiles on the apps screen.

## Install on Frappe Cloud

Frappe Cloud reads `[tool.bench.frappe-dependencies]` from the root `pyproject.toml` before it will add the app. This repo declares `frappe = ">=16.0.0-dev,<17.0.0"`. The Python package, `hooks.py` (`app_title`, `required_apps = ["frappe"]`), `patches.txt`, and `__version__` sit in `melliflous_branding/` at the repository root, and the build backend is `flit_core`.

The bench group needs the app, then the site needs it installed. Order:

1. Merge this repository to `main` (or point the bench at the branch you deployed).
2. In Frappe Cloud, open the **private bench group** that hosts `melliflous.m.frappe.cloud`.
3. Open **Apps** and choose **Add App**.
4. Choose **Add from GitHub**. Repository: `https://github.com/Mellifous/melliflous_branding`. Branch: `main`.
5. If the repository is private, connect the GitHub account on that bench first. A public repository does not need that.
6. Save. Frappe Cloud adds the app to the bench group and starts a **deploy**. Wait until that deploy is successful. The deploy links `/assets/melliflous_branding/` to this app's `public` folder. There is no frontend bundle to build.
7. Open the site **melliflous** (`melliflous.m.frappe.cloud`) and install the app `melliflous_branding` from the site's app list. Frappe is already on the bench. `required_apps` is only `frappe`, so ERPNext, HRMS, CRM, and India Compliance do not have to be named for the install to succeed.
8. Hard-refresh `https://melliflous.m.frappe.cloud/desk`. On iPhone Safari, use Add to Home Screen from that URL, not from the login page.

Confirm the site file `/files/melliflous_icon_512.png` is public. That is the icon the manifest and the apple touch link ask iOS to use.

To remove it: on the site, uninstall `melliflous_branding`, then remove the app from the bench group on a later deploy if you do not want the code on the bench. No tables are dropped. Users keep the company default the picker saved.

## Develop

```bash
python -m unittest melliflous_branding.tests.test_branding
node --check melliflous_branding/public/js/melliflous_branding.js
```

The unit tests cover the title, who sees the picker, User Permission filtering, tile colours, and the head tags. They do not need a site. A full `bench` install was not run in the environment this was built in: Frappe v16 requires Python 3.14, and that image was not available there.

Hooks, and nothing else:

| Hook | What it does |
| --- | --- |
| `app_include_css` / `app_include_js` | Switcher, title, and tile colours inside the desk. |
| `extend_bootinfo` and `boot_session` | Companies, the current default, whether to show the picker, and the tone map. |
| `after_request` | Apple touch icon, manifest link, and `apple-mobile-web-app-title` on `/desk` HTML. |
| `melliflous_branding.api.set_default_company` | Whitelisted POST. Writes the user default `company`. |
