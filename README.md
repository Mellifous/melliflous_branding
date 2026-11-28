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

- On a wide desk it is a Company select and a Division select in the header, with the division's short pill (SK, SUN) beside them.
- On a phone, or any window up to 900px, those two selects leave the header. One chip stays in the bar: the division pill, the company name, and the division name. It is at least 44px tall. Tapping it opens a bottom sheet with a full-width Company select and a full-width Division select. The type is 16px so iOS Safari does not zoom. Done, the dimmed backdrop, or Escape closes the sheet. Choosing either value still saves and reloads, the same as the wide controls.
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

## Desk theme

The whole desk uses the SK Gourmet Spices red `#C8102E` and maroon `#7A0019`. Primary buttons are that red. Cards are rounded with a soft shadow. The navbar has a red accent strip, and the sidebar is lightly tinted with the active item in maroon. List and form text is a step larger. Empty lists get a short friendly line. On `/desk` a greeting says good morning, good afternoon, or good evening, plus the person's first name and today's date. Hover on a button or a shortcut lifts it slightly, and that motion is turned off when the browser asks for reduced motion.

Workspace number cards and shortcuts get a coloured left edge for the module you are in: Selling green, Buying blue, Stock teal, Accounting purple, HR orange, CRM pink, Manufacturing amber.

The same red and maroon are the Distributor 360 header. The rest of that page is unchanged.

### Status colour key

List pills, form badges, and a Status column in a report use one meaning:

| Status | Colour |
| --- | --- |
| Draft | Grey |
| Submitted, To Deliver, To Receive, Open | Blue |
| Unpaid, Pending, To Bill, Partly Paid | Amber |
| Overdue, Cancelled, Lost, Expired, Rejected | Red |
| Paid, Completed, Ordered, Delivered, Active | Green |
| Return, Credit Note, Debit Note | Purple |

A status that is not in this list keeps the colour ERPNext already gave it. The words on the pill and the list filter do not change. Sales Invoice, Quotation, Sales Order, Payment Entry, Delivery Note, Purchase Invoice, Purchase Order, Customer, Lead, Opportunity, Item, and Stock Entry are the lists this applies to.

`desk_theme.js` injects a `<style id="melliflous-desk-theme">` tag on load and again on every route change, using `frappe.dom.set_style` when Frappe provides it. The same rules live in `public/css/desk_theme.css`. The asset URLs carry `?v=20261127e`. No bench build is required for the colours to show. Hard-refresh `/desk` after the deploy.

On the apps home, the greeting and the six quick actions sit in a full-width block above the app tiles. A phone shows the actions as a two-column grid of coloured cards. The app tiles wrap underneath, three across, with the whole label visible. A wide desk shows the six actions in one row and the tiles in a wrapping grid. Nothing on that screen scrolls sideways.

Select lists, link suggestions, the form menu, list filters, and the navbar menu stay above the page and the phone tab bar. On a narrow screen each row is at least 44px, a long list scrolls inside the menu, and a menu that would run off the screen is pulled back into view. The page head still shows the control that opens the sidebar.

## Quick Invoice

`/desk/quick-invoice` writes a **draft** for Melliflous International Multi Trade Pvt Ltd. It does not submit.

Pick a customer, then a price list. The customer's own price list is selected when they have one. The list always offers Classic Distributor, Classic Retailer, Classic MRP, and Standard Selling. Add items with the big search and a quantity. The rate comes from the price list. Classic lists store a GST-inclusive price at 5 percent, so the draft rate is that price divided by 1.05 when the item's tax template is `GST 5% - MIMT`. Any other tax rate is left as the price-list rate. The batch starts as the last one used on a sales line. The page shows taxable value, CGST, SGST, and the grand total while you type.

**Save as Draft** creates a Sales Invoice and opens it. **Save as Draft Quotation** does the same for a Quotation. If every item uses `GST 5% - MIMT`, the taxes template is `Output GST 5% In-state - MIMT`. Otherwise the company's default selling template is used. A missing customer, price list, item, or quantity is explained on the page.

On `/desk` and on the Selling workspace, six large buttons sit under the greeting: New Quick Invoice, New Quotation, Payment Received (a new Payment Entry of type Receive), New Sales Order, Stock Balance, and Distributor 360.

