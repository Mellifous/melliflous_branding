# Copyright (c) 2026, Melliflous and contributors
# License: MIT. See license.txt
"""Which ledger rows belong to a cancelled voucher, and which live document blocks delete.

No Frappe import. A cancelled Sales Invoice keeps its own Payment Ledger,
GL, and stock rows. Those rows are delinked or marked cancelled, and they are
the only reason the link check refuses the delete. A submitted document that
still points at the voucher is a real block and is named in the message.
"""

from __future__ import annotations

LEDGER_DOCTYPES = frozenset(
	{
		"Payment Ledger Entry",
		"GL Entry",
		"Stock Ledger Entry",
		"Repost Payment Ledger",
		"Repost Payment Ledger Items",
		"Repost Item Valuation",
		"Advance Payment Ledger Entry",
	}
)


def clean(value) -> str:
	return " ".join(str(value or "").split())


def _flag(value) -> bool:
	if value is True:
		return True
	text = clean(value).lower()
	return text in {"1", "true", "yes"}


def _status(value) -> int:
	try:
		return int(value or 0)
	except (TypeError, ValueError):
		return 0


def _points_at(row, document_type, document_name) -> bool:
	"""True when voucher_no or against_voucher_no is this document."""
	name = clean(document_name)
	dtype = clean(document_type)
	if not name:
		return False
	voucher_no = clean(row.get("voucher_no"))
	voucher_type = clean(row.get("voucher_type"))
	against_no = clean(row.get("against_voucher_no"))
	against_type = clean(row.get("against_voucher_type"))
	own_voucher = voucher_no == name and (not voucher_type or voucher_type == dtype)
	own_against = against_no == name and (not against_type or against_type == dtype)
	return own_voucher or own_against


def _is_closed_ledger(row) -> bool:
	"""Delinked, cancelled, or a cancelled document. A live posting is none of these."""
	return _flag(row.get("delinked")) or _flag(row.get("is_cancelled")) or _status(row.get("docstatus")) == 2


def ledger_rows_to_remove(document_type, document_name, rows) -> list:
	"""Names to delete before the voucher itself.

	Payment Ledger and Advance Payment Ledger rows must be delinked or cancelled.
	GL Entry and Stock Ledger Entry must be marked cancelled. Repost rows that
	name this voucher are removed whether or not they were submitted, because
	they exist only to rebuild this voucher.
	"""
	chosen = []
	seen = set()
	for row in rows or []:
		if not isinstance(row, dict):
			continue
		kind = clean(row.get("doctype"))
		name = clean(row.get("name"))
		if not kind or not name or (kind, name) in seen:
			continue
		if not _points_at(row, document_type, document_name):
			continue
		if kind in {"Payment Ledger Entry", "Advance Payment Ledger Entry", "GL Entry", "Stock Ledger Entry"}:
			if not _is_closed_ledger(row):
				continue
			if kind in {"GL Entry", "Stock Ledger Entry"} and not _flag(row.get("is_cancelled")):
				continue
		elif kind not in LEDGER_DOCTYPES:
			continue
		seen.add((kind, name))
		chosen.append({"doctype": kind, "name": name})
	chosen.sort(key=lambda row: (0 if row["doctype"].endswith("Items") else 1, row["doctype"], row["name"]))
	return chosen


def uncleared_ledger_message(document_type, document_name, rows) -> str | None:
	"""A ledger row that still posts this voucher, so it must not be deleted."""
	removing = {(row["doctype"], row["name"]) for row in ledger_rows_to_remove(document_type, document_name, rows)}
	for row in rows or []:
		if not isinstance(row, dict):
			continue
		kind = clean(row.get("doctype"))
		name = clean(row.get("name"))
		if kind not in LEDGER_DOCTYPES or not name:
			continue
		if not _points_at(row, document_type, document_name):
			continue
		if (kind, name) in removing:
			continue
		return (
			f"Cannot delete {clean(document_type)} {clean(document_name)}. "
			f"{kind} {name} is still linked to it and is not cancelled. "
			"Cancel that document first."
		)
	return None


def live_link_message(document_type, document_name, references) -> str | None:
	"""The first submitted document, other than a ledger row, that still points here."""
	for row in references or []:
		if not isinstance(row, dict):
			continue
		kind = clean(row.get("doctype"))
		name = clean(row.get("name"))
		if not kind or not name or kind in LEDGER_DOCTYPES:
			continue
		if _status(row.get("docstatus")) != 1:
			continue
		if kind == clean(document_type) and name == clean(document_name):
			continue
		return (
			f"Cannot delete {clean(document_type)} {clean(document_name)}. "
			f"{kind} {name} is submitted and still linked to it. "
			"Cancel that document first."
		)
	return None
