# Melliflous Branding

Desk branding, a few plain screens, and a primary sales target for each customer, for the Melliflous Group sites on Frappe v16. Uninstalling the app removes the hooks, the pages, the assets, and the Customer Primary Target records. A user's saved default company is left in place, because that value belongs to the user, not to this app.

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

## Quick Actions

A **Quick Actions** tile on the desk home, a **Distributor 360** tile beside it, a **Quick Actions** workspace, and a sidebar named Melliflous Branding. v16 opens desk pages at `/desk/...`. The old `/app/...` address redirects there. Distributor 360 is its own apps-screen icon (`/desk/distributor-360`) for System Manager, Sales Manager, and Sales User. Everyone else who can use the desk still sees Quick Actions.

The grid on `/desk` is not one icon per `add_to_apps_screen` entry. Frappe's boot (`get_app_data`) copies **only the first** entry of each installed app into `boot.app_data`, and the desktop draws that list. Quick Actions is that first entry for this app, which is why it shows and a second hook entry does not. Distributor 360 is added to `boot.app_data` on every desk boot, including a cached one, with the same fields the grid reads: title, `/desk/distributor-360`, and the SVG logo. It has an empty dock, so the icon opens that page instead of the first module of this app. No Desktop Icon row is created. A site on the Apps screen never reads those rows. Migrate does not have to insert anything for this tile. After the bench is deployed, hard-refresh `/desk`.

| Screen | Route | Who |
| --- | --- | --- |
| Add Team Member | `/desk/add-team-member` | System Manager only |
| Give a Task | `/desk/give-task` | Anyone who can use the desk |
| Quick Lead | `/desk/quick-lead` | Anyone who can use the desk |
| My Tasks | `/desk/my-tasks` | The signed-in person |
| Team Files | `/desk/team-files` | Anyone who can use the desk |
| Team Chat | `/raven` | Anyone who can use the desk, when Raven is installed |
| Quick Actions | `/desk/quick-actions` | The workspace of large shortcuts |

**Add Team Member.** Full name, email, mobile, a tick for each company, one default company, and a job: Owner / Admin (System Manager), Accounts, HR, Sales Manager, Sales Rep / Van, Plant / Stock, or CRM Sales. Save creates or updates the user, turns welcome email off, and gives them the desk roles for that job. When the Raven User role exists, it is added as well so they can open Team Chat. A Role Profile already on the user is cleared, because on v16 a profile replaces the whole role list and would undo the choice. Unrelated roles such as Employee stay. One Company user permission is kept per ticked company, with Is Default on the chosen company. Unticked companies are removed. Administrator and Guest are left alone. The same page lists people, with Edit.

**Give a Task.** Pick a person, write what to do, set a due date (tomorrow if left empty) and a priority (Medium if left empty). Company and a link to a record are optional. A linked record is assigned with Frappe's assign-to, which also creates the ToDo. Open tasks are grouped by person. Overdue dates are red. Mark done closes the ToDo. A System Manager sees every open task. Everyone else sees the tasks they gave.

**Quick Lead.** Name, mobile, shop, city, source (Field Visit unless another is chosen), who follows up, and the next follow-up date (tomorrow if left empty). Save creates a **CRM Lead** when Frappe CRM is installed, otherwise an ERPNext **Lead**, and a follow-up ToDo. Below the form, today's and overdue follow-ups have Call (`tel:`) and WhatsApp (`wa.me`) buttons. A 10-digit mobile is treated as an Indian number.

**My Tasks.** Only the signed-in person's open ToDos, with Mark done.

**Team Files.** A shared folder for the desk, used because Frappe Drive does not install on this v16 bench. It is a system page, so the address stays `/desk/team-files`. The sidebar stays on whichever module was already open (often Accounts, if that is the home module). The form itself is drawn by `page/team_files/team_files.js`, which Frappe reads when the page opens, not by the cached desk script. Folders General, Sales, Accounts, HR, Plant, and Marketing are on the page immediately. The first load asks the server to create `Home/Team Files` if it is missing. If that call fails, the message is shown on the page. Drop a file, or use Choose files. Each file is a private Frappe File (`is_private` 1) inside that folder. The list shows the name, size, who uploaded it, the date, and the folder. Search matches the name or the folder. Download and Preview only serve a file from that folder. Delete is limited to the person who uploaded it, or a System Manager.