New Sales Invoice, Quotation, and Payment Entry forms start on MIMT with today's date, and a new Sales Invoice leaves Update Stock off. Sections people rarely touch (address, terms, print settings, accounting dimensions, and the like) start collapsed. Every field is still there. Open the section to use it.

The Quick Invoice page is a standard Page. The first deploy that runs migrate imports it. Until that migrate, the button is on screen and the address answers only after **Update Now**.

## Sales Invoice numbers

The **Invoice No** field is the first field on the Sales Invoice Details tab, including on a phone, above Company. That value is the document name, so it is the number GST and e-invoice use. It can be at most 16 characters: a letter or digit first, then letters, digits, `/` and `-`. It stays on screen when Melliflous Settings has no prefix yet, and the number then comes from the Sales Invoice series.

A new invoice is filled with the lowest deleted number for that company and prefix that no invoice still uses. If none is free, it is the next serial after the highest number already saved. Drafts and cancelled invoices count as saved, so a cancelled number is not issued twice. If you type a number that is already used, saving is refused: `Invoice no X is already used. Please change it (next free number: Y).` The next invoice then continues from the highest serial, including one you typed by hand, unless a deleted number is free.

Numbers follow posting date. An earlier date cannot get a higher serial than a later date in the same series, and a later date cannot get a lower one. A back-dated invoice is offered a free number between the invoice before it and the invoice after it. If nothing fits, the form asks you to change the date. Cancelled invoices do not set that order, but their numbers stay taken. Drafts do set the order. Two people saving at once are serialized on that company and prefix; the second save is asked to change the number.

**Configure the series.** Open Melliflous Settings → Invoice numbers. Add one row per company.

- **Prefix.** The start of the number, such as `MIMT/26-27/`. Leave it blank to keep using the Sales Invoice naming series. `ACC-SINV-.YYYY.-` becomes `ACC-SINV-2026-`, and the serial is shortened so the full number stays within 16 characters (`ACC-SINV-2026-01` up to `ACC-SINV-2026-99`). Set a shorter prefix when that book is too small.
- **Starting number.** The first number to issue when nothing higher is saved yet. If the old billing software stopped at 150, enter **151**. Leave 0 to start at 1. Once an invoice uses a higher serial, the next one is one past that serial.

Credit notes use the same prefix, so a credit note cannot collide with a tax invoice. Submitted invoices stay on the number they were saved with. An Invoice Admin can still rename those from the menu. A draft can be changed from Invoice No; that renames the document.

A saved draft or a cancelled Sales Invoice shows a **Delete Invoice** button when the server says the signed-in user is Administrator or is on Melliflous Settings → Invoice Admin. Deleting a cancelled invoice first removes that invoice's own delinked Payment Ledger rows and its cancelled GL, stock, repost, and advance-ledger rows. A submitted document that still points at it is named, and the delete stops. The same **Delete Payment** button, with a reason and the same log, is on a cancelled Payment Entry. The check runs when the form opens. It does not use the desk boot. The button asks for a reason, then deletes. The list has **Delete with reason** for the same people. A submitted invoice has to be cancelled first. An invoice with an IRN has to have the e-invoice cancelled first. Accounts Manager and System Manager are not on that list unless someone adds them. The Invoice Admin list is stored once per user; migrate removes duplicate and blank rows instead of adding Administrator and akash again. The reason is stored on Invoice Deletion Log (invoice, company, customer, date, total, status, who, and when). That log is on the Selling workspace. Only Administrator can change or delete a log row.

Cancelling keeps the number taken. Deleting writes the number on the log. The next new Sales Invoice for that company and prefix is offered the lowest deleted number that no invoice still uses. Saving that number consumes it. If that number would put an earlier date on a higher serial than a later date, the form warns you and suggests the next serial after the highest invoice that still exists instead.

The field is created on migrate (`ensure_invoice_numbers`). Until that migrate, new invoices keep ERPNext's own naming series.

## Simple desk

Melliflous Simple Mode is on unless an admin turns it off. Nothing is deleted and no core file is edited. A hidden page still opens from its address.

Kept on the sidebar and the apps grid: Home, Selling, Buying, Stock, Accounting, CRM, Distributor 360, India Compliance, Raven, and Drive. Quick Actions is not an app tile. The six cards on the home screen are those actions. HR stays, and it sits lower than the selling modules, for attendance. Recruitment is not in the hide list, so it stays where HRMS put it.

Hidden while simple mode is on:

| Hidden | What it covers |
| --- | --- |
| Manufacturing | Workspace, dock, and sidebar |
| Projects | Workspace, dock, and sidebar |
| Assets | Workspace, dock, and sidebar |
| Quality, Quality Management | Workspace, dock, and sidebar |
| Support | Workspace, dock, and sidebar |
| Website | Workspace and the Website app tile |
| Tools | Workspace, dock, and sidebar |
| Build, Integrations | Workspace and the Framework app tile |
| ERPNext Settings | Workspace |
| Subcontracting | Workspace |
| Loans, Loan Management | Workspace, plus Loan, Loan Application, Loan Product, Loan Type, Loan Disbursement, Loan Repayment |
| Payroll | Workspace, plus Salary Slip, Salary Structure, Salary Structure Assignment, Payroll Entry, Salary Component |
| Frappe Framework | Taken off the apps grid. The app stays in the boot payload so the desk can still name it |

Selling, Stock, Buying, and Accounting keep their documents. The simple desk only shows these shortcuts. The others are still in the workspace; they are hidden, not removed.

| Workspace | Shortcuts left on screen |
| --- | --- |
| Selling | Quick Invoice, Quotation, Sales Order, Sales Invoice, Payment Entry, Customer, Distributor 360 |
| Stock | Item, Stock Entry, Stock Balance, Delivery Note |
| Buying | Supplier, Purchase Order, Purchase Invoice |
| Accounting | Payment Entry, Journal Entry, General Ledger, Accounts Receivable |

Boot filters `app_data`, the sidebar payload, and the dock on every desk load, including a cached boot. That works on a pull that did not migrate. The desk script hides the same names again in case the sidebar was drawn from an older payload.

**Full desk**, on the navbar, is for System Manager and Administrator. It shows every module for that person and leaves simple mode on for everyone else. Melliflous Settings → **Melliflous Simple Mode** is the site-wide switch. Untick it and the full desk comes back for the team. The workspaces this app had hidden return to the visibility they had before. A workspace that was already hidden stays hidden.

One step needs migrate. **Update Now** (or `bench migrate`) imports the Melliflous Settings DocType and the Quick Invoice page, and sets `Workspace.is_hidden` for the hidden list. A plain pull that does not migrate still hides those modules through boot and the desk script. The Settings page and `/desk/quick-invoice` appear after that migrate. Turning the site-wide switch off, and writing `is_hidden` back, also waits for that migrate because the previous visibility is stored on Melliflous Settings.

## Quick Actions

A **Distributor 360** tile on the desk home, and a sidebar named Melliflous Branding. There is no Quick Actions app tile and no Quick Actions workspace. The six cards on the home screen (New Quick Invoice, New Quotation, Payment Received, New Sales Order, Stock Balance, Distributor 360) are those actions. v16 opens desk pages at `/desk/...`. The old `/app/...` address redirects there. Distributor 360 is its own apps-screen icon (`/desk/distributor-360`) for System Manager, Sales Manager, and Sales User. Other desk users do not get that tile, and nobody gets a Quick Actions tile.

The grid on `/desk` is not one icon per `add_to_apps_screen` entry. Frappe's boot (`get_app_data`) copies **only the first** entry of each installed app into `boot.app_data`. That first entry is Distributor 360. The same row is added again on every desk boot, including a cached one, and a cached Quick Actions row is dropped in that pass. It has an empty dock, so the icon opens `/desk/distributor-360`. No Desktop Icon row is created. After the bench is deployed, hard-refresh `/desk`. Migrate deletes the Quick Actions workspace this app created, and the sidebar link that opened it.

| Screen | Route | Who |
| --- | --- | --- |
| Add Team Member | `/desk/add-team-member` | System Manager only |
| Give a Task | `/desk/give-task` | Anyone who can use the desk |
| Quick Lead | `/desk/quick-lead` | Anyone who can use the desk |
| My Tasks | `/desk/my-tasks` | The signed-in person |
| Team Files | `/desk/team-files` | Anyone who can use the desk |
| Team Chat | `/raven` | Anyone who can use the desk, when Raven is installed |

