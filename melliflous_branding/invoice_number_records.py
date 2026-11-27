# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Editable Sales Invoice numbers.

The number the user sees is the document name, which is what GST and e-invoice
send. The next number is the next serial after the highest one already stored
for that company and prefix, including drafts and cancelled invoices. Posting
dates stay in the same order as the serials. Cancelled invoices do not set
that order, but their numbers stay taken.

Two people saving at once share a row lock on `tabSeries` for that company and
prefix. The lock is held until the request commits or rolls back, so the second
save sees the first number and is told to change it.
"""

from __future__ import annotations

import hashlib

import frappe
from frappe import _
from frappe.utils import today

from melliflous_branding.access import require_desk_user
from melliflous_branding.invoice_number import (
	INVOICE_NO_FIELD,
	InvoiceNumberError,
	clean,
	clean_invoice_no,
	detect_prefix,
	duplicate_message,
	format_problem,
	plan_invoice,
	series_prefix,
	split_serial,
)

SETTINGS = "Melliflous Settings"
SERIES_CHILD = "Sales Invoice Series"
FIELDNAME = "custom_invoice_no"


def ensure_invoice_numbers() -> None:
	"""Custom field on Sales Invoice. Safe to run more than once."""
	if not frappe.db.exists("DocType", "Sales Invoice"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Sales Invoice": [dict(INVOICE_NO_FIELD)]}, update=True)


def prepare_invoice_number(doc, method=None):
	"""Company and naming series before Frappe names the invoice."""
	if not doc or doc.doctype != "Sales Invoice":
		return
	if not doc.get("company"):
		try:
			doc.company = frappe.defaults.get_user_default("company")
		except Exception:
			pass
	if not clean(doc.get("naming_series")):
		doc.naming_series = fallback_series(doc.get("is_return"))
	if _has_field(doc) and doc.get(FIELDNAME):
		doc.set(FIELDNAME, clean_invoice_no(doc.get(FIELDNAME)))


def assign_invoice_number(doc, method=None):
	"""`autoname` hook. Frappe calls this only when the name is still empty.

	Amended invoices are named by ERPNext before this hook, as `original-1`.
	"""
	if not doc or doc.doctype != "Sales Invoice" or doc.get("amended_from"):
		return
	chosen = clean_invoice_no(doc.get(FIELDNAME)) if _has_field(doc) else ""
	try:
		plan = _plan(doc, chosen or None, current_name=None)
	except InvoiceNumberError as exc:
		frappe.throw(_(str(exc)))
	if plan.get("error"):
		frappe.throw(_(plan["error"]))
	number = chosen or plan.get("suggested")
	if not number:
		frappe.throw(_(plan.get("warning") or _("No invoice number fits this date. Please change the date.")))
	doc.name = number
	if _has_field(doc):
		doc.set(FIELDNAME, number)


def validate_invoice_number(doc, method=None):
	"""Reject a repeated serial or a number that breaks posting-date order.

	A new document takes this number as its name before insert. A saved draft
	is renamed in on_update, after the row has been written. Submitted invoices
	stay with Invoice Admin.
	"""
	if not doc or doc.doctype != "Sales Invoice":
		return
	if int(doc.docstatus or 0) == 2:
		return
	if int(doc.docstatus or 0) == 1 and not _resubmit_or_changed(doc):
		return
	if doc.get("amended_from") and _is_new(doc) and not clean_invoice_no(doc.get(FIELDNAME)):
		if _has_field(doc) and doc.name:
			doc.set(FIELDNAME, doc.name)
		return
	chosen = clean_invoice_no(doc.get(FIELDNAME)) if _has_field(doc) else ""
	if not chosen:
		chosen = "" if _is_new(doc) else clean_invoice_no(doc.name)
	if not chosen and _is_new(doc):
		return
	current = None if _is_new(doc) else doc.name
	try:
		plan = _plan(doc, chosen, current_name=current)
	except InvoiceNumberError as exc:
		frappe.throw(_(str(exc)))
	if plan.get("error"):
		frappe.throw(_(plan["error"]))
	if _is_new(doc):
		if chosen and doc.name != chosen:
			doc.name = chosen
		if _has_field(doc) and doc.name:
			doc.set(FIELDNAME, doc.name)
		return
	if int(doc.docstatus or 0) != 0:
		return
	if _has_field(doc) and not clean_invoice_no(doc.get(FIELDNAME)) and doc.name:
		doc.set(FIELDNAME, doc.name)


def sync_invoice_number(doc, method=None):
	"""Rename after save when Invoice No changed on a draft, including the save that submits it."""
	if not doc or doc.doctype != "Sales Invoice" or int(doc.docstatus or 0) == 2:
		return
	if doc.flags.get("melliflous_invoice_renaming"):
		return
	if int(doc.docstatus or 0) == 1 and not _was_draft(doc):
		return
	chosen = clean_invoice_no(doc.get(FIELDNAME)) if _has_field(doc) else ""
	if not chosen or chosen == doc.name:
		return
	doc.flags.melliflous_invoice_renaming = True
	_rename_draft(doc, chosen)


@frappe.whitelist()
def suggest_invoice_no(company=None, posting_date=None, naming_series=None, is_return=0):
	"""Next invoice number for a new Sales Invoice on this date."""
	require_desk_user()
	if not frappe.has_permission("Sales Invoice", "create"):
		frappe.throw(_("You are not allowed to create a Sales Invoice."), frappe.PermissionError)
	company = _require_company(company)
	when = posting_date or today()
	prefix, starting, digits = _series(company, naming_series, when, is_return)
	rows = _series_rows(company, prefix)
	plan = plan_invoice(
		prefix,
		rows,
		when,
		starting_number=starting,
		digits=digits,
	)
	return {"invoice_no": plan.get("suggested"), "warning": plan.get("warning"), "prefix": prefix}


@frappe.whitelist()
def check_invoice_no(invoice_no=None, company=None, posting_date=None, current=None, naming_series=None, is_return=0):
	"""Live check. Does not save. `ok` is false when the number must be changed."""
	require_desk_user()
	if not frappe.has_permission("Sales Invoice", "read"):
		frappe.throw(_("You are not allowed to read a Sales Invoice."), frappe.PermissionError)
	number = clean_invoice_no(invoice_no)
	company = _require_company(company)
	when = posting_date or today()
	prefix = _prefix_for(number, company, naming_series, when, is_return)
	rows = _series_rows(company, prefix)
	starting, digits = _start_and_digits(company, naming_series, when, is_return, prefix)
	plan = plan_invoice(
		prefix,
		rows,
		when,
		starting_number=starting,
		digits=digits,
		current_name=clean_invoice_no(current) or None,
		chosen=number,
	)
	plan = _apply_global_name(number, current, plan)
	if plan.get("error"):
		return {
			"ok": False,
			"invoice_no": number,
			"message": plan["error"],
			"next_free": plan.get("suggested"),
		}
	return {"ok": True, "invoice_no": number, "message": None, "next_free": plan.get("suggested")}


def _require_company(company) -> str:
	company = clean(company)
	if not company:
		frappe.throw(_("Choose a company first."))
	from melliflous_branding.companies import get_permitted_companies

	allowed = get_permitted_companies()
	if allowed and company not in allowed:
		frappe.throw(_("You cannot use company {0}.").format(company), frappe.PermissionError)
	return company


def fallback_series(is_return) -> str:
	"""First Sales Invoice naming series, or the return series when this is a credit note."""
	lines = _naming_options()
	if cint_flag(is_return):
		for line in lines:
			if "RET" in line.upper():
				return line
		return "ACC-SINV-RET-.YYYY.-"
	if lines:
		return lines[0]
	return "ACC-SINV-.YYYY.-"


def cint_flag(value) -> bool:
	text = str(value or "").strip().lower()
	return text in {"1", "true", "yes"}


def _plan(doc, chosen, current_name):
	company = clean(doc.get("company"))
	if not company:
		raise InvoiceNumberError("Choose a company first.")
	if chosen:
		problem = format_problem(chosen)
		if problem:
			return {"suggested": None, "warning": None, "error": problem}
	when = doc.get("posting_date") or today()
	prefix = _prefix_for(
		chosen,
		company,
		doc.get("naming_series"),
		when,
		doc.get("is_return"),
	)
	_lock(company, prefix)
	rows = _series_rows(company, prefix)
	starting, digits = _start_and_digits(company, doc.get("naming_series"), when, doc.get("is_return"), prefix)
	plan = plan_invoice(
		prefix,
		rows,
		when,
		starting_number=starting,
		digits=digits,
		current_name=current_name,
		chosen=chosen,
	)
	return _apply_global_name(chosen, current_name, plan)


def _prefix_for(chosen, company, naming_series, when, is_return) -> str:
	configured, _starting, _digits = _series(company, naming_series, when, is_return)
	if chosen and split_serial(chosen, configured):
		return configured
	detected = detect_prefix(chosen) if chosen else None
	if chosen and detected is not None:
		return detected
	return configured


def _series(company, naming_series, when, is_return):
	"""Prefix, optional starting number, and digit width from settings or the naming series."""
	row = _setting(company)
	prefix = clean(row.get("prefix")) if row else ""
	starting = row.get("starting_number") if row else None
	if prefix:
		return prefix, starting, 0
	pattern = clean(naming_series) or fallback_series(is_return)
	resolved, digits = series_prefix(pattern, when, _abbr(company))
	if not resolved:
		raise InvoiceNumberError(
			"Set an invoice prefix for this company on Melliflous Settings. "
			"The naming series did not produce a prefix."
		)
	return resolved, starting, digits


def _start_and_digits(company, naming_series, when, is_return, prefix):
	configured, starting, digits = _series(company, naming_series, when, is_return)
	if prefix == configured:
		return starting, digits
	return None, digits


def _setting(company):
	if not company or not frappe.db.table_exists(SERIES_CHILD):
		return None
	rows = frappe.get_all(
		SERIES_CHILD,
		filters={"parent": SETTINGS, "parenttype": SETTINGS, "company": company},
		fields=["prefix", "starting_number"],
		limit=1,
	)
	return rows[0] if rows else None


def _abbr(company) -> str:
	try:
		if company and frappe.db.has_column("Company", "abbr"):
			return clean(frappe.db.get_value("Company", company, "abbr"))
	except Exception:
		return ""
	return ""


def _naming_options() -> list[str]:
	try:
		meta = frappe.get_meta("Sales Invoice")
		field = meta.get_field("naming_series") if meta else None
		options = field.options if field else ""
	except Exception:
		options = ""
	return [clean(line) for line in str(options or "").split("\n") if clean(line)]


def _series_rows(company, prefix) -> list:
	"""Every Sales Invoice in this company and prefix: draft, submitted, and cancelled."""
	if not company or not frappe.db.table_exists("Sales Invoice"):
		return []
	if prefix:
		like = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
		return frappe.db.sql(
			"""select name, posting_date, docstatus
			   from `tabSales Invoice`
			   where company=%s and name like %s""",
			(company, like),
			as_dict=True,
		)
	return frappe.db.sql(
		"""select name, posting_date, docstatus
		   from `tabSales Invoice`
		   where company=%s""",
		(company,),
		as_dict=True,
	)


def _lock(company, prefix) -> None:
	"""Serialize allocation for this company and prefix until the request ends."""
	if not company or not frappe.db.table_exists("Series"):
		return
	key = "mb-si-" + hashlib.sha1(f"{company}\n{prefix}".encode()).hexdigest()[:24]
	frappe.db.sql(
		"insert into `tabSeries` (`name`, `current`) values (%s, 0) on duplicate key update `name`=`name`",
		key,
	)
	frappe.db.sql("select `name` from `tabSeries` where `name`=%s for update", key)


def _apply_global_name(chosen, current, plan) -> dict:
	"""Names are unique on the doctype, including another company's invoice."""
	if not chosen or plan.get("error") or not frappe.db.table_exists("Sales Invoice"):
		return plan
	current_name = clean_invoice_no(current)
	if current_name and current_name.casefold() == clean_invoice_no(chosen).casefold():
		return plan
	if not frappe.db.exists("Sales Invoice", chosen):
		return plan
	updated = dict(plan)
	updated["error"] = duplicate_message(chosen, plan.get("suggested"))
	return updated


