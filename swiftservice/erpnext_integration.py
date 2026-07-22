"""
ERPNext stock & accounts posting for SwiftService.

Uses standard DocTypes only:
- Stock Entry (Material Issue / Material Receipt)
- Sales Invoice (+ GL on submit)
- Payment Entry
- Material Request
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate


def get_ss_settings():
	try:
		return frappe.get_single("SwiftService Settings")
	except Exception:
		return frappe._dict()


def default_company(doc_company=None):
	return (
		doc_company
		or frappe.defaults.get_user_default("Company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
	)


def default_warehouse(company=None, fallback=None):
	if fallback:
		return fallback
	ss = get_ss_settings()
	wh = getattr(ss, "default_service_warehouse", None)
	if wh and frappe.db.exists("Warehouse", wh):
		return wh
	company = default_company(company)
	# Prefer Stores / Service warehouse naming
	for name in ("Stores - ", "Finished Goods - ", "Service Warehouse"):
		rows = frappe.get_all(
			"Warehouse",
			filters={"company": company, "name": ["like", f"%{name}%"], "is_group": 0},
			pluck="name",
			limit=1,
		)
		if rows:
			return rows[0]
	rows = frappe.get_all(
		"Warehouse",
		filters={"company": company, "is_group": 0},
		pluck="name",
		limit=1,
	)
	return rows[0] if rows else None


def default_income_account(company=None, item_code=None):
	ss = get_ss_settings()
	acc = getattr(ss, "default_income_account", None)
	if acc and frappe.db.exists("Account", acc):
		return acc
	if item_code:
		item_acc = frappe.db.get_value("Item Default", {"parent": item_code, "company": company}, "income_account")
		if item_acc:
			return item_acc
		item_acc = frappe.get_cached_value("Item", item_code, "income_account")
		if item_acc:
			return item_acc
	company = default_company(company)
	return frappe.get_cached_value("Company", company, "default_income_account")


def default_cost_center(company=None):
	ss = get_ss_settings()
	cc = getattr(ss, "default_cost_center", None)
	if cc and frappe.db.exists("Cost Center", cc):
		return cc
	company = default_company(company)
	return frappe.get_cached_value("Company", company, "cost_center")


def auto_submit_stock():
	ss = get_ss_settings()
	# default ON so Bin / SLE update
	return cint(getattr(ss, "auto_submit_stock_entry", 1))


def auto_submit_invoice():
	ss = get_ss_settings()
	return cint(getattr(ss, "auto_submit_sales_invoice", 1))


def _serial_string(serial_nos):
	if not serial_nos:
		return None
	if isinstance(serial_nos, (list, tuple)):
		return "\n".join(str(s).strip() for s in serial_nos if s)
	return str(serial_nos).replace(",", "\n").strip() or None


def create_material_issue(
	*,
	company,
	items,
	from_warehouse=None,
	remarks=None,
	reference_doctype=None,
	reference_name=None,
	submit=None,
):
	"""
	items: [{item_code, qty, warehouse?, batch_no?, serial_nos?}]
	Creates Stock Entry Material Issue (outward from warehouse).
	"""
	if not items:
		frappe.throw(_("No items to issue"))

	company = default_company(company)
	wh_default = default_warehouse(company, from_warehouse)
	if not wh_default:
		frappe.throw(_("Set Default Service Warehouse in SwiftService Settings (or on the document)"))

	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Issue"
	se.purpose = "Material Issue"
	se.company = company
	se.posting_date = nowdate()
	if remarks:
		se.remarks = remarks
	if reference_doctype and reference_name:
		# custom fields may not exist — keep in remarks
		se.remarks = (se.remarks or "") + f" | {reference_doctype}: {reference_name}"

	for row in items:
		item_code = row.get("item_code")
		qty = flt(row.get("qty"))
		if not item_code or qty <= 0:
			continue
		wh = row.get("warehouse") or wh_default
		if not wh:
			frappe.throw(_("Warehouse required to issue {0}").format(item_code))
		line = {
			"item_code": item_code,
			"qty": qty,
			"s_warehouse": wh,
			"uom": frappe.db.get_value("Item", item_code, "stock_uom"),
			"conversion_factor": 1,
			"transfer_qty": qty,
		}
		if row.get("batch_no"):
			line["batch_no"] = row["batch_no"]
		serials = _serial_string(row.get("serial_nos") or row.get("serial_no"))
		if serials:
			line["serial_no"] = serials
		se.append("items", line)

	if not se.items:
		frappe.throw(_("No valid stock lines for Material Issue"))

	se.flags.ignore_permissions = True
	se.insert(ignore_permissions=True)

	do_submit = auto_submit_stock() if submit is None else cint(submit)
	if do_submit:
		se.submit()
	return se


def create_material_receipt(
	*,
	company,
	items,
	to_warehouse=None,
	remarks=None,
	reference_doctype=None,
	reference_name=None,
	submit=None,
):
	"""Inward — Material Receipt into warehouse (returns / unused parts)."""
	if not items:
		frappe.throw(_("No items to receive"))

	company = default_company(company)
	wh_default = default_warehouse(company, to_warehouse)
	if not wh_default:
		frappe.throw(_("Set Default Service Warehouse for returns"))

	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Receipt"
	se.purpose = "Material Receipt"
	se.company = company
	se.posting_date = nowdate()
	if remarks:
		se.remarks = remarks
	if reference_doctype and reference_name:
		se.remarks = (se.remarks or "") + f" | {reference_doctype}: {reference_name}"

	for row in items:
		item_code = row.get("item_code")
		qty = flt(row.get("qty"))
		if not item_code or qty <= 0:
			continue
		wh = row.get("warehouse") or wh_default
		line = {
			"item_code": item_code,
			"qty": qty,
			"t_warehouse": wh,
			"uom": frappe.db.get_value("Item", item_code, "stock_uom"),
			"conversion_factor": 1,
			"transfer_qty": qty,
		}
		if row.get("batch_no"):
			line["batch_no"] = row["batch_no"]
		serials = _serial_string(row.get("serial_nos") or row.get("serial_no"))
		if serials:
			line["serial_no"] = serials
		se.append("items", line)

	if not se.items:
		frappe.throw(_("No valid stock lines for Material Receipt"))

	se.flags.ignore_permissions = True
	se.insert(ignore_permissions=True)
	do_submit = auto_submit_stock() if submit is None else cint(submit)
	if do_submit:
		se.submit()
	return se


def submit_sales_invoice(si):
	"""Submit SI so GL Entries / receivable ledger post."""
	if si.docstatus == 1:
		return si
	si.flags.ignore_permissions = True
	si.submit()
	return si


def create_payment_entry_for_invoice(sales_invoice, amount, mode_of_payment=None, reference=None, posting_date=None):
	"""Create + submit Payment Entry against Sales Invoice (Accounts receivable)."""
	if not sales_invoice or not frappe.db.exists("Sales Invoice", sales_invoice):
		frappe.throw(_("Sales Invoice required for payment"))

	si = frappe.get_doc("Sales Invoice", sales_invoice)
	if si.docstatus != 1:
		frappe.throw(_("Submit Sales Invoice {0} before recording payment").format(sales_invoice))

	amt = flt(amount)
	if amt <= 0:
		frappe.throw(_("Payment amount must be positive"))

	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	pe = get_payment_entry(si.doctype, si.name, party_amount=amt)
	pe.posting_date = posting_date or nowdate()
	if mode_of_payment and frappe.db.exists("Mode of Payment", mode_of_payment):
		pe.mode_of_payment = mode_of_payment
	if reference:
		pe.reference_no = reference
		pe.reference_date = pe.posting_date
	pe.flags.ignore_permissions = True
	pe.insert(ignore_permissions=True)
	pe.submit()
	return pe