**Add Team Member.** Full name, email, mobile, a tick for each company, one default company, and a job: Owner / Admin (System Manager), Accounts, HR, Sales Manager, Sales Rep / Van, Plant / Stock, or CRM Sales. Save creates or updates the user, turns welcome email off, and gives them the desk roles for that job. When the Raven User role exists, it is added as well so they can open Team Chat. A Role Profile already on the user is cleared, because on v16 a profile replaces the whole role list and would undo the choice. Unrelated roles such as Employee stay. One Company user permission is kept per ticked company, with Is Default on the chosen company. Unticked companies are removed. Administrator and Guest are left alone. The same page lists people, with Edit.

**Give a Task.** Pick a person, write what to do, set a due date (tomorrow if left empty) and a priority (Medium if left empty). Company and a link to a record are optional. A linked record is assigned with Frappe's assign-to, which also creates the ToDo. Open tasks are grouped by person. Overdue dates are red. Mark done closes the ToDo. A System Manager sees every open task. Everyone else sees the tasks they gave.

**Quick Lead.** Name, mobile, shop, city, source (Field Visit unless another is chosen), who follows up, and the next follow-up date (tomorrow if left empty). Save creates a **CRM Lead** when Frappe CRM is installed, otherwise an ERPNext **Lead**, and a follow-up ToDo. Below the form, today's and overdue follow-ups have Call (`tel:`) and WhatsApp (`wa.me`) buttons. A 10-digit mobile is treated as an Indian number.

**My Tasks.** Only the signed-in person's open ToDos, with Mark done.

**Team Files.** A shared folder for the desk, used because Frappe Drive does not install on this v16 bench. It is a system page, so the address stays `/desk/team-files`. The sidebar stays on whichever module was already open (often Accounts, if that is the home module). The form itself is drawn by `page/team_files/team_files.js`, which Frappe reads when the page opens, not by the cached desk script. Folders General, Sales, Accounts, HR, Plant, and Marketing are on the page immediately. The first load asks the server to create `Home/Team Files` if it is missing. If that call fails, the message is shown on the page. Drop a file, or use Choose files. Each file is a private Frappe File (`is_private` 1) inside that folder. The list shows the name, size, who uploaded it, the date, and the folder. Search matches the name or the folder. Download and Preview only serve a file from that folder. Delete is limited to the person who uploaded it, or a System Manager.

**Team Chat.** Team Chat (`/raven`, same window) and Team Files stay on the Melliflous Branding sidebar. The old Quick Actions workspace no longer hosts them. The plain shortcut rows for those two are hidden once the tiles are in place. `desk_tiles.js` does this, so an older cached `quick_actions.js` does not leave only the rows. The sidebar still lists both. On migrate, every enabled System User who does not already have **Raven User** is given that role, so they can open the chat. Administrator and Guest are skipped. If the Raven app is not installed and the role does not exist, the step does nothing.

These records are imported on `bench migrate` from the app's page, workspace, and sidebar files. The patches `ensure_quick_actions`, `ensure_team_files`, and `show_team_files` import them once as well, so a site that already had the app picks them up on the next update. `ensure_team_files` also creates the folder and grants Raven User.

## Customer targets

A primary (sell-in) target for one customer, for a month or a quarter. The amount is the net total before GST, in the company currency. Submitted Sales Invoices count. A credit note (a Sales Invoice with Is Return ticked) is subtracted, whether ERPNext stored that amount as a negative or a positive. Opening a target, saving it, or the daily job refreshes the achieved amount, the gap, the percent, and the status.

Status is **Achieved** at 100% or more. It is **In Progress** while the period has not ended. It is **Not Achieved** once the period has ended below 100%. On the report, green is 100% or more, amber is 70 to 99, and red is under 70.

An item group counts that group and the groups under it. A brand counts invoice lines of that brand. Leave both blank to count the whole invoice. Two targets for the same customer, company, item group, and brand cannot cover overlapping dates.

**Set one target.** Open Customer Primary Target from the Melliflous Branding sidebar (Customer Targets). Pick the customer, the company, and a day in the month or quarter. Enter the target amount. Quantity and UOM are optional. Sales Person and Sales User say who it belongs to. Saving fills the achieved numbers from Sales Invoices in that period.

**Set a month for many customers.** On the Customer Primary Target list, **Set Targets for Month**. Pick the company and any day in the month, optionally an item group, a brand, a sales person, or a customer group, then Load Customers. Type the amounts and Save Targets. A customer who already has that month is updated. A blank amount is skipped. The list stops at 500 customers; narrow it with the sales person or customer group when it does.

**Read the result.** Open Target vs Achievement. Filter by company, period, customer, sales person, and status. The table has a total row. The bar chart compares target and achieved, and shows the 15 largest targets when there are more.