**Team Chat.** On the Quick Actions workspace (`/desk/quick-actions`, which v16 shows as `/desk/melliflous-branding/quick-actions`) two large tiles sit above the other shortcuts: Team Chat (`/raven`, same window) and Team Files. The plain shortcut rows for those two are hidden once the tiles are in place. `desk_tiles.js` does this, so an older cached `quick_actions.js` does not leave only the rows. The sidebar still lists both. On migrate, every enabled System User who does not already have **Raven User** is given that role, so they can open the chat. Administrator and Guest are skipped. If the Raven app is not installed and the role does not exist, the step does nothing.

These records are imported on `bench migrate` from the app's page, workspace, and sidebar files. The patches `ensure_quick_actions`, `ensure_team_files`, and `show_team_files` import them once as well, so a site that already had the app picks them up on the next update. `ensure_team_files` also creates the folder and grants Raven User.

## Customer targets

A primary (sell-in) target for one customer, for a month or a quarter. The amount is the net total before GST, in the company currency. Submitted Sales Invoices count. A credit note (a Sales Invoice with Is Return ticked) is subtracted, whether ERPNext stored that amount as a negative or a positive. Opening a target, saving it, or the daily job refreshes the achieved amount, the gap, the percent, and the status.

Status is **Achieved** at 100% or more. It is **In Progress** while the period has not ended. It is **Not Achieved** once the period has ended below 100%. On the report, green is 100% or more, amber is 70 to 99, and red is under 70.

An item group counts that group and the groups under it. A brand counts invoice lines of that brand. Leave both blank to count the whole invoice. Two targets for the same customer, company, item group, and brand cannot cover overlapping dates.

**Set one target.** Open Customer Primary Target (Quick Actions → Customer Targets). Pick the customer, the company, and a day in the month or quarter. Enter the target amount. Quantity and UOM are optional. Sales Person and Sales User say who it belongs to. Saving fills the achieved numbers from Sales Invoices in that period.

**Set a month for many customers.** On the Customer Primary Target list, **Set Targets for Month**. Pick the company and any day in the month, optionally an item group, a brand, a sales person, or a customer group, then Load Customers. Type the amounts and Save Targets. A customer who already has that month is updated. A blank amount is skipped. The list stops at 500 customers; narrow it with the sales person or customer group when it does.

**Read the result.** Open Target vs Achievement. Filter by company, period, customer, sales person, and status. The table has a total row. The bar chart compares target and achieved, and shows the 15 largest targets when there are more.

Sales Manager and System Manager can create, edit, and delete every target, and they can run the report. A Sales User can run the report and read a target when they are its owner, its Sales User, or the Sales Person is linked to their Employee (`Sales Person → Employee → User ID`). A Sales User cannot create or edit targets.

Quick Actions has both shortcuts, and so does the Melliflous Branding sidebar. On migrate, the same two links are added to the Selling sidebar and the CRM sidebar (the CRM module is FCRM) when those modules exist. On an older desk that still opens the workspace page, they are added to the Selling and CRM workspaces as well. That step does not pin those workspaces, so a later ERPNext update can still refresh them, and the links are put back on the next migrate.

## Distributors

A distributor is an ERPNext Customer with one Distributor Profile. The profile holds the company, the account manager (a User), the salesman (a Sales Person, a User, or both), the territory and area, how many counters they serve, and how often they are visited. Weekly adds 7 days to the last visit, fortnightly adds 14, and monthly adds one month (31 January becomes the last day of February). Next visit due stays empty until the first visit is filed. There is one profile per customer.