def _rename_draft(doc, new_name) -> None:
	status = int(doc.docstatus or 0)
	if status == 2 or (status == 1 and not _was_draft(doc)):
		frappe.throw(_("This invoice is already submitted. An Invoice Admin can rename it from the menu."))
	if clean(doc.get("irn")):
		frappe.throw(_("This invoice has an IRN. Cancel the e-invoice before changing the number."))
	old = doc.name
	if not old or old == new_name:
		return
	frappe.flags.melliflous_invoice_no_edit = True
	try:
		from frappe.model.rename_doc import rename_doc

		rename_doc(doc.doctype, old, new_name, force=True, show_alert=False, rebuild_search=False)
	finally:
		frappe.flags.melliflous_invoice_no_edit = False
	doc.name = new_name
	if _has_field(doc):
		doc.set(FIELDNAME, new_name)
	try:
		for child in doc.get_all_children():
			child.parent = new_name
	except Exception:
		pass


def _was_draft(doc) -> bool:
	try:
		before = doc.get_doc_before_save()
	except Exception:
		return False
	return bool(before) and int(getattr(before, "docstatus", 0) or 0) == 0


def _resubmit_or_changed(doc) -> bool:
	"""True while submitting, or when a submitted invoice's date or number changed."""
	try:
		before = doc.get_doc_before_save()
	except Exception:
		before = None
	if not before or int(getattr(before, "docstatus", 0) or 0) != 1:
		return True
	try:
		return bool(doc.has_value_changed("posting_date") or doc.has_value_changed(FIELDNAME))
	except Exception:
		return False


def _is_new(doc) -> bool:
	try:
		return bool(doc.is_new())
	except Exception:
		return False


def _has_field(doc) -> bool:
	try:
		return bool(frappe.get_meta(doc.doctype).has_field(FIELDNAME))
	except Exception:
		return False