Sales Manager and System Manager can create, edit, and delete every target, and they can run the report. A Sales User can run the report and read a target when they are its owner, its Sales User, or the Sales Person is linked to their Employee (`Sales Person → Employee → User ID`). A Sales User cannot create or edit targets.

The Melliflous Branding sidebar has both shortcuts. On migrate, the same two links are added to the Selling sidebar and the CRM sidebar (the CRM module is FCRM) when those modules exist. On an older desk that still opens the workspace page, they are added to the Selling and CRM workspaces as well. That step does not pin those workspaces, so a later ERPNext update can still refresh them, and the links are put back on the next migrate.

## Distributors

A distributor is an ERPNext Customer with one Distributor Profile. The profile holds the company, the account manager (a User), the salesman (a Sales Person, a User, or both), the territory and area, how many counters they serve, and how often they are visited. Weekly adds 7 days to the last visit, fortnightly adds 14, and monthly adds one month (31 January becomes the last day of February). Next visit due stays empty until the first visit is filed. There is one profile per customer.

**Log a visit.** Distributor Visit is the phone form. Pick the distributor, the date, and who went. The stock-on-hand table is item, quantity, UOM, and an optional batch written on the pack. Record the order as an amount, a Sales Order, or both, plus how many counters were visited and the next follow-up. Saving the visit sets the profile's last visit to the latest visit date and recomputes the next visit due. Deleting a visit does the same from the visits that remain.

**File the month's secondary sales.** Distributor Stock Statement is one per distributor, company, and month. Pick any day in the month. Fill Items copies last month's closing stock into opening, and fills primary received from submitted Sales Invoices for that month. A credit note is subtracted, whether ERPNext stored the quantity as negative or positive. Secondary sales is what the distributor sold onward. Closing stock is opening plus primary received minus secondary sales. Tick Edit closing to keep a figure you typed; untick it and the formula is used again. Leave Keep this opening unticked to keep using last month's closing. Value is closing quantity times the rate. An item that closed at zero and was not billed this month is left off the fill, so the list does not grow forever.

**Record a complaint.** Type is Quality, Damage, Short Supply, Expiry, Pricing, or Other. Item, batch, and quantity are optional. Description is required. Attach photos of the pack or the bill. Status runs Open, In Progress, Resolved, Closed. Assigned To starts as the account manager. The credit note has to be a submitted Sales Invoice with Is Return ticked, for the same customer.

**Read one distributor.** Distributor 360 is an icon on the apps screen, and the page is `/desk/distributor-360`. It asks for the customer and the company. It shows the last billing date and amount, primary for this month, the last 3 months, and the last 12 months (net total before GST, credit notes subtracted), secondary sales and closing stock from the latest statement, counters, the last visit, days since the last order, open complaints, and the outstanding receivable. The chart is primary against secondary for 12 months. A month with no stock statement has no secondary bar. Below that are the top products, the product-mix share by month, and the buying pattern: orders in 12 months, average order value, average days between orders, and orders per month. The suggested target for next month is the average primary of the last three calendar months, including the month in progress, times one plus the growth percent. Growth starts at 10. Create Target asks you to confirm, then creates or updates the Customer Primary Target for that customer and company for next month, with no item group and no brand. Only a Sales Manager or a System Manager can press it. The tabs list recent invoices, credit notes, payments, visits, stock statements, and complaints, each opening the document. New Visit, New Stock Statement, and New Complaint are on the page. If a call fails, the message is written on the page.

**Chase the book.** Distributor Follow-up lists distributors that need a person: no visit yet or the next visit is before today, no order yet or no order in the last X days (30 unless you change it; an order exactly X days ago is still inside the window), a current-month primary target under 70%, an open complaint (Open or In Progress), or an overdue receivable. Filter by company, account manager, or sales person, and by one of those reasons. Inactive distributors are hidden unless Include inactive is ticked, and a visit is not chased for them. The current-month whole-customer target is the one that counts; if there is only an item-group target, the lowest percent is used.

Sales Manager and System Manager can create and edit every distributor record, and they can open 360 for any customer. A Sales User can read a profile, and can create and edit visits, stock statements, and complaints, only when they are that profile's account manager, salesman, or the Sales Person linked to their Employee. They keep a record they created if the profile is later moved to someone else, as long as they do not change the distributor. They cannot create or delete profiles. 360 and the follow-up report use the same rule, so a salesman does not open another account's billing.