**Log a visit.** Distributor Visit is the phone form. Pick the distributor, the date, and who went. The stock-on-hand table is item, quantity, UOM, and an optional batch written on the pack. Record the order as an amount, a Sales Order, or both, plus how many counters were visited and the next follow-up. Saving the visit sets the profile's last visit to the latest visit date and recomputes the next visit due. Deleting a visit does the same from the visits that remain.

**File the month's secondary sales.** Distributor Stock Statement is one per distributor, company, and month. Pick any day in the month. Fill Items copies last month's closing stock into opening, and fills primary received from submitted Sales Invoices for that month. A credit note is subtracted, whether ERPNext stored the quantity as negative or positive. Secondary sales is what the distributor sold onward. Closing stock is opening plus primary received minus secondary sales. Tick Edit closing to keep a figure you typed; untick it and the formula is used again. Leave Keep this opening unticked to keep using last month's closing. Value is closing quantity times the rate. An item that closed at zero and was not billed this month is left off the fill, so the list does not grow forever.

**Record a complaint.** Type is Quality, Damage, Short Supply, Expiry, Pricing, or Other. Item, batch, and quantity are optional. Description is required. Attach photos of the pack or the bill. Status runs Open, In Progress, Resolved, Closed. Assigned To starts as the account manager. The credit note has to be a submitted Sales Invoice with Is Return ticked, for the same customer.

**Read one distributor.** Distributor 360 is an icon on the apps screen, and the page is `/desk/distributor-360`. It asks for the customer and the company. It shows the last billing date and amount, primary for this month, the last 3 months, and the last 12 months (net total before GST, credit notes subtracted), secondary sales and closing stock from the latest statement, counters, the last visit, days since the last order, open complaints, and the outstanding receivable. The chart is primary against secondary for 12 months. A month with no stock statement has no secondary bar. Below that are the top products, the product-mix share by month, and the buying pattern: orders in 12 months, average order value, average days between orders, and orders per month. The suggested target for next month is the average primary of the last three calendar months, including the month in progress, times one plus the growth percent. Growth starts at 10. Create Target asks you to confirm, then creates or updates the Customer Primary Target for that customer and company for next month, with no item group and no brand. Only a Sales Manager or a System Manager can press it. The tabs list recent invoices, credit notes, payments, visits, stock statements, and complaints, each opening the document. New Visit, New Stock Statement, and New Complaint are on the page. If a call fails, the message is written on the page.

**Chase the book.** Distributor Follow-up lists distributors that need a person: no visit yet or the next visit is before today, no order yet or no order in the last X days (30 unless you change it; an order exactly X days ago is still inside the window), a current-month primary target under 70%, an open complaint (Open or In Progress), or an overdue receivable. Filter by company, account manager, or sales person, and by one of those reasons. Inactive distributors are hidden unless Include inactive is ticked, and a visit is not chased for them. The current-month whole-customer target is the one that counts; if there is only an item-group target, the lowest percent is used.

Sales Manager and System Manager can create and edit every distributor record, and they can open 360 for any customer. A Sales User can read a profile, and can create and edit visits, stock statements, and complaints, only when they are that profile's account manager, salesman, or the Sales Person linked to their Employee. They keep a record they created if the profile is later moved to someone else, as long as they do not change the distributor. They cannot create or delete profiles. 360 and the follow-up report use the same rule, so a salesman does not open another account's billing.

Quick Actions and the Melliflous Branding sidebar list Distributor 360, Distributor Visits, Stock Statements, Complaints, and Distributor Follow-up. Team Chat, Team Files, and the customer-target links stay where they were. On migrate, the same links are put back if they are missing. The patch `ensure_distributors` imports the DocTypes, the page, and the report once for a site that already had the app.

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

The app is already on private bench group **bench-52993**. For a later change that is already on `main`: open that bench group, **Deploy** so the bench picks up the commit, then on the site **melliflous** press **Update Now**. Update Now runs migrate, which loads new pages, the Quick Actions workspace, and the sidebar, creates **Home/Team Files** if it is missing, gives Raven User to enabled desk users when that role exists, creates Customer Primary Target plus the Target vs Achievement report, and creates the distributor profile, visit, stock statement, complaint, Distributor 360 page, and Distributor Follow-up report. Hard-refresh `/desk` after it finishes.

