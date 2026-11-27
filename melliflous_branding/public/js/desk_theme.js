// Desk theme, status colours, greeting, shortcuts, and the simple desk.
// Styles are injected here because app_include_css has stayed cached after deploys.
// THEME_CSS is the same text as public/css/desk_theme.css.
(function () {
	const THEME_VERSION = "20261127e";
	const THEME_STYLE_ID = "melliflous-desk-theme";
	const THEME_CSS = "/* Melliflous desk theme. Injected again from desk_theme.js because a cached\n   app_include_css file has shipped stale rules. Scoped to the desk. */\n\n:root {\n\t--melliflous-red: #c8102e;\n\t--melliflous-maroon: #7a0019;\n\t--melliflous-red-hover: #9b0c24;\n\t--melliflous-gold: #e4c56a;\n\t--melliflous-gold-deep: #a6842c;\n\t--melliflous-cream: #fbf6ee;\n\t--melliflous-cream-card: #fffaf3;\n\t--melliflous-ink: #1c1917;\n\t--melliflous-card: #fffaf3;\n\t--melliflous-line: #ead9c8;\n\t--melliflous-shadow: 0 1px 2px rgba(28, 25, 23, 0.05), 0 12px 28px rgba(122, 0, 25, 0.08);\n\t--melliflous-selling: #1f9d55;\n\t--melliflous-buying: #2f6fdb;\n\t--melliflous-stock: #0e8f8a;\n\t--melliflous-accounts: #7a45c4;\n\t--melliflous-hr: #e07a1f;\n\t--melliflous-crm: #d4538c;\n\t--melliflous-manufacturing: #d4a017;\n}\n\n[data-theme=\"dark\"] {\n\t--melliflous-ink: #f6efe9;\n\t--melliflous-card: #241418;\n\t--melliflous-cream: #140d0f;\n\t--melliflous-cream-card: #2a171c;\n\t--melliflous-line: #5c3038;\n\t--melliflous-shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 12px 28px rgba(0, 0, 0, 0.35);\n}\n\n/* Status pills. v16 draws .es-badge; older rows still use .indicator-pill.\n   Text sits on a light tint so it stays readable in both themes. */\nbody .es-badge[data-theme=\"gray\"],\nbody .es-badge[data-theme=\"grey\"],\nbody .indicator-pill.gray,\nbody .indicator-pill.grey,\nbody .indicator-pill.darkgrey,\nbody .indicator.gray,\nbody .indicator.grey {\n\t--c-fill: #e7e5e4;\n\t--c-fg: #44403c;\n\t--c-line: #d6d3d1;\n\tbackground: #e7e5e4;\n\tcolor: #44403c;\n}\n\nbody .es-badge[data-theme=\"blue\"],\nbody .es-badge[data-theme=\"light-blue\"],\nbody .indicator-pill.blue,\nbody .indicator-pill.light-blue,\nbody .indicator.blue {\n\t--c-fill: #dbeafe;\n\t--c-fg: #1e3a8a;\n\t--c-line: #bfdbfe;\n\tbackground: #dbeafe;\n\tcolor: #1e3a8a;\n}\n\nbody .es-badge[data-theme=\"amber\"],\nbody .es-badge[data-theme=\"orange\"],\nbody .es-badge[data-theme=\"yellow\"],\nbody .indicator-pill.orange,\nbody .indicator-pill.yellow,\nbody .indicator-pill.amber,\nbody .indicator.orange,\nbody .indicator.yellow {\n\t--c-fill: #fef3c7;\n\t--c-fg: #92400e;\n\t--c-line: #fde68a;\n\tbackground: #fef3c7;\n\tcolor: #92400e;\n}\n\nbody .es-badge[data-theme=\"red\"],\nbody .indicator-pill.red,\nbody .indicator.red {\n\t--c-fill: #fee2e2;\n\t--c-fg: #991b1b;\n\t--c-line: #fecaca;\n\tbackground: #fee2e2;\n\tcolor: #991b1b;\n}\n\nbody .es-badge[data-theme=\"green\"],\nbody .indicator-pill.green,\nbody .indicator.green {\n\t--c-fill: #dcfce7;\n\t--c-fg: #14532d;\n\t--c-line: #bbf7d0;\n\tbackground: #dcfce7;\n\tcolor: #14532d;\n}\n\nbody .es-badge[data-theme=\"purple\"],\nbody .es-badge[data-theme=\"violet\"],\nbody .indicator-pill.purple,\nbody .indicator-pill.violet,\nbody .indicator.purple {\n\t--c-fill: #ede9fe;\n\t--c-fg: #5b21b6;\n\t--c-line: #ddd6fe;\n\tbackground: #ede9fe;\n\tcolor: #5b21b6;\n}\n\n[data-theme=\"dark\"] body .es-badge[data-theme=\"gray\"],\n[data-theme=\"dark\"] body .es-badge[data-theme=\"grey\"],\n[data-theme=\"dark\"] body .indicator-pill.gray,\n[data-theme=\"dark\"] body .indicator-pill.grey,\n[data-theme=\"dark\"] body .indicator-pill.darkgrey {\n\t--c-fill: #44403c;\n\t--c-fg: #f5f5f4;\n\tbackground: #44403c;\n\tcolor: #f5f5f4;\n}\n\n[data-theme=\"dark\"] body .es-badge[data-theme=\"blue\"],\n[data-theme=\"dark\"] body .indicator-pill.blue {\n\t--c-fill: #1e3a8a;\n\t--c-fg: #dbeafe;\n\tbackground: #1e3a8a;\n\tcolor: #dbeafe;\n}\n\n[data-theme=\"dark\"] body .es-badge[data-theme=\"amber\"],\n[data-theme=\"dark\"] body .es-badge[data-theme=\"orange\"],\n[data-theme=\"dark\"] body .indicator-pill.orange,\n[data-theme=\"dark\"] body .indicator-pill.yellow {\n\t--c-fill: #78350f;\n\t--c-fg: #fde68a;\n\tbackground: #78350f;\n\tcolor: #fde68a;\n}\n\n[data-theme=\"dark\"] body .es-badge[data-theme=\"red\"],\n[data-theme=\"dark\"] body .indicator-pill.red {\n\t--c-fill: #7f1d1d;\n\t--c-fg: #fecaca;\n\tbackground: #7f1d1d;\n\tcolor: #fecaca;\n}\n\n[data-theme=\"dark\"] body .es-badge[data-theme=\"green\"],\n[data-theme=\"dark\"] body .indicator-pill.green {\n\t--c-fill: #14532d;\n\t--c-fg: #bbf7d0;\n\tbackground: #14532d;\n\tcolor: #bbf7d0;\n}\n\n[data-theme=\"dark\"] body .es-badge[data-theme=\"purple\"],\n[data-theme=\"dark\"] body .es-badge[data-theme=\"violet\"],\n[data-theme=\"dark\"] body .indicator-pill.purple {\n\t--c-fill: #4c1d95;\n\t--c-fg: #ddd6fe;\n\tbackground: #4c1d95;\n\tcolor: #ddd6fe;\n}\n\n/* Primary actions in the brand red. White on these reds clears WCAG AA. */\nbody .btn-primary,\nbody .btn-primary:focus,\nbody .btn-primary-dark {\n\tbackground-color: var(--melliflous-red);\n\tborder-color: var(--melliflous-red-hover);\n\tcolor: #fff;\n\tborder-radius: 10px;\n}\n\nbody .btn-primary:hover,\nbody .btn-primary-dark:hover {\n\tbackground-color: var(--melliflous-maroon);\n\tborder-color: var(--melliflous-maroon);\n\tcolor: #fff;\n}\n\nbody .btn-primary,\nbody .shortcut-widget-box,\nbody .number-widget-box,\nbody .melliflous-shortcut {\n\ttransition: box-shadow 160ms ease, background-color 160ms ease;\n}\n\nbody .melliflous-shortcut {\n\ttransition: transform 160ms ease, box-shadow 160ms ease, background-color 160ms ease;\n}\n\nbody .melliflous-shortcut:hover {\n\ttransform: translateY(-1px);\n}\n\nbody .widget,\nbody .shortcut-widget-box,\nbody .number-widget-box,\nbody .widget.shortcut,\nbody .widget.number {\n\tborder-radius: 14px;\n\tbox-shadow: var(--melliflous-shadow);\n}\n\nbody .layout-main-section,\nbody .form-layout,\nbody .frappe-card {\n\tborder-radius: 16px;\n}\n\n/* Navbar in the brand crimson, with a gold hairline. */\nbody .navbar,\nbody .desktop-navbar,\nbody.desktop-page .navbar-container {\n\tposition: relative;\n\tbackground: linear-gradient(100deg, #5c0012 0%, #9b1230 52%, #c8102e 100%);\n\tcolor: #fffaf3;\n\tbox-shadow: inset 0 -3px 0 var(--melliflous-gold), 0 8px 24px rgba(92, 0, 18, 0.18);\n}\n\nbody .navbar .nav-link,\nbody .navbar .navbar-brand,\nbody .navbar .btn-reset,\nbody.desktop-page .desktop-navbar a,\nbody.desktop-page .desktop-navbar .melliflous-simple-toggle {\n\tcolor: #fffaf3;\n}\n\n[data-theme=\"dark\"] body .navbar,\n[data-theme=\"dark\"] body .desktop-navbar,\n[data-theme=\"dark\"] body.desktop-page .navbar-container {\n\tbackground: linear-gradient(100deg, #3a0a14 0%, #7a0019 62%, #9b1230 100%);\n\tcolor: #fff5f5;\n}\n\nbody .body-sidebar,\nbody .standard-sidebar,\nbody .layout-side-section {\n\tbackground: #fff7f0;\n}\n\n[data-theme=\"dark\"] body .body-sidebar,\n[data-theme=\"dark\"] body .standard-sidebar,\n[data-theme=\"dark\"] body .layout-side-section {\n\tbackground: #2a1216;\n}\n\nbody .standard-sidebar-item.selected,\nbody .standard-sidebar-item.active,\nbody .sidebar-item.selected,\nbody .sidebar-item.active,\nbody .desk-sidebar-item.selected {\n\tbackground: rgba(200, 16, 46, 0.12);\n\tcolor: var(--melliflous-maroon);\n\tbox-shadow: inset 3px 0 0 var(--melliflous-red);\n\tborder-radius: 8px;\n}\n\n[data-theme=\"dark\"] body .standard-sidebar-item.selected,\n[data-theme=\"dark\"] body .standard-sidebar-item.active,\n[data-theme=\"dark\"] body .sidebar-item.selected {\n\tbackground: rgba(200, 16, 46, 0.28);\n\tcolor: #fecdd3;\n}\n\n/* Readable type on the lists and forms people use all day. */\nbody .frappe-list .list-row,\nbody .frappe-list .list-row-head,\nbody .list-row-col,\nbody .form-layout .control-label,\nbody .form-layout .form-control,\nbody .form-layout .like-disabled-input {\n\tfont-size: 15px;\n}\n\nbody .form-layout .form-control,\nbody .form-layout .like-disabled-input {\n\tborder-radius: 8px;\n}\n\nbody .no-result,\nbody .empty-state,\nbody .list-empty-state,\nbody .msg-box.no-result {\n\tborder: 1px dashed var(--melliflous-line);\n\tborder-radius: 16px;\n\tbackground: #fff7f6;\n\tcolor: var(--melliflous-ink);\n\tpadding: 28px 18px;\n}\n\n[data-theme=\"dark\"] body .no-result,\n[data-theme=\"dark\"] body .empty-state,\n[data-theme=\"dark\"] body .msg-box.no-result {\n\tbackground: #2a1216;\n\tcolor: #f5f5f4;\n}\n\n.melliflous-empty-note {\n\tmargin: 8px 0 0;\n\tcolor: #57534e;\n}\n\n[data-theme=\"dark\"] .melliflous-empty-note {\n\tcolor: #d6d3d1;\n}\n\n.melliflous-greeting {\n\tbox-sizing: border-box;\n\twidth: 100%;\n\tmax-width: 100%;\n\tmargin: 0 0 12px;\n\tpadding: 16px 18px;\n\tborder-radius: 18px;\n\tbackground:\n\t\tradial-gradient(120% 80% at 100% 0%, rgba(228, 197, 106, 0.35), transparent 46%),\n\t\tlinear-gradient(120deg, var(--melliflous-red) 0%, var(--melliflous-maroon) 100%);\n\tcolor: #fff;\n\tbox-shadow: var(--melliflous-shadow);\n}\n\n.melliflous-greeting-hello {\n\tmargin: 0;\n\tfont-size: 1.35rem;\n\tfont-weight: 700;\n\tline-height: 1.25;\n}\n\n.melliflous-greeting-date {\n\tmargin: 4px 0 0;\n\tfont-size: 0.95rem;\n\topacity: 0.92;\n}\n\n.melliflous-shortcuts {\n\tdisplay: grid;\n\tgrid-template-columns: repeat(2, minmax(0, 1fr));\n\tgap: 10px;\n\twidth: 100%;\n\tmax-width: 100%;\n\tmargin: 0 0 14px;\n\tbox-sizing: border-box;\n\tmin-width: 0;\n}\n\n.melliflous-shortcut {\n\tdisplay: flex;\n\tflex-direction: column;\n\talign-items: flex-start;\n\tjustify-content: space-between;\n\tgap: 10px;\n\tmin-width: 0;\n\tmin-height: 96px;\n\tpadding: 12px;\n\tborder: 0;\n\tborder-radius: 18px;\n\tbackground: linear-gradient(145deg, #e11d3a, #7a0019);\n\tcolor: #fff;\n\tfont-size: 0.95rem;\n\tfont-weight: 800;\n\tline-height: 1.2;\n\ttext-align: left;\n\ttext-decoration: none;\n\tbox-shadow: 0 10px 22px rgba(92, 0, 18, 0.16);\n\tcursor: pointer;\n\ttouch-action: manipulation;\n\tbox-sizing: border-box;\n}\n\n.melliflous-shortcut-icon {\n\tdisplay: flex;\n\talign-items: center;\n\tjustify-content: center;\n\twidth: 36px;\n\theight: 36px;\n\tborder-radius: 12px;\n\tbackground: rgba(255, 255, 255, 0.2);\n}\n\n.melliflous-shortcut-label {\n\tdisplay: block;\n\tmax-width: 100%;\n\toverflow-wrap: anywhere;\n}\n\n.melliflous-shortcut.tone-brand { background: linear-gradient(145deg, #e11d3a, #7a0019); }\n.melliflous-shortcut.tone-blue { background: linear-gradient(145deg, #3b82f6, #1e3a8a); }\n.melliflous-shortcut.tone-green { background: linear-gradient(145deg, #22c55e, #14532d); }\n.melliflous-shortcut.tone-teal { background: linear-gradient(145deg, #2dd4bf, #0f766e); }\n.melliflous-shortcut.tone-amber {\n\tbackground: linear-gradient(145deg, #f8e7b0, #d4a017);\n\tcolor: #1c1917;\n}\n.melliflous-shortcut.tone-maroon { background: linear-gradient(145deg, #be123c, #4c0519); }\n\n.melliflous-shortcut.tone-amber .melliflous-shortcut-icon {\n\tbackground: rgba(28, 25, 23, 0.1);\n}\n\n.melliflous-shortcut:hover {\n\ttext-decoration: none;\n\tcolor: inherit;\n}\n\n@media (min-width: 768px) {\n\t.melliflous-shortcuts {\n\t\tgrid-template-columns: repeat(3, minmax(0, 1fr));\n\t}\n}\n\n@media (min-width: 1100px) {\n\t.melliflous-shortcuts {\n\t\tgrid-template-columns: repeat(6, minmax(0, 1fr));\n\t}\n}\n\n.melliflous-simple-toggle {\n\tmargin-left: 8px;\n\tborder-radius: 999px;\n\tborder: 1px solid var(--melliflous-red);\n\tbackground: transparent;\n\tcolor: var(--melliflous-maroon);\n\tfont-weight: 700;\n\tmin-height: 32px;\n\tpadding: 0 12px;\n}\n\n[data-theme=\"dark\"] .melliflous-simple-toggle {\n\tcolor: #fecdd3;\n}\n\n.melliflous-simple-hidden {\n\tdisplay: none !important;\n}\n\nbody[data-melliflous-module=\"selling\"] .shortcut-widget-box,\nbody[data-melliflous-module=\"selling\"] .number-widget-box,\nbody[data-melliflous-module=\"selling\"] .widget.shortcut,\nbody[data-melliflous-module=\"selling\"] .widget.number {\n\tborder-left: 4px solid var(--melliflous-selling);\n}\n\nbody[data-melliflous-module=\"buying\"] .shortcut-widget-box,\nbody[data-melliflous-module=\"buying\"] .number-widget-box,\nbody[data-melliflous-module=\"buying\"] .widget.shortcut,\nbody[data-melliflous-module=\"buying\"] .widget.number {\n\tborder-left: 4px solid var(--melliflous-buying);\n}\n\nbody[data-melliflous-module=\"stock\"] .shortcut-widget-box,\nbody[data-melliflous-module=\"stock\"] .number-widget-box,\nbody[data-melliflous-module=\"stock\"] .widget.shortcut,\nbody[data-melliflous-module=\"stock\"] .widget.number {\n\tborder-left: 4px solid var(--melliflous-stock);\n}\n\nbody[data-melliflous-module=\"accounting\"] .shortcut-widget-box,\nbody[data-melliflous-module=\"accounting\"] .number-widget-box,\nbody[data-melliflous-module=\"accounting\"] .widget.shortcut,\nbody[data-melliflous-module=\"accounting\"] .widget.number,\nbody[data-melliflous-module=\"accounts\"] .shortcut-widget-box,\nbody[data-melliflous-module=\"accounts\"] .number-widget-box,\nbody[data-melliflous-module=\"accounts\"] .widget.shortcut,\nbody[data-melliflous-module=\"accounts\"] .widget.number {\n\tborder-left: 4px solid var(--melliflous-accounts);\n}\n\nbody[data-melliflous-module=\"hr\"] .shortcut-widget-box,\nbody[data-melliflous-module=\"hr\"] .number-widget-box,\nbody[data-melliflous-module=\"hr\"] .widget.shortcut,\nbody[data-melliflous-module=\"hr\"] .widget.number {\n\tborder-left: 4px solid var(--melliflous-hr);\n}\n\nbody[data-melliflous-module=\"crm\"] .shortcut-widget-box,\nbody[data-melliflous-module=\"crm\"] .number-widget-box,\nbody[data-melliflous-module=\"crm\"] .widget.shortcut,\nbody[data-melliflous-module=\"crm\"] .widget.number {\n\tborder-left: 4px solid var(--melliflous-crm);\n}\n\nbody[data-melliflous-module=\"manufacturing\"] .shortcut-widget-box,\nbody[data-melliflous-module=\"manufacturing\"] .number-widget-box,\nbody[data-melliflous-module=\"manufacturing\"] .widget.shortcut,\nbody[data-melliflous-module=\"manufacturing\"] .widget.number {\n\tborder-left: 4px solid var(--melliflous-manufacturing);\n}\n\n.melliflous-quick.melliflous-invoice .row-card {\n\tmargin-top: 12px;\n\tpadding: 12px;\n\tborder: 1px solid var(--melliflous-line);\n\tborder-radius: 14px;\n\tbackground: var(--melliflous-card);\n}\n\n.melliflous-invoice .totals {\n\tdisplay: grid;\n\tgrid-template-columns: repeat(4, 1fr);\n\tgap: 8px;\n\tmargin-top: 16px;\n}\n\n.melliflous-invoice .total {\n\tpadding: 12px;\n\tborder-radius: 12px;\n\tbackground: #fff7f6;\n\tborder-top: 4px solid var(--melliflous-red);\n}\n\n.melliflous-invoice .total .label {\n\tfont-size: 0.85rem;\n\tcolor: #57534e;\n}\n\n.melliflous-invoice .total .value {\n\tmargin-top: 4px;\n\tfont-size: 1.15rem;\n\tfont-weight: 800;\n}\n\n.melliflous-invoice .btn-row .btn {\n\tmin-height: 52px;\n\tfont-size: 1.05rem;\n}\n\n.melliflous-invoice .note {\n\tmargin-top: 8px;\n\tcolor: #57534e;\n}\n\n.melliflous-greeting svg,\n.melliflous-simple-toggle svg,\n.melliflous-invoice svg {\n\twidth: 18px;\n\theight: 18px;\n\tmax-width: 18px;\n\tmax-height: 18px;\n}\n\n.melliflous-shortcut-icon svg {\n\twidth: 20px;\n\theight: 20px;\n\tmax-width: 20px;\n\tmax-height: 20px;\n}\n\n@media (max-width: 720px) {\n\t.melliflous-invoice .totals {\n\t\tgrid-template-columns: 1fr 1fr;\n\t}\n\t.melliflous-greeting-hello {\n\t\tfont-size: 1.2rem;\n\t}\n}\n\n/* Home apps screen. The shortcut row and the icon grid are stacked, full width,\n   and the icons wrap so a phone never scrolls sideways. */\nbody.desktop-page .desktop-wrapper {\n\tmax-width: 100%;\n}\n\nbody.desktop-page .desktop-container {\n\tdisplay: flex !important;\n\tflex-direction: column !important;\n\talign-items: stretch !important;\n\tjustify-content: flex-start !important;\n\twidth: 100% !important;\n\tmax-width: 1120px;\n\tmargin: 0 auto;\n\tpadding: 16px 14px 96px;\n\tbox-sizing: border-box;\n}\n\nbody.desktop-page .desktop-container > .icons-container {\n\twidth: 100%;\n\tmin-width: 0;\n\tmargin-top: 4px !important;\n\tpadding: 0 !important;\n}\n\nbody.desktop-page .desktop-container > .icons-container > .icons {\n\tdisplay: grid !important;\n\twidth: 100%;\n\tgrid-template-columns: repeat(3, minmax(0, 1fr)) !important;\n\tgrid-template-rows: none !important;\n\tgap: 10px !important;\n\tjustify-items: stretch;\n}\n\nbody.desktop-page .desktop-container > .icons-container > .icons > .desktop-icon {\n\twidth: 100% !important;\n\theight: auto !important;\n\tmin-height: 112px;\n\tbox-sizing: border-box;\n\tpadding: 12px 8px;\n\tborder: 1px solid #f0e0d0;\n\tborder-radius: 18px;\n\tbackground: linear-gradient(180deg, #fffdf8, #fff4ea);\n\tbox-shadow: var(--melliflous-shadow);\n}\n\nbody.desktop-page .desktop-container .icon-caption {\n\theight: auto;\n\ttext-wrap: wrap;\n}\n\nbody.desktop-page .desktop-container .icon-title,\nbody.desktop-page .desktop-container a.icon-title {\n\tdisplay: block;\n\twhite-space: normal !important;\n\toverflow: visible;\n\ttext-overflow: unset;\n\toverflow-wrap: anywhere;\n\tline-height: 1.25;\n\tcolor: var(--melliflous-ink);\n}\n\n[data-theme=\"dark\"] body.desktop-page .desktop-container > .icons-container > .icons > .desktop-icon {\n\tbackground: #2a171c;\n\tborder-color: #5c3038;\n\tcolor: #fff5f5;\n}\n\n[data-theme=\"dark\"] body.desktop-page .desktop-container .icon-title,\n[data-theme=\"dark\"] body.desktop-page .desktop-container a.icon-title {\n\tcolor: #fff5f5;\n}\n\n@media (min-width: 700px) {\n\tbody.desktop-page .desktop-container > .icons-container > .icons {\n\t\tgrid-template-columns: repeat(auto-fill, minmax(132px, 1fr)) !important;\n\t}\n}\n\n/* Warm desk chrome: cream page, gold-edged cards, readable dark mode. */\nbody {\n\tbackground: var(--melliflous-cream);\n\tcolor: var(--melliflous-ink);\n}\n\nbody .page-head {\n\tbackground: linear-gradient(180deg, rgba(200, 16, 46, 0.07), transparent 80%);\n\tborder-bottom: 1px solid var(--melliflous-line);\n}\n\n[data-theme=\"dark\"] body .page-head {\n\tbackground: linear-gradient(180deg, rgba(200, 16, 46, 0.2), transparent 80%);\n}\n\nbody .layout-main-section,\nbody .form-layout,\nbody .frappe-card,\nbody .widget,\nbody .shortcut-widget-box,\nbody .number-widget-box {\n\tbackground: var(--melliflous-card);\n\tborder: 1px solid var(--melliflous-line);\n}\n\nbody .form-control,\nbody textarea.form-control,\nbody select.form-control,\nbody .like-disabled-input {\n\tborder-radius: 10px;\n\tborder-color: var(--melliflous-line);\n\tbackground: var(--melliflous-cream-card);\n\tcolor: var(--melliflous-ink);\n}\n\nbody .form-control:focus,\nbody select.form-control:focus,\nbody textarea.form-control:focus {\n\tborder-color: var(--melliflous-red);\n\tbox-shadow: 0 0 0 3px rgba(200, 16, 46, 0.16);\n}\n\nbody .btn-default,\nbody .btn-secondary {\n\tborder-radius: 10px;\n\tborder-color: var(--melliflous-gold-deep);\n\tbackground: var(--melliflous-cream-card);\n\tcolor: var(--melliflous-maroon);\n}\n\n[data-theme=\"dark\"] body .btn-default,\n[data-theme=\"dark\"] body .btn-secondary {\n\tcolor: #f6e7c1;\n\tbackground: #321c22;\n\tborder-color: var(--melliflous-gold-deep);\n}\n\nbody .list-row:hover,\nbody .frappe-list .list-row:hover {\n\tbackground: #fff6ee;\n}\n\n[data-theme=\"dark\"] body .list-row:hover,\n[data-theme=\"dark\"] body .frappe-list .list-row:hover {\n\tbackground: #3a2228;\n}\n\nbody .modal-content {\n\toverflow: visible;\n\tborder: 1px solid var(--melliflous-line);\n\tborder-radius: 18px;\n\tbackground: var(--melliflous-card);\n\tcolor: var(--melliflous-ink);\n\tbox-shadow: 0 24px 60px rgba(92, 0, 18, 0.22);\n}\n\nbody .modal-header {\n\tbackground: linear-gradient(90deg, #7a0019, #c8102e);\n\tcolor: #fffaf3;\n}\n\nbody .modal-header .btn,\nbody .modal-header .close,\nbody .modal-header .btn-modal-close {\n\tcolor: #fffaf3;\n}\n\nbody .number-widget-box,\nbody .widget.number {\n\tborder-top: 3px solid var(--melliflous-gold);\n\tbackground: linear-gradient(180deg, var(--melliflous-cream-card), var(--melliflous-card));\n}\n\nbody .standard-sidebar-item,\nbody .sidebar-item {\n\tborder-radius: 10px;\n}\n\nbody .melliflous-simple-toggle {\n\tmin-height: 36px;\n\tborder-color: var(--melliflous-gold);\n\tcolor: #fffaf3;\n}\n\n@media (prefers-reduced-motion: reduce) {\n\tbody .btn-primary,\n\tbody .shortcut-widget-box,\n\tbody .number-widget-box,\n\tbody .melliflous-shortcut,\n\tbody .desktop-icon,\n\t.melliflous-sheet-panel {\n\t\ttransition: none;\n\t}\n\n\tbody .melliflous-shortcut:hover {\n\t\ttransform: none;\n\t}\n}\n\n/* Menus, link suggestions, and the sidebar. Ancestors above stay overflow\n   visible. These rules only size and stack the menus themselves. */\n.dropdown-menu,\n.awesomplete > ul,\n.popover,\n.filter-popover,\n.list-filter-popover {\n\tz-index: 2050;\n\tmax-width: calc(100vw - 16px);\n\tborder-radius: 14px;\n\tborder: 1px solid var(--melliflous-line);\n\tbackground: var(--melliflous-card);\n\tcolor: var(--melliflous-ink);\n\tbox-shadow: 0 16px 40px rgba(92, 0, 18, 0.18);\n}\n\n.dropdown-menu .dropdown-item,\n.dropdown-menu > li > a,\n.awesomplete > ul > li,\n.popover .dropdown-item {\n\tmin-height: 44px;\n\tdisplay: flex;\n\talign-items: center;\n\tpadding: 8px 14px;\n\tcolor: var(--melliflous-ink);\n\twhite-space: normal;\n}\n\n.dropdown-menu .dropdown-item:hover,\n.dropdown-menu > li > a:hover,\n.awesomplete > ul > li:hover,\n.awesomplete > ul > li[aria-selected=\"true\"],\n.awesomplete mark {\n\tbackground: rgba(200, 16, 46, 0.1);\n\tcolor: var(--melliflous-maroon);\n}\n\n[data-theme=\"dark\"] .dropdown-menu,\n[data-theme=\"dark\"] .awesomplete > ul,\n[data-theme=\"dark\"] .popover,\n[data-theme=\"dark\"] .filter-popover {\n\tbackground: #2a171c;\n\tcolor: #fff5f5;\n\tborder-color: #5c3038;\n}\n\n[data-theme=\"dark\"] .dropdown-menu .dropdown-item,\n[data-theme=\"dark\"] .dropdown-menu > li > a,\n[data-theme=\"dark\"] .awesomplete > ul > li {\n\tcolor: #fff5f5;\n}\n\n[data-theme=\"dark\"] .dropdown-menu .dropdown-item:hover,\n[data-theme=\"dark\"] .awesomplete > ul > li:hover,\n[data-theme=\"dark\"] .awesomplete > ul > li[aria-selected=\"true\"] {\n\tbackground: #4a2030;\n\tcolor: #fff5f5;\n}\n\n@media (max-width: 900px) {\n\t.dropdown-menu,\n\t.awesomplete > ul,\n\t.popover,\n\t.filter-popover,\n\t.list-filter-popover {\n\t\tmax-height: min(60dvh, calc(100dvh - 7.5rem));\n\t\toverflow-y: auto;\n\t\t-webkit-overflow-scrolling: touch;\n\t\toverscroll-behavior: contain;\n\t}\n\n\tbody .page-head .sidebar-toggle-btn {\n\t\topacity: 1 !important;\n\t\tvisibility: visible !important;\n\t\tposition: relative !important;\n\t\tright: auto !important;\n\t\tbottom: auto !important;\n\t\twidth: 44px !important;\n\t\theight: 44px !important;\n\t\tmin-width: 44px;\n\t\tmin-height: 44px;\n\t\tborder-radius: 12px;\n\t}\n\n\tbody .standard-sidebar-item,\n\tbody .sidebar-item,\n\tbody .desk-sidebar .sidebar-item a {\n\t\tmin-height: 44px;\n\t}\n}\n";

	const COMPANY = "Melliflous International Multi Trade Pvt Ltd";
	const TRACKED = {
		"Sales Invoice": true,
		Quotation: true,
		"Sales Order": true,
		"Payment Entry": true,
		"Delivery Note": true,
		"Purchase Invoice": true,
		"Purchase Order": true,
		Customer: true,
		Lead: true,
		Opportunity: true,
		Item: true,
		"Stock Entry": true,
	};

	// Keep this in step with STATUS_COLOURS in branding.py.
	const STATUS_COLOURS = {
		Draft: "grey",
		Submitted: "blue",
		"To Deliver": "blue",
		"To Receive": "blue",
		Open: "blue",
		Replied: "blue",
		Lead: "blue",
		Opportunity: "blue",
		Unpaid: "orange",
		Pending: "orange",
		"To Bill": "orange",
		"To Deliver and Bill": "orange",
		"To Receive and Bill": "orange",
		"Partly Paid": "orange",
		"Partly Paid and Discounted": "orange",
		"Unpaid and Discounted": "orange",
		"On Hold": "orange",
		"Partially Ordered": "orange",
		Interested: "orange",
		Quotation: "orange",
		Overdue: "red",
		"Overdue and Discounted": "red",
		Cancelled: "red",
		Lost: "red",
		"Lost Quotation": "red",
		Expired: "red",
		Rejected: "red",
		"Do Not Contact": "red",
		Paid: "green",
		Completed: "green",
		Ordered: "green",
		Delivered: "green",
		Active: "green",
		Enabled: "green",
		Converted: "green",
		Closed: "green",
		Disabled: "grey",
		Return: "purple",
		"Credit Note Issued": "purple",
		"Debit Note Issued": "purple",
		"Return Issued": "purple",
	};

	const HIDDEN = [
		"Manufacturing",
		"Projects",
		"Assets",
		"Quality",
		"Quality Management",
		"Support",
		"Website",
		"Tools",
		"Build",
		"Integrations",
		"ERPNext Settings",
		"Subcontracting",
		"Loans",
		"Loan Management",
		"Payroll",
		"Salary Slip",
		"Salary Structure",
		"Salary Structure Assignment",
		"Payroll Entry",
		"Salary Component",
		"Loan",
		"Loan Application",
		"Loan Product",
		"Loan Type",
		"Loan Disbursement",
		"Loan Repayment",
	];

	const LOWER = ["HR", "Frappe HR", "HRMS", "Attendance", "Leaves", "Shift & Attendance", "Employees"];

	const ESSENTIAL = {
		Selling: [
			"Quick Invoice",
			"New Quick Invoice",
			"Quotation",
			"New Quotation",
			"Sales Order",
			"New Sales Order",
			"Sales Invoice",
			"Payment Entry",
			"Payment Received",
			"Customer",
			"Distributor 360",
		],
		Stock: ["Item", "Stock Entry", "Stock Balance", "Delivery Note"],
		Buying: ["Supplier", "Purchase Order", "Purchase Invoice"],
		Accounting: ["Payment Entry", "Journal Entry", "General Ledger", "Accounts Receivable"],
		Accounts: ["Payment Entry", "Journal Entry", "General Ledger", "Accounts Receivable"],
	};

	const RARE_SECTIONS = {
		"accounting dimensions": true,
		"address and contact": true,
		"terms and conditions": true,
		"more information": true,
		"print settings": true,
		"printing settings": true,
		"printing details": true,
		subscription: true,
		"sales team": true,
		"time sheets": true,
		timesheets: true,
		"loyalty points": true,
		"additional discount": true,
		"e-way bill": true,
		"eway bill": true,
		"transporter info": true,
		"deductions or loss": true,
	};

	const DAILY_FORMS = { "Sales Invoice": true, Quotation: true, "Payment Entry": true };

	function fold(value) {
		return String(value || "")
			.replace(/\s+/g, " ")
			.trim()
			.toLowerCase();
	}

	function plain(value) {
		return String(value == null ? "" : value)
			.replace(/<[^>]*>/g, "")
			.replace(/\s+/g, " ")
			.trim();
	}

	function statusColour(status) {
		const text = plain(status);
		if (!text) return null;
		if (STATUS_COLOURS[text]) return STATUS_COLOURS[text];
		const folded = fold(text);
		for (const key in STATUS_COLOURS) {
			if (Object.prototype.hasOwnProperty.call(STATUS_COLOURS, key) && fold(key) === folded) {
				return STATUS_COLOURS[key];
			}
		}
		return null;
	}

	function simpleBoot() {
		return (window.frappe && frappe.boot && frappe.boot.melliflous_simple) || null;
	}

	function simpleActive() {
		const data = simpleBoot();
		if (!data) return true;
		if (data.active === false || data.active === 0) return false;
		if (data.show_all && data.can_toggle) return false;
		if (data.enabled === false || data.enabled === 0) return false;
		return true;
	}

	function hiddenSet() {
		const data = simpleBoot();
		const rows = (data && data.hidden) || HIDDEN;
		const extras = (data && data.hr_extras) || [];
		const set = {};
		HIDDEN.concat(rows, extras).forEach((name) => {
			set[fold(name)] = true;
		});
		return set;
	}

	function lowerSet() {
		const data = simpleBoot();
		const rows = (data && data.lower) || LOWER;
		const set = {};
		rows.forEach((name) => {
			set[fold(name)] = true;
		});
		return set;
	}

	function essentialFor(workspace) {
		const data = simpleBoot();
		const table = (data && data.shortcuts) || ESSENTIAL;
		const folded = fold(workspace);
		for (const key in table) {
			if (Object.prototype.hasOwnProperty.call(table, key) && fold(key) === folded) {
				const allow = {};
				(table[key] || []).forEach((name) => {
					allow[fold(name)] = true;
				});
				return allow;
			}
		}
		return null;
	}

	function injectTheme() {
		if (!THEME_CSS) return;
		const existing = document.getElementById(THEME_STYLE_ID);
		if (existing && existing.dataset.version === THEME_VERSION && existing.textContent) return;
		if (window.frappe && frappe.dom && typeof frappe.dom.set_style === "function") {
			frappe.dom.set_style(THEME_CSS, THEME_STYLE_ID);
		} else {
			let tag = existing;
			if (!tag) {
				tag = document.createElement("style");
				tag.id = THEME_STYLE_ID;
				(document.head || document.documentElement).appendChild(tag);
			}
			tag.textContent = THEME_CSS;
		}
		const tag = document.getElementById(THEME_STYLE_ID);
		if (tag) tag.dataset.version = THEME_VERSION;
	}

	function recolorIndicator(result, doc, doctype) {
		if (!result || !TRACKED[doctype]) return result;
		const status = doc && doc.status;
		const label = plain(result[0]);
		let colour = statusColour(status) || statusColour(label);
		if (status === "Draft" || label === "Draft") colour = "grey";
		if (!colour) return result;
		return [result[0], colour, result[2]];
	}

	function installIndicators() {
		if (!window.frappe) return;
		if (frappe.get_indicator && !frappe.get_indicator.__melliflous) {
			const original = frappe.get_indicator;
			function wrapped(doc, doctype) {
				const result = original.apply(this, arguments);
				return recolorIndicator(result, doc, doctype || (doc && doc.doctype));
			}
			wrapped.__melliflous = true;
			frappe.get_indicator = wrapped;
		}
		if (!frappe.listview_settings) frappe.listview_settings = {};
		Object.keys(TRACKED).forEach((doctype) => {
			const settings = frappe.listview_settings[doctype];
			if (!settings || !settings.get_indicator || settings.get_indicator.__melliflous) return;
			const original = settings.get_indicator;
			function wrapped(doc) {
				let result = null;
				try {
					result = original.call(this, doc);
				} catch (error) {
					result = null;
				}
				return recolorIndicator(result, doc, doctype);
			}
			wrapped.__melliflous = true;
			settings.get_indicator = wrapped;
		});
	}

	function paintReports() {
		const headers = {};
		document.querySelectorAll(".dt-header .dt-cell, .dt-row-header .dt-cell").forEach((cell) => {
			const index = cell.getAttribute("data-col-index");
			if (index == null) return;
			headers[index] = fold(cell.textContent);
		});
		document.querySelectorAll(".dt-cell__content").forEach((node) => {
			if (node.dataset.melliflousStatus === "1" || node.querySelector(".indicator-pill, .es-badge")) return;
			const cell = node.closest(".dt-cell");
			if (!cell) return;
			const header = headers[cell.getAttribute("data-col-index")] || "";
			if (header.indexOf("status") === -1) return;
			const text = plain(node.textContent);
			const colour = statusColour(text);
			if (!colour) return;
			node.dataset.melliflousStatus = "1";
			node.textContent = "";
			const pill = document.createElement("span");
			pill.className = "indicator-pill " + colour + " es-badge";
			const theme = colour === "orange" ? "amber" : colour === "grey" ? "gray" : colour;
			pill.setAttribute("data-theme", theme);
			pill.textContent = text;
			node.appendChild(pill);
		});
	}

	function isHome() {
		if (!window.frappe || !frappe.get_route) return false;
		const route = frappe.get_route() || [];
		const first = route[0] || "";
		return first === "" || first === "desktop" || first === "Desk";
	}

	function workspaceName() {
		if (window.frappe && frappe.workspace && frappe.workspace.title) {
			return plain(frappe.workspace.title);
		}
		if (window.frappe && frappe.get_route) {
			const route = frappe.get_route() || [];
			if (route[0] === "Workspaces" && route.length > 1) return plain(route[route.length - 1]);
		}
		const title = document.querySelector(".workspace-title, .page-title .title-text");
		return title ? plain(title.textContent) : "";
	}

	function paintModule() {
		const name = fold(workspaceName());
		let module = "";
		if (name.indexOf("selling") !== -1) module = "selling";
		else if (name.indexOf("buying") !== -1) module = "buying";
		else if (name.indexOf("stock") !== -1) module = "stock";
		else if (name.indexOf("account") !== -1) module = "accounting";
		else if (name === "hr" || name.indexOf("attendance") !== -1 || name.indexOf("frappe hr") !== -1) module = "hr";
		else if (name.indexOf("crm") !== -1) module = "crm";
		else if (name.indexOf("manufacturing") !== -1) module = "manufacturing";
		if (module) document.body.setAttribute("data-melliflous-module", module);
		else document.body.removeAttribute("data-melliflous-module");
	}

	function firstName() {
		const user = (window.frappe && frappe.boot && frappe.boot.user) || {};
		const first = plain(user.first_name);
		if (first) return first.split(" ")[0];
		const full = plain(user.full_name);
		if (full && full !== "Administrator") return full.split(" ")[0];
		return "";
	}

	function greetingWords() {
		const hour = new Date().getHours();
		if (hour < 12) return "Good morning";
		if (hour < 17) return "Good afternoon";
		return "Good evening";
	}

	function mountGreeting() {
		let node = document.getElementById("melliflous-greeting");
		if (!isHome()) {
			if (node) node.remove();
			return;
		}
		const host =
			document.querySelector(".desktop-container") ||
			document.querySelector(".layout-main") ||
			document.querySelector("#body");
		if (!host) return;
		if (!node) {
			node = document.createElement("div");
			node.id = "melliflous-greeting";
			node.className = "melliflous-greeting";
			const hello = document.createElement("p");
			hello.className = "melliflous-greeting-hello";
			const date = document.createElement("p");
			date.className = "melliflous-greeting-date";
			node.appendChild(hello);
			node.appendChild(date);
		}
		const name = firstName();
		const helloText = name ? greetingWords() + ", " + name + "!" : greetingWords() + "!";
		node.querySelector(".melliflous-greeting-hello").textContent = helloText;
		node.querySelector(".melliflous-greeting-date").textContent = new Date().toLocaleDateString(undefined, {
			weekday: "long",
			day: "numeric",
			month: "long",
			year: "numeric",
		});
		if (node.parentElement !== host) host.prepend(node);
	}

	function today() {
		if (window.frappe && frappe.datetime && frappe.datetime.get_today) return frappe.datetime.get_today();
		const now = new Date();
		const month = String(now.getMonth() + 1).padStart(2, "0");
		const day = String(now.getDate()).padStart(2, "0");
		return now.getFullYear() + "-" + month + "-" + day;
	}

	function openNew(doctype, values) {
		if (window.frappe && frappe.new_doc) {
			frappe.new_doc(doctype, values);
			return;
		}
		window.location.href = "/desk/" + fold(doctype).replace(/ /g, "-");
	}

	const SHORTCUTS = [
		{ label: "New Quick Invoice", tone: "tone-brand", href: "/desk/quick-invoice" },
		{
			label: "New Quotation",
			tone: "tone-blue",
			run() {
				openNew("Quotation", { company: COMPANY, transaction_date: today() });
			},
		},
		{
			label: "Payment Received",
			tone: "tone-green",
			run() {
				openNew("Payment Entry", { company: COMPANY, payment_type: "Receive", posting_date: today() });
			},
		},
		{
			label: "New Sales Order",
			tone: "tone-teal",
			run() {
				openNew("Sales Order", { company: COMPANY, transaction_date: today() });
			},
		},
		{
			label: "Stock Balance",
			tone: "tone-amber",
			run() {
				if (window.frappe && frappe.set_route) frappe.set_route("query-report", "Stock Balance");
				else window.location.href = "/desk/query-report/Stock%20Balance";
			},
		},
		{ label: "Distributor 360", tone: "tone-maroon", href: "/desk/distributor-360" },
	];

	const SHORTCUT_ICONS = {
		"tone-brand": "M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zm7 1v4h4M8 13h8M8 17h5",
		"tone-blue": "M7 3h10a1 1 0 0 1 1 1v16l-6-3-6 3V4a1 1 0 0 1 1-1z",
		"tone-green": "M3 10h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-8zm2-5h14l2 5H3l2-5zm7 8v4",
		"tone-teal": "M6 6h15l-1.5 9h-12L6 6zM6 6 5 3H2M9 20a1 1 0 1 0 .01-2A1 1 0 0 0 9 20zm8 0a1 1 0 1 0 .01-2A1 1 0 0 0 17 20z",
		"tone-amber": "M4 8h16v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V8zM6 5h12v3H6V5zm3 8h6",
		"tone-maroon": "M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zM5 20a7 7 0 0 1 14 0",
	};

	function shortcutIcon(tone) {
		const icon = document.createElement("span");
		icon.className = "melliflous-shortcut-icon";
		icon.setAttribute("aria-hidden", "true");
		const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
		svg.setAttribute("viewBox", "0 0 24 24");
		svg.setAttribute("fill", "none");
		svg.setAttribute("stroke", "currentColor");
		svg.setAttribute("stroke-width", "1.8");
		svg.setAttribute("stroke-linecap", "round");
		svg.setAttribute("stroke-linejoin", "round");
		const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
		path.setAttribute("d", SHORTCUT_ICONS[tone] || SHORTCUT_ICONS["tone-brand"]);
		svg.appendChild(path);
		icon.appendChild(svg);
		return icon;
	}

	function shortcutBar() {
		let bar = document.getElementById("melliflous-shortcuts");
		if (bar && bar.dataset.icons === "1") return bar;
		if (bar) bar.remove();
		bar = document.createElement("div");
		bar.id = "melliflous-shortcuts";
		bar.className = "melliflous-shortcuts";
		bar.dataset.icons = "1";
		SHORTCUTS.forEach((item) => {
			const button = document.createElement(item.href ? "a" : "button");
			button.className = "melliflous-shortcut " + item.tone;
			const label = document.createElement("span");
			label.className = "melliflous-shortcut-label";
			label.textContent = item.label;
			button.append(shortcutIcon(item.tone), label);
			if (item.href) {
				button.href = item.href;
			} else {
				button.type = "button";
				button.addEventListener("click", item.run);
			}
			bar.appendChild(button);
		});
		return bar;
	}

	function showShortcuts() {
		const home = isHome();
		const selling = fold(workspaceName()) === "selling";
		const bar = document.getElementById("melliflous-shortcuts") || shortcutBar();
		if (!home && !selling) {
			if (bar.parentElement) bar.remove();
			return;
		}
		const host = home
			? document.querySelector(".desktop-container") || document.querySelector(".layout-main")
			: document.querySelector(".layout-main-section") ||
				document.querySelector(".editor-js-container") ||
				document.querySelector(".layout-main");
		if (!host) return;
		const greeting = document.getElementById("melliflous-greeting");
		if (home && greeting && greeting.parentElement === host) greeting.after(bar);
		else if (bar.parentElement !== host) host.prepend(bar);
	}

	function friendlifyEmpty() {
		document.querySelectorAll(".no-result, .empty-state, .msg-box.no-result").forEach((node) => {
			if (node.dataset.melliflousEmpty === "1") return;
			if (node.querySelector(".melliflous-empty-note")) return;
			node.dataset.melliflousEmpty = "1";
			const note = document.createElement("p");
			note.className = "melliflous-empty-note";
			note.textContent = "Nothing here yet. When you add one, it will show up in this list.";
			node.appendChild(note);
		});
	}

	function textHits(value, set) {
		return !!set[fold(value)];
	}

	function hideSimpleSidebar() {
		if (!simpleActive()) {
			document.querySelectorAll(".melliflous-simple-hidden").forEach((node) => {
				node.classList.remove("melliflous-simple-hidden");
			});
			return;
		}
		const hidden = hiddenSet();
		const lower = lowerSet();
		const items = Array.from(document.querySelectorAll(".standard-sidebar-item, .sidebar-item"));
		const lowered = [];
		items.forEach((node) => {
			const label = plain(node.getAttribute("title") || node.textContent);
			const link = node.getAttribute("data-link") || node.getAttribute("data-name") || "";
			if (textHits(label, hidden) || textHits(link, hidden)) {
				node.classList.add("melliflous-simple-hidden");
				return;
			}
			node.classList.remove("melliflous-simple-hidden");
			if (textHits(label, lower) || textHits(link, lower)) lowered.push(node);
		});
		lowered.forEach((node) => {
			const parent = node.parentElement;
			if (parent) parent.appendChild(node);
		});
	}

	function trimWorkspace() {
		if (!simpleActive()) return;
		const allow = essentialFor(workspaceName());
		if (!allow) return;
		document
			.querySelectorAll(".shortcut-widget-box, .widget.shortcut, .link-item, .shortcut-widget")
			.forEach((node) => {
				if (node.closest(".melliflous-shortcuts")) return;
				const named = node.getAttribute("shortcut_name") || "";
				const title = node.querySelector(".widget-title, .widget-title-text, .link-content, .ellipsis");
				const label = plain(named || (title ? title.textContent : node.textContent));
				if (!label || allow[fold(label)]) {
					node.classList.remove("melliflous-simple-hidden");
					return;
				}
				const block = node.closest(".ce-block") || node;
				block.classList.add("melliflous-simple-hidden");
			});
	}

	function mountToggle() {
		const data = simpleBoot();
		let button = document.getElementById("melliflous-simple-toggle");
		if (!data || !data.can_toggle) {
			if (button) button.remove();
			return;
		}
		const navbar = document.querySelector(".desktop-navbar, .navbar .navbar-nav, header.navbar");
		if (!navbar) return;
		if (!button) {
			button = document.createElement("button");
			button.id = "melliflous-simple-toggle";
			button.type = "button";
			button.className = "melliflous-simple-toggle btn btn-default";
			button.addEventListener("click", () => {
				const showAll = simpleActive();
				if (!window.frappe || !frappe.call) return;
				frappe.call({
					method: "melliflous_branding.simple_records.set_show_all",
					args: { show_all: showAll ? 1 : 0 },
					callback() {
						window.location.reload();
					},
				});
			});
		}
		button.textContent = simpleActive() ? "Full desk" : "Simple desk";
		button.title = simpleActive()
			? "Show every module for you. The team keeps the simple desk."
			: "Hide the extra modules again.";
		if (button.parentElement !== navbar) navbar.appendChild(button);
	}

	function applyForm(frm) {
		if (!frm || !DAILY_FORMS[frm.doctype]) return;
		if (frm.is_new && frm.is_new() && !frm.__melliflous_defaults) {
			frm.__melliflous_defaults = true;
			const day = today();
			if (frm.fields_dict && frm.fields_dict.company) frm.set_value("company", COMPANY);
			if (frm.doctype === "Quotation" && frm.fields_dict.transaction_date) frm.set_value("transaction_date", day);
			if ((frm.doctype === "Sales Invoice" || frm.doctype === "Payment Entry") && frm.fields_dict.posting_date) {
				frm.set_value("posting_date", day);
			}
			if (frm.doctype === "Sales Invoice" && frm.fields_dict.update_stock && frm.doc.update_stock) {
				frm.set_value("update_stock", 0);
			}
		}
		if (frm.__melliflous_collapsed || !frm.layout || !frm.layout.sections) return;
		frm.__melliflous_collapsed = true;
		frm.layout.sections.forEach((section) => {
			const label = fold(section.df && section.df.label);
			if (!label || !RARE_SECTIONS[label]) return;
			if (typeof section.collapse === "function") section.collapse(true);
		});
	}

	function installFormHook() {
		if (!window.frappe || !frappe.ui || !frappe.ui.form || !frappe.ui.form.Form) return;
		const proto = frappe.ui.form.Form.prototype;
		if (!proto.refresh || proto.refresh.__melliflous) return;
		const original = proto.refresh;
		function wrapped() {
			const result = original.apply(this, arguments);
			try {
				applyForm(this);
			} catch (error) {
				// A form refresh should still finish if the tidy-up misses a section.
			}
			return result;
		}
		wrapped.__melliflous = true;
		proto.refresh = wrapped;
	}

	const MENU_SELECTOR = ".dropdown-menu, .awesomplete > ul, .popover, .filter-popover, .list-filter-popover";
	let menuLock = false;

	function menuOpen(menu) {
		if (!menu || menu.hidden) return false;
		if (menu.closest("[hidden]")) return false;
		const style = window.getComputedStyle(menu);
		if (style.display === "none" || style.visibility === "hidden") return false;
		const rect = menu.getBoundingClientRect();
		return rect.width > 1 && rect.height > 1;
	}

	function releaseMenu(menu) {
		if (!menu || menu.dataset.melliflousClamped !== "1") return;
		["position", "left", "top", "right", "bottom", "width", "maxWidth", "maxHeight", "overflowY", "overflowX", "zIndex"].forEach(
			(prop) => {
				menu.style[prop] = "";
			}
		);
		delete menu.dataset.melliflousClamped;
	}

	function bottomObstacle() {
		let height = 0;
		document.querySelectorAll("nav, .mobile-navbar, .nav-mobile, .mobile-menu, .navbar-bottom").forEach((node) => {
			const style = window.getComputedStyle(node);
			if (style.position !== "fixed" && style.position !== "sticky") return;
			const rect = node.getBoundingClientRect();
			if (rect.top > window.innerHeight * 0.55 && rect.height > 24 && rect.width > window.innerWidth * 0.6) {
				height = Math.max(height, rect.height);
			}
		});
		return height;
	}

	function setMenuStyle(menu, prop, value) {
		if (menu.style[prop] !== value) menu.style[prop] = value;
	}

	function clampMenu(menu) {
		if (!menuOpen(menu)) {
			releaseMenu(menu);
			return;
		}
		const margin = 8;
		const rect = menu.getBoundingClientRect();
		const vw = window.innerWidth;
		const vh = window.innerHeight;
		const maxBottom = vh - bottomObstacle() - margin;
		const overflows =
			rect.left < margin - 1 ||
			rect.right > vw - margin + 1 ||
			rect.top < margin - 1 ||
			rect.bottom > maxBottom + 1;
		if (!overflows) return;

		const maxW = Math.max(160, vw - margin * 2);
		const width = Math.min(Math.max(rect.width, 160), maxW);
		let left = rect.left;
		if (left + width > vw - margin) left = vw - margin - width;
		if (left < margin) left = margin;

		const spaceBelow = maxBottom - Math.max(rect.top, margin);
		const spaceAbove = Math.max(0, rect.top - margin);
		let top = Math.max(margin, rect.top);
		let maxH = Math.min(rect.height, Math.max(spaceBelow, 88));
		if (rect.bottom > maxBottom && spaceAbove > spaceBelow && spaceAbove >= 88) {
			maxH = Math.min(rect.height, spaceAbove);
			top = Math.max(margin, rect.bottom - maxH);
			maxH = Math.min(maxH, maxBottom - top);
		} else if (rect.bottom > maxBottom) {
			maxH = Math.max(88, maxBottom - top);
		}

		setMenuStyle(menu, "position", "fixed");
		setMenuStyle(menu, "left", Math.round(left) + "px");
		setMenuStyle(menu, "top", Math.round(top) + "px");
		setMenuStyle(menu, "right", "auto");
		setMenuStyle(menu, "bottom", "auto");
		setMenuStyle(menu, "width", Math.round(width) + "px");
		setMenuStyle(menu, "maxWidth", Math.round(maxW) + "px");
		setMenuStyle(menu, "maxHeight", Math.round(maxH) + "px");
		setMenuStyle(menu, "overflowY", "auto");
		setMenuStyle(menu, "overflowX", "hidden");
		setMenuStyle(menu, "zIndex", "2050");
		menu.dataset.melliflousClamped = "1";
	}

	function clampMenus() {
		if (menuLock) return;
		menuLock = true;
		try {
			document.querySelectorAll(MENU_SELECTOR).forEach(clampMenu);
		} finally {
			menuLock = false;
		}
	}

	function installMenuClamp() {
		if (installMenuClamp.done || !document.body) return;
		installMenuClamp.done = true;
		const later = () => window.setTimeout(clampMenus, 0);
		document.addEventListener("click", later, true);
		document.addEventListener("focusin", later, true);
		document.addEventListener("keyup", later, true);
		document.addEventListener("awesomplete-open", later, true);
		document.addEventListener("shown.bs.dropdown", clampMenus, true);
		window.addEventListener("resize", clampMenus);
		window.addEventListener("scroll", clampMenus, true);
		if (window.MutationObserver) {
			let frame = 0;
			const observer = new MutationObserver(() => {
				if (frame || menuLock) return;
				frame = window.requestAnimationFrame(() => {
					frame = 0;
					clampMenus();
				});
			});
			observer.observe(document.body, {
				subtree: true,
				childList: true,
				attributes: true,
				attributeFilter: ["class", "hidden", "style", "aria-expanded"],
			});
		}
		clampMenus();
	}

	function refresh() {
		injectTheme();
		installIndicators();
		installFormHook();
		installMenuClamp();
		paintModule();
		mountGreeting();
		showShortcuts();
		hideSimpleSidebar();
		trimWorkspace();
		mountToggle();
		paintReports();
		friendlifyEmpty();
	}

	function start() {
		refresh();
		if (window.jQuery) {
			jQuery(document).on("page-change.melliflous-desk desktop_screen.melliflous-desk", refresh);
		}
		if (window.frappe && frappe.router && frappe.router.on) frappe.router.on("change", refresh);
		[50, 300, 1000].forEach((ms) => window.setTimeout(refresh, ms));
	}

	window.melliflous_desk = { statusColour, simpleActive, refresh, clampMenus, COMPANY };

	if (window.jQuery) jQuery(start);
	else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
	else start();
})();