The Melliflous Branding sidebar lists Distributor 360, Distributor Visits, Stock Statements, Complaints, and Distributor Follow-up. Team Chat, Team Files, and the customer-target links stay where they were. On migrate, the same links are put back if they are missing. The patch `ensure_distributors` imports the DocTypes, the page, and the report once for a site that already had the app.

## Recipes and Convert Stock

A recipe is how the plant turns raw spices, a bulk blend, and packs into a finished item. Saving a recipe writes a standard ERPNext **BOM**. **Convert Stock** writes a **Stock Entry** and, when you press Convert, submits it. Raw materials and packs leave the source warehouse. The finished item enters the target warehouse. ERPNext values the finished item from the materials that were consumed.

Open **Recipes** at `/desk/recipes`. The same links are on the **Recipes** workspace and, after Update Now, on the Melliflous Branding sidebar.

**Write a blend.** Name the recipe, pick the company and division, and pick the finished item (create the Item first; this app does not create items). Set the output quantity and its UOM. Use the item's stock UOM. **By percent**, each ingredient is a share of that output before loss, and the percentages have to add up to 100. A 2% expected process loss on a 1 kg blend puts 1.02 kg of spices on the BOM and still receives 1 kg, so the loss sits in the cost. **By quantity**, type the amount you will consume, including loss. Packs are per the output quantity: a recipe of 1 pouch uses 1 pouch and 1 label. Process loss does not add extra pouches.

**Pack a pouch from a bulk blend.** Save the bulk recipe first. On the pouch recipe, add that recipe as a sub-recipe and add the pouch, carton, and label. Converting the pouch consumes the bulk item that is already in stock. It does not grind the spices again. The BOM keeps the sub-recipe's BOM number so the multi-level recipe is visible, and the stock entry does not explode it.

A blend of raw spices is a Stock Entry of type **Manufacture**. A recipe with no raw spices, only a sub-recipe and packs, is **Repack**. Both roll the material value into the finished item.

**Convert.** Open `/desk/convert-stock`. Pick the company, division, recipe, and the quantity to produce. Add one or more source warehouses. Stock is taken from the first, then the next. Pick the target warehouse for the finished goods. The page shows, for each ingredient and pack, what the recipe needs, what is in stock, and the shortfall in red, plus the estimated cost and the cost per unit. Change **Actual qty** when the floor used a different amount. Lower **Actual output** when the batch came out short. Batch no, manufacturing date, and expiry date are optional unless the item tracks batches; a new finished-goods batch is created, and a raw-material batch has to exist already.

**Convert** submits the stock entry. **Save as draft** leaves it unsubmitted, including when stock is short. If something is short, Convert stays blocked. A Manufacturing Manager or a System Manager can tick **Convert despite short stock** and convert anyway. Anyone else cannot. If the company does not allow negative stock, ERPNext can still refuse that entry. Cancelling the stock entry puts the stock back. **Undo this conversion** does that, and only for someone who is allowed to cancel a Stock Entry. It does not delete the document. A user without Delete does not gain Delete.

**Read the register.** Production / Conversion Register filters by company, division, recipe, and date. Each row has the planned quantity, the actual output, yield %, the expected loss %, the actual loss % (how far the spices consumed moved from the loss-free blend), loss versus expected, the total cost, and the cost per unit. Cancelled entries stay hidden unless Include cancelled is ticked. Yield under 100% is amber. Loss above the recipe is red.

The recipe stores the company and the division. The BOM and the stock entry get both. Manufacturing stays hidden in simple mode; use Recipes and Convert Stock instead of the Manufacturing workspace.

No real blend is loaded with the app. Items, warehouses, and recipes are entered on the site.

## HSN and GST checks

Open **HSN Audit** at `/desk/hsn-audit`, or the HSN Audit report on Item. The page lists every enabled item whose HSN or item tax template looks wrong, with the suggested code. Tick the rows and **Apply selected**. Only a System Manager can apply them, and nothing is written until that button is pressed. Ambiguous rows start unticked. Migrate fills **HSN Category Map** and does not change Item.