Confirm the site file `/files/melliflous_icon_512.png` is public. That is the icon the manifest and the apple touch link ask iOS to use.

To remove it: on the site, uninstall `melliflous_branding`, then remove the app from the bench group on a later deploy if you do not want the code on the bench. Uninstall drops the Customer Primary Target table. Users keep the company default the picker saved.

## Develop

```bash
python -m unittest melliflous_branding.tests.test_branding melliflous_branding.tests.test_quick melliflous_branding.tests.test_files melliflous_branding.tests.test_targets melliflous_branding.tests.test_distributors
node --check melliflous_branding/public/js/melliflous_branding.js
node --check melliflous_branding/public/js/quick_actions.js
node --check melliflous_branding/public/js/desk_tiles.js
node --check melliflous_branding/melliflous_branding/page/team_files/team_files.js
node --check melliflous_branding/melliflous_branding/page/distributor_360/distributor_360.js
node --check melliflous_branding/melliflous_branding/doctype/customer_primary_target/customer_primary_target.js
node --check melliflous_branding/melliflous_branding/doctype/customer_primary_target/customer_primary_target_list.js
node --check melliflous_branding/melliflous_branding/doctype/distributor_profile/distributor_profile.js
node --check melliflous_branding/melliflous_branding/doctype/distributor_visit/distributor_visit.js
node --check melliflous_branding/melliflous_branding/doctype/distributor_stock_statement/distributor_stock_statement.js
node --check melliflous_branding/melliflous_branding/doctype/distributor_complaint/distributor_complaint.js
node --check melliflous_branding/melliflous_branding/doctype/distributor_complaint/distributor_complaint_list.js
node --check melliflous_branding/melliflous_branding/report/customer_target_vs_achievement/customer_target_vs_achievement.js
node --check melliflous_branding/melliflous_branding/report/distributor_follow_up/distributor_follow_up.js
```

The unit tests cover the title, who sees the picker, User Permission filtering, tile colours, the head tags, and the target rules (periods, credit notes, overlap, the report total, and who can see a row). They do not need a site. A full `bench` install was not run in the environment this was built in: Frappe v16 requires Python 3.14, and that image was not available there.

Hooks:

| Hook | What it does |
| --- | --- |
| `add_to_apps_screen` | Quick Actions, the first entry, is the one the apps grid copies for this app. The Distributor 360 entry is declared here and is not what places that icon. |
| `extend_bootinfo` and `boot_session` | Companies, the current default, whether to show the picker, the tone map, and the Distributor 360 row on `boot.app_data` for System Manager, Sales Manager, and Sales User. |
| `app_include_css` / `app_include_js` | Switcher, title, and tile colours inside the desk. |
| `after_request` | Apple touch icon, manifest link, and `apple-mobile-web-app-title` on `/desk` HTML. |
| `after_install` / `after_migrate` | Create Home/Team Files if it is missing. On migrate, grant Raven User to enabled desk users when that role exists, add the target links to Selling and CRM when those modules exist, and put the distributor links back on Quick Actions and the Melliflous Branding sidebar if they are missing. |
| `doc_events` File `before_validate` | A file saved into Team Files is forced private. |
| `scheduler_events` daily | Refresh achieved amount, gap, percent, and status on every Customer Primary Target. |
| `permission_query_conditions` / `has_permission` | A Sales User reads only the targets they own, and only the distributors assigned to them. Sales Manager and System Manager read all of them. |
| `melliflous_branding.api.set_default_company` | Whitelisted POST. Writes the user default `company`. |
| `melliflous_branding.team_files` | Whitelisted list, upload, download, and delete. Each one requires a desk user and stays inside Home/Team Files. |
| `melliflous_branding.target_records` | Whitelisted month bounds, the bulk target list, and saving a month of targets. Sales Manager or System Manager only, for the bulk save. |