Saving an Item, Sales Invoice, Purchase Invoice, Quotation, Sales Order, or Delivery Note opens one dialog when something looks off. **Apply and save** on an Item writes the suggestion onto the form. **Save anyway** leaves the document as it is. The save is blocked only when a quantity or rate is negative, a GSTIN fails its format or check digit, or an HSN on a selling or purchase document contains letters or an impossible length. A missing HSN is a warning, so a draft can still be saved.

The dialog is one list, with 16px type and 44px buttons, and it uses the full width on a phone. E-invoice and e-way bill stay manual. This check does not turn those automatic flags on. An e-way bill above the limit is a warning only.

What it warns about:

| Check | What it says |
| --- | --- |
| HSN | Missing, not 6 or 8 digits, not in the GST HSN master, or not the code for that product. 6 digits are the minimum above Rs 5 crore turnover (Notification 78/2020-Central Tax). |
| Tax template | The item tax rate is not the GST rate for that HSN. |
| Tax type | IGST on a supply inside the company's state, or CGST/SGST on a supply to another state. A Bihar to Bihar supply is CGST and SGST. |
| GSTIN | Missing on a registered or company customer, wrong check digit, or the state code does not match the billing address. |
| Rate | Zero, below valuation, or more than 20% under the price list rate. |
| Quantity | Zero, or the same item on two rows. Negative quantity or rate blocks the save. |
| Date | In the future, or in an earlier GST month (monthly GSTR-1 is due on the 11th). |
| E-way bill | Total above Rs 50,000, or above Rs 1,00,000 when the supply starts and ends in Bihar, and no e-way bill number. Quotation and Sales Order are not checked. |
| Address | No billing address, or no place of supply. |
| UOM | Row UOM differs from the stock UOM and the conversion is missing or 1. |

Rates are from Notification 9/2025-Central Tax (Rate) and Notification 10/2025-Central Tax (Rate), both dated 17 September 2025, effective 22 September 2025. Spice headings 0904 to 0910, pasta and vermicelli (1902), sauces (2103), soya bari (21061000) and soya flour (12081000) are 5%. Besan, sattu and atta are 5% when pre-packaged and labelled, and nil when sold loose. Garam masala is suggested as ground spice mixture 09109100. Sunkeera products are suggested as food supplements 21069099, not pan masala 21069020. Kitchen king, curry powder, and other wellness names that are not Sunkeera stay ambiguous. Every suggestion, including these two, is written onto an item only when someone ticks the row and presses Apply.

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

The app is already on private bench group **bench-52993**. For a later change that is already on `main`: open that bench group, **Deploy** so the bench picks up the commit, then on the site **melliflous** press **Update Now**. Update Now runs migrate, which loads new pages, the Quick Actions workspace, and the sidebar, creates **Home/Team Files** if it is missing, gives Raven User to enabled desk users when that role exists, creates Customer Primary Target plus the Target vs Achievement report, and creates the distributor profile, visit, stock statement, complaint, Distributor 360 page, and Distributor Follow-up report. It also loads Recipes, Convert Stock, and the Production / Conversion Register, and adds the recipe fields on Stock Entry and BOM. Hard-refresh `/desk` after it finishes.

Confirm the site file `/files/melliflous_icon_512.png` is public. That is the icon the manifest and the apple touch link ask iOS to use.

To remove it: on the site, uninstall `melliflous_branding`, then remove the app from the bench group on a later deploy if you do not want the code on the bench. Uninstall drops the Customer Primary Target table. Users keep the company default the picker saved.

## Develop

```bash
python -m unittest melliflous_branding.tests.test_branding melliflous_branding.tests.test_quick melliflous_branding.tests.test_files melliflous_branding.tests.test_targets melliflous_branding.tests.test_distributors melliflous_branding.tests.test_desk melliflous_branding.tests.test_invoice_number melliflous_branding.tests.test_invoice_admin melliflous_branding.tests.test_hsn_guard melliflous_branding.tests.test_recipes
node --check melliflous_branding/public/js/melliflous_branding.js
node --check melliflous_branding/public/js/quick_actions.js
node --check melliflous_branding/public/js/desk_tiles.js
node --check melliflous_branding/public/js/desk_theme.js
node --check melliflous_branding/public/js/invoice_admin.js
node --check melliflous_branding/public/js/invoice_number.js
node --check melliflous_branding/public/js/hsn_guard.js
node --check melliflous_branding/melliflous_branding/page/hsn_audit/hsn_audit.js
node --check melliflous_branding/melliflous_branding/report/hsn_audit/hsn_audit.js
node --check melliflous_branding/melliflous_branding/page/team_files/team_files.js
node --check melliflous_branding/melliflous_branding/page/distributor_360/distributor_360.js
node --check melliflous_branding/melliflous_branding/page/quick_invoice/quick_invoice.js
node --check melliflous_branding/melliflous_branding/doctype/customer_primary_target/customer_primary_target.js
node --check melliflous_branding/melliflous_branding/doctype/customer_primary_target/customer_primary_target_list.js
node --check melliflous_branding/melliflous_branding/doctype/distributor_profile/distributor_profile.js
node --check melliflous_branding/melliflous_branding/doctype/distributor_visit/distributor_visit.js
node --check melliflous_branding/melliflous_branding/doctype/distributor_stock_statement/distributor_stock_statement.js
node --check melliflous_branding/melliflous_branding/doctype/distributor_complaint/distributor_complaint.js
node --check melliflous_branding/melliflous_branding/doctype/distributor_complaint/distributor_complaint_list.js
node --check melliflous_branding/melliflous_branding/report/customer_target_vs_achievement/customer_target_vs_achievement.js
node --check melliflous_branding/melliflous_branding/report/distributor_follow_up/distributor_follow_up.js
node --check melliflous_branding/melliflous_branding/page/recipes/recipes.js
node --check melliflous_branding/melliflous_branding/page/convert_stock/convert_stock.js
node --check melliflous_branding/melliflous_branding/doctype/recipe/recipe.js
node --check melliflous_branding/melliflous_branding/report/production_conversion_register/production_conversion_register.js
python -m unittest melliflous_branding.tests.test_recipes
```

The unit tests cover the title, who sees the picker, User Permission filtering, tile colours, the head tags, and the target rules (periods, credit notes, overlap, the report total, and who can see a row). They do not need a site. A full `bench` install was not run in the environment this was built in: Frappe v16 requires Python 3.14, and that image was not available there.

Hooks:

| Hook | What it does |
| --- | --- |
| `add_to_apps_screen` | Distributor 360 is the only entry. The apps grid copies that first entry. Quick Actions is not declared. |
| `extend_bootinfo` and `boot_session` | Companies, the current default, whether to show the picker, the tone map, the Distributor 360 row, and the simple-desk filter on `boot.app_data`, the sidebar, and the dock. Simple mode stays on when Melliflous Settings does not exist yet. |
| `app_include_css` / `app_include_js` | Switcher, title, tile colours, `desk_theme.js`, recipe styles, and `hsn_guard.js`. The theme script injects `<style id="melliflous-desk-theme">` so a cached stylesheet still updates. Asset URLs carry a version query (`20261127e` for the desk theme, `20261127hsn` for the HSN script). |
| `after_request` | Apple touch icon, manifest link, and `apple-mobile-web-app-title` on `/desk` HTML. |
| `after_install` / `after_migrate` | Create Home/Team Files if it is missing. On migrate, grant Raven User to enabled desk users when that role exists, add the target links to Selling and CRM when those modules exist, and put the distributor links back on the Melliflous Branding sidebar if they are missing. Migrate also deletes the Quick Actions workspace this app created, creates the invoice-number series and the HSN Category Map, and adds the recipe fields plus the Recipes sidebar links. |
| `doc_events` Sales Invoice | Assigns the invoice number, checks it is free and in date order, and warns when the HSN or GST treatment looks wrong. The same HSN check runs on Purchase Invoice, Quotation, Sales Order, Delivery Note, and Item. |
| `doc_events` Stock Entry `validate` | A submitted recipe conversion is refused when stock is short, unless a Manufacturing Manager or System Manager has confirmed. |
| `doc_events` File `before_validate` | A file saved into Team Files is forced private. |
| `scheduler_events` daily | Refresh achieved amount, gap, percent, and status on every Customer Primary Target. |
| `permission_query_conditions` / `has_permission` | A Sales User reads only the targets they own, and only the distributors assigned to them. Sales Manager and System Manager read all of them. |
| `melliflous_branding.api.set_default_company` | Whitelisted POST. Writes the user default `company`. |
| `melliflous_branding.team_files` | Whitelisted list, upload, download, and delete. Each one requires a desk user and stays inside Home/Team Files. |
| `melliflous_branding.target_records` | Whitelisted month bounds, the bulk target list, and saving a month of targets. Sales Manager or System Manager only, for the bulk save. |
