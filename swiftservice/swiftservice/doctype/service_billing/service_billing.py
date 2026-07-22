import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, now_datetime, nowdate


COVERED = {"Warranty", "AMC", "FOC", "Goodwill"}
CHARGEABLE = {"Chargeable"}

ALLOWED_TRANSITIONS = {
	"Draft": {"Commercial Review", "Warranty Settlement", "Cancelled"},
	"Commercial Review": {"Customer Approval", "Approved", "Draft", "Cancelled"},
	"Customer Approval": {"Approved", "Commercial Review", "Cancelled", "Disputed"},
	"Approved": {"Invoice Generated", "Warranty Settlement", "Customer Approval", "Cancelled"},
	"Invoice Generated": {"Payment Pending", "Payment Received", "Closed", "Cancelled"},
	"Payment Pending": {"Payment Received", "Disputed", "Closed"},
	"Payment Received": {"Closed"},
	"Warranty Settlement": {"Closed", "Cancelled"},
	"Closed": set(),
	"Cancelled": set(),
	"Disputed": {"Commercial Review", "Customer Approval", "Cancelled"},
}

STATUS_ORDER = [
	"Draft",
	"Commercial Review",
	"Customer Approval",
	"Approved",
	"Invoice Generated",
	"Payment Pending",
	"Payment Received",
	"Closed",
]

DEFAULT_LABOUR_RATE = 500.0
DEFAULT_TRAVEL_RATE = 12.0


class ServiceBilling(Document):
	def validate(self):
		self._set_defaults()
		self._fetch_links()
		self._apply_line_amounts()
		self._recalc_totals()
		self._validate_amounts()

	def before_submit(self):
		if self.status in (None, "", "Draft", "Commercial Review", "Approved"):
			if not cint(self.customer_invoice_required):
				self.status = "Warranty Settlement"
			elif self.sales_invoice:
				self.status = "Invoice Generated"
			else:
				self.status = "Approved"

	def on_submit(self):
		self._append_timeline(_("Billing submitted"))

	def on_cancel(self):
		self.status = "Cancelled"

	def on_update_after_submit(self):
		if self.has_value_changed("status"):
			old = self.get_doc_before_save()
			if old:
				self._assert_transition(old.status, self.status)

	def _set_defaults(self):
		if not self.naming_series:
			self.naming_series = "BILL-.YYYY.-.#####"
		if not self.status:
			self.status = "Draft"
		if not self.billing_date:
			self.billing_date = nowdate()
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)
		if not self.currency:
			self.currency = frappe.db.get_value("Company", self.company, "default_currency") if self.company else None
		if not self.commercial_type:
			self.commercial_type = "Paid Service"

	def _fetch_links(self):
		if self.service_request and frappe.db.exists("Swift Service Request", self.service_request):
			sr = frappe.db.get_value(
				"Swift Service Request",
				self.service_request,
				["customer", "company", "branch", "amc_contract", "warranty_status", "warranty_end", "amc_status"],
				as_dict=True,
			)
			if sr:
				for src, dst in (
					("customer", "customer"),
					("company", "company"),
					("branch", "branch"),
					("amc_contract", "amc_contract"),
				):
					if not self.get(dst) and sr.get(src):
						self.set(dst, sr.get(src))

	def _assert_transition(self, old_status, new_status):
		if old_status == new_status:
			return
		allowed = ALLOWED_TRANSITIONS.get(old_status) or set()
		if new_status not in allowed and "System Manager" not in frappe.get_roles():
			frappe.throw(_("Cannot change billing status from {0} to {1}").format(old_status, new_status))

	def _append_timeline(self, activity, remarks=""):
		self.append(
			"billing_timeline",
			{
				"activity": activity,
				"user": frappe.session.user,
				"time": now_datetime(),
				"remarks": remarks,
			},
		)

	def _line_billable(self, coverage):
		return (coverage or "Chargeable") not in COVERED

	def _apply_line_amounts(self):
		for row in self.labour_charges or []:
			row.amount = flt(row.hours) * flt(row.hourly_rate)
		for row in self.spare_charges or []:
			row.amount = max(flt(row.qty) * flt(row.rate) - flt(row.discount), 0)
		for row in self.travel_charges or []:
			if not flt(row.amount):
				row.amount = flt(row.distance_km) * flt(row.rate)

	def _sum_billable(self, rows, amount_field="amount"):
		total = 0
		covered = 0
		for row in rows or []:
			amt = flt(row.get(amount_field))
			if self._line_billable(row.get("coverage")):
				total += amt
			else:
				covered += amt
		return total, covered

	def _recalc_totals(self):
		labour, labour_cov = self._sum_billable(self.labour_charges)
		travel, travel_cov = self._sum_billable(self.travel_charges)
		spare, spare_cov = self._sum_billable(self.spare_charges)
		misc, misc_cov = self._sum_billable(self.misc_charges)

		self.labour_total = labour
		self.travel_total = travel
		self.spare_total = spare
		self.misc_total = misc
		self.covered_amount = labour_cov + travel_cov + spare_cov + misc_cov
		self.discount_total = sum(flt(r.amount) for r in (self.discounts or []))

		subtotal = labour + travel + spare + misc - self.discount_total
		if subtotal < 0:
			subtotal = 0
		self.taxable_amount = subtotal

		# tax rows or flat % from template rate on first row
		if self.tax_rows:
			self.tax_total = sum(flt(r.amount) or (flt(r.rate) * subtotal / 100.0) for r in self.tax_rows)
			for r in self.tax_rows:
				if not flt(r.amount) and flt(r.rate):
					r.amount = flt(r.rate) * subtotal / 100.0
			self.tax_total = sum(flt(r.amount) for r in self.tax_rows)
		else:
			self.tax_total = 0

		self.grand_total = flt(self.taxable_amount) + flt(self.tax_total)
		self.invoice_amount = self.grand_total if cint(self.customer_invoice_required) else 0

		self.amount_paid = sum(flt(r.amount) for r in (self.payments or []))
		self.outstanding_amount = max(flt(self.invoice_amount) - flt(self.amount_paid), 0)

		self.total_cost = (
			flt(self.labour_cost) + flt(self.material_cost) + flt(self.travel_cost) + flt(self.vendor_cost)
		)
		self.revenue = flt(self.invoice_amount)
		self.gross_margin = flt(self.revenue) - flt(self.total_cost)
		self.gross_margin_pct = (self.gross_margin / self.revenue * 100.0) if flt(self.revenue) else 0

	def _validate_amounts(self):
		if flt(self.grand_total) < 0 or flt(self.invoice_amount) < 0:
			frappe.throw(_("Negative invoice values are not allowed"))

	def detect_coverage(self):
		"""Set warranty/AMC flags from Service Request / AMC Contract."""
		warranty = False
		amc = False
		if self.service_request and frappe.db.exists("Swift Service Request", self.service_request):
			sr = frappe.db.get_value(
				"Swift Service Request",
				self.service_request,
				["warranty_status", "warranty_end", "amc_status", "amc_contract", "amc_end"],
				as_dict=True,
			)
			if sr:
				if (sr.warranty_status or "").lower() in ("active", "under warranty", "valid") or (
					sr.warranty_end and getdate(sr.warranty_end) >= getdate()
				):
					warranty = True
				if (sr.amc_status or "").lower() in ("active", "valid") or (
					sr.amc_end and getdate(sr.amc_end) >= getdate()
				):
					amc = True
				if not self.amc_contract and sr.amc_contract:
					self.amc_contract = sr.amc_contract

		if self.amc_contract and frappe.db.exists("AMC Contract", self.amc_contract):
			amc_doc = frappe.db.get_value(
				"AMC Contract", self.amc_contract, ["status", "end_date"], as_dict=True
			)
			if amc_doc and amc_doc.status == "Active" and (
				not amc_doc.end_date or getdate(amc_doc.end_date) >= getdate()
			):
				amc = True

		self.warranty_active = 1 if warranty else 0
		self.amc_active = 1 if amc else 0

		# default coverage rules
		if warranty:
			self.labour_covered = 1
			self.spare_covered = 1
			self.travel_covered = 0  # configurable default: travel chargeable
			self.customer_invoice_required = 0
			self.commercial_type = "Warranty"
			self.customer_approval = "Not Required"
		elif amc:
			self.labour_covered = 1
			self.spare_covered = 0  # spares often excluded
			self.travel_covered = 1
			self.customer_invoice_required = 0
			self.commercial_type = "AMC"
			self.customer_approval = "Not Required"
		else:
			self.labour_covered = 0
			self.spare_covered = 0
			self.travel_covered = 0
			self.customer_invoice_required = 1
			if self.commercial_type in ("Warranty", "AMC"):
				self.commercial_type = "Paid Service"
			if self.customer_approval == "Not Required" and flt(self.grand_total) > 0:
				self.customer_approval = "Pending"

		return self

	def apply_coverage_to_lines(self):
		lab_cov = "Warranty" if cint(self.warranty_active) else ("AMC" if cint(self.amc_active) and cint(self.labour_covered) else "Chargeable")
		if not cint(self.labour_covered):
			lab_cov = "Chargeable"
		sp_cov = "Warranty" if cint(self.warranty_active) and cint(self.spare_covered) else (
			"AMC" if cint(self.amc_active) and cint(self.spare_covered) else "Chargeable"
		)
		tr_cov = "Warranty" if cint(self.warranty_active) and cint(self.travel_covered) else (
			"AMC" if cint(self.amc_active) and cint(self.travel_covered) else "Chargeable"
		)

		for row in self.labour_charges or []:
			if not row.coverage or row.coverage == "Chargeable":
				row.coverage = lab_cov
		for row in self.spare_charges or []:
			# respect explicit chargeable flag from source if already set to Warranty
			if not row.coverage:
				row.coverage = sp_cov
		for row in self.travel_charges or []:
			if not row.coverage or row.coverage == "Chargeable":
				row.coverage = tr_cov
		for row in self.misc_charges or []:
			if not row.coverage:
				row.coverage = "Chargeable"
		self._apply_line_amounts()
		self._recalc_totals()
		# refresh invoice required after totals
		if flt(self.labour_total) + flt(self.spare_total) + flt(self.travel_total) + flt(self.misc_total) <= 0:
			self.customer_invoice_required = 0
			if cint(self.warranty_active):
				self.commercial_type = "Warranty"
			elif cint(self.amc_active):
				self.commercial_type = "AMC"
		elif cint(self.covered_amount) and (
			flt(self.labour_total) + flt(self.spare_total) + flt(self.travel_total) + flt(self.misc_total) > 0
		):
			self.commercial_type = "Mixed"
			self.customer_invoice_required = 1
			if self.customer_approval == "Not Required":
				self.customer_approval = "Pending"
		return self

	def populate_from_sources(self):
		self.detect_coverage()
		self._populate_from_report()
		self._populate_from_repair()
		self._populate_from_visit_fallback()
		self.apply_coverage_to_lines()
		# cost side
		self.material_cost = sum(flt(r.amount) for r in (self.spare_charges or []))
		self.labour_cost = sum(flt(r.amount) for r in (self.labour_charges or []))
		self.travel_cost = sum(flt(r.amount) for r in (self.travel_charges or []))
		self._recalc_totals()
		return self

	def _populate_from_report(self):
		if not self.service_report or not frappe.db.exists("Service Report", self.service_report):
			return
		srpt = frappe.get_doc("Service Report", self.service_report)
		if not self.service_request:
			self.service_request = srpt.service_request
		if not self.repair_order and srpt.repair_order:
			self.repair_order = srpt.repair_order
		if not self.customer and srpt.customer:
			self.customer = srpt.customer

		if not self.labour_charges:
			hours = flt(srpt.total_hours) or 1
			# prefer time logs
			if srpt.time_logs:
				for log in srpt.time_logs:
					h = flt(log.hours) or hours
					self.append(
						"labour_charges",
						{
							"activity": log.activity or "Service Labour",
							"engineer": log.engineer or srpt.primary_engineer,
							"hours": h,
							"hourly_rate": DEFAULT_LABOUR_RATE,
						},
					)
			elif flt(srpt.labour_amount):
				self.append(
					"labour_charges",
					{
						"activity": "Service Labour",
						"engineer": srpt.primary_engineer,
						"hours": hours,
						"hourly_rate": flt(srpt.labour_amount) / hours if hours else DEFAULT_LABOUR_RATE,
					},
				)
			elif hours:
				self.append(
					"labour_charges",
					{
						"activity": "Service Labour",
						"engineer": srpt.primary_engineer,
						"hours": hours,
						"hourly_rate": DEFAULT_LABOUR_RATE,
					},
				)

		if not self.spare_charges:
			for row in srpt.spare_used or []:
				if not row.item_code:
					continue
				coverage = "Chargeable"
				if cint(row.warranty_claimable):
					coverage = "Warranty"
				elif not cint(row.chargeable) and cint(self.warranty_active):
					coverage = "Warranty"
				rate = flt(row.cost)
				if not rate and frappe.db.exists("Item", row.item_code):
					rate = flt(frappe.db.get_value("Item", row.item_code, "standard_rate"))
				self.append(
					"spare_charges",
					{
						"item_code": row.item_code,
						"qty": flt(row.qty) or 1,
						"rate": rate,
						"coverage": coverage,
						"serial_no": row.serial_no,
						"spare_request": row.spare_request,
					},
				)

		if not self.travel_charges and flt(srpt.travel_amount):
			self.append(
				"travel_charges",
				{
					"description": "Travel",
					"distance_km": 0,
					"rate": 0,
					"amount": flt(srpt.travel_amount),
				},
			)

		if not self.misc_charges and flt(srpt.misc_amount):
			self.append(
				"misc_charges",
				{"charge_type": "Other", "description": "Misc from Service Report", "amount": flt(srpt.misc_amount)},
			)

		if flt(srpt.tax_amount) and not self.tax_rows:
			self.append("tax_rows", {"tax_type": "GST", "amount": flt(srpt.tax_amount)})

	def _populate_from_repair(self):
		if not self.repair_order or not frappe.db.exists("Repair Order", self.repair_order):
			return
		ro = frappe.get_doc("Repair Order", self.repair_order)
		if not self.service_request:
			self.service_request = ro.service_request
		for row in ro.spare_used or []:
			if not row.item_code:
				continue
			exists = any(s.item_code == row.item_code for s in (self.spare_charges or []))
			if exists:
				continue
			self.append(
				"spare_charges",
				{
					"item_code": row.item_code,
					"qty": flt(row.qty) or 1,
					"rate": flt(row.cost),
					"coverage": "Warranty" if cint(row.warranty_claimable) else "Chargeable",
					"serial_no": row.serial_no,
				},
			)
		if flt(ro.vendor_cost):
			self.vendor_cost = flt(self.vendor_cost) + flt(ro.vendor_cost)
			self.append(
				"misc_charges",
				{
					"charge_type": "Other",
					"description": f"Vendor repair {ro.name}",
					"amount": flt(ro.vendor_cost),
					"coverage": "Chargeable",
				},
			)

	def _populate_from_visit_fallback(self):
		if self.labour_charges or not self.service_request:
			return
		visit = frappe.db.get_value(
			"Engineer Visit",
			{"service_request": self.service_request, "docstatus": ["<", 2]},
			"name",
			order_by="modified desc",
		)
		if not visit:
			return
		v = frappe.get_doc("Engineer Visit", visit)
		for log in v.labour_logs or []:
			self.append(
				"labour_charges",
				{
					"activity": log.activity or "Visit Labour",
					"engineer": log.engineer,
					"hours": flt(log.hours) or 1,
					"hourly_rate": DEFAULT_LABOUR_RATE,
				},
			)
		if flt(v.travel_distance) and not self.travel_charges:
			self.append(
				"travel_charges",
				{
					"description": "Field travel",
					"distance_km": flt(v.travel_distance),
					"rate": DEFAULT_TRAVEL_RATE,
				},
			)

	# —— workflow ——

	def start_commercial_review(self):
		self._recalc_totals()
		self.status = "Commercial Review"
		self._append_timeline(_("Commercial review started"))
		self.save(ignore_permissions=True)
		return self

	def request_customer_approval(self):
		if not cint(self.customer_invoice_required) or flt(self.invoice_amount) <= 0:
			return self.approve_billing()
		self.customer_approval = "Pending"
		self.status = "Customer Approval"
		self._append_timeline(_("Awaiting customer approval"))
		self.save(ignore_permissions=True)
		return self

	def approve_billing(self, method=None, remarks=None):
		self.customer_approval = "Approved" if cint(self.customer_invoice_required) else "Not Required"
		self.customer_approved_on = now_datetime()
		if method:
			self.approval_method = method
		if remarks:
			self.approval_remarks = remarks
		self.status = "Approved"
		self._append_timeline(_("Billing approved"))
		self.save(ignore_permissions=True)
		return self

	def mark_warranty_settlement(self):
		self.customer_invoice_required = 0
		self.invoice_amount = 0
		self.status = "Warranty Settlement"
		self._append_timeline(_("Warranty / covered settlement — no customer invoice"))
		self.save(ignore_permissions=True)
		return self

	def generate_sales_invoice(self):
		"""Create + submit ERPNext Sales Invoice → Customer receivable + income GL."""
		from swiftservice.erpnext_integration import (
			auto_submit_invoice,
			default_cost_center,
			default_income_account,
			submit_sales_invoice,
		)

		if self.sales_invoice and frappe.db.exists("Sales Invoice", self.sales_invoice):
			return self.sales_invoice

		if not cint(self.customer_invoice_required) or flt(self.invoice_amount) <= 0:
			return self.mark_warranty_settlement()

		if self.customer_approval not in ("Approved", "Not Required"):
			frappe.throw(_("Customer approval is required before invoice generation"))

		if not self.customer:
			frappe.throw(_("Customer is required for invoicing"))

		if self.service_request:
			sr_status = frappe.db.get_value("Swift Service Request", self.service_request, "status")
			if sr_status in ("Closed",):
				frappe.throw(_("Cannot bill a closed Service Request — reopen first"))

		company = self.company or frappe.defaults.get_user_default("Company")
		cost_center = default_cost_center(company)

		si = frappe.new_doc("Sales Invoice")
		si.customer = self.customer
		si.company = company
		si.due_date = nowdate()
		si.posting_date = nowdate()
		si.currency = self.currency
		si.update_stock = 0  # stock already posted via Spare Request Material Issue
		if self.taxes_and_charges:
			si.taxes_and_charges = self.taxes_and_charges
		si.remarks = _("From Service Billing {0}").format(self.name)

		def _service_item():
			for candidate in ("Service Charges", "Servicing", "Labour Charges"):
				if frappe.db.exists("Item", candidate):
					return candidate
			return frappe.db.get_value("Item", {"is_sales_item": 1, "disabled": 0}, "name")

		def _append_line(item_code, qty, rate, description=None, item_name=None, discount=0):
			if not item_code:
				frappe.throw(_("No sales Item configured for service billing lines"))
			income = default_income_account(company, item_code)
			row = {
				"item_code": item_code,
				"qty": flt(qty) or 1,
				"rate": flt(rate),
				"description": description or item_name or item_code,
			}
			if item_name:
				row["item_name"] = item_name
			if flt(discount):
				row["discount_amount"] = flt(discount)
			if income:
				row["income_account"] = income
			if cost_center:
				row["cost_center"] = cost_center
			si.append("items", row)

		for row in self.labour_charges or []:
			if not self._line_billable(row.coverage) or flt(row.amount) <= 0:
				continue
			_append_line(
				_service_item(),
				flt(row.hours) or 1,
				flt(row.hourly_rate) if flt(row.hours) else flt(row.amount),
				description=row.activity or "Service Labour",
				item_name=row.activity or "Labour",
			)

		for row in self.spare_charges or []:
			if not self._line_billable(row.coverage) or flt(row.amount) <= 0:
				continue
			item = row.item_code if row.item_code and frappe.db.exists("Item", row.item_code) else _service_item()
			_append_line(
				item,
				flt(row.qty) or 1,
				flt(row.rate),
				description=frappe.db.get_value("Item", item, "item_name") or item,
				discount=flt(row.discount),
			)

		for row in self.travel_charges or []:
			if not self._line_billable(row.coverage) or flt(row.amount) <= 0:
				continue
			_append_line(
				_service_item(),
				1,
				flt(row.amount),
				description=row.description or "Travel",
				item_name="Travel Charges",
			)

		for row in self.misc_charges or []:
			if not self._line_billable(row.coverage) or flt(row.amount) <= 0:
				continue
			_append_line(
				_service_item(),
				1,
				flt(row.amount),
				description=row.description or row.charge_type,
				item_name=row.charge_type or "Misc",
			)

		if not si.items:
			_append_line(
				_service_item(),
				1,
				flt(self.invoice_amount),
				description=_("Service Billing {0}").format(self.name),
			)

		if flt(self.discount_total):
			si.discount_amount = flt(self.discount_total)

		if self.tax_rows:
			for tr in self.tax_rows:
				tax_row = {
					"charge_type": "On Net Total" if flt(tr.rate) else "Actual",
					"description": tr.description or getattr(tr, "tax_type", None) or "Tax",
					"rate": flt(tr.rate),
					"tax_amount": flt(tr.amount),
				}
				if tr.account_head and frappe.db.exists("Account", tr.account_head):
					tax_row["account_head"] = tr.account_head
				si.append("taxes", tax_row)

		si.flags.ignore_permissions = True
		si.contact_person = None
		si.customer_address = None
		si.shipping_address_name = None

		prev_import = getattr(frappe.flags, "in_import", False)
		try:
			frappe.flags.in_import = True
			si.insert(ignore_permissions=True)
			frappe.flags.in_import = prev_import
			if auto_submit_invoice():
				submit_sales_invoice(si)
		except Exception:
			frappe.flags.in_import = prev_import
			frappe.log_error(title="Service Billing Sales Invoice failed")
			frappe.throw(
				_("Could not create Sales Invoice. Check Item, Income Account, and Customer setup in ERPNext.")
			)

		self.sales_invoice = si.name
		self.status = "Invoice Generated"
		self._append_timeline(
			_("Sales Invoice {0} {1} — receivable / income ledger posted").format(
				si.name, _("submitted") if si.docstatus == 1 else _("draft")
			)
		)
		self.save(ignore_permissions=True)

		try:
			est = frappe.db.get_value(
				"Service Estimate", {"service_request": self.service_request, "docstatus": ["<", 2]}, "name"
			)
			if est:
				frappe.db.set_value(
					"Service Estimate",
					est,
					{"sales_invoice": si.name, "status": "Invoiced", "total_amount": self.invoice_amount},
				)
		except Exception:
			pass

		return si.name

	def record_payment(self, amount, mode="UPI", reference=None, payment_date=None):
		"""Record payment on billing + create ERPNext Payment Entry against Sales Invoice."""
		from swiftservice.erpnext_integration import create_payment_entry_for_invoice

		amt = flt(amount)
		if amt <= 0:
			frappe.throw(_("Payment amount must be positive"))

		pe_name = None
		if self.sales_invoice and frappe.db.exists("Sales Invoice", self.sales_invoice):
			si_status = frappe.db.get_value("Sales Invoice", self.sales_invoice, "docstatus")
			if cint(si_status) == 1:
				mop = mode
				if mode and not frappe.db.exists("Mode of Payment", mode):
					for candidate in (mode, "Cash", "UPI", "Bank Draft", "Wire Transfer"):
						if frappe.db.exists("Mode of Payment", candidate):
							mop = candidate
							break
					else:
						mop = None
				try:
					pe = create_payment_entry_for_invoice(
						self.sales_invoice,
						amt,
						mode_of_payment=mop,
						reference=reference,
						posting_date=payment_date or nowdate(),
					)
					pe_name = pe.name
				except Exception:
					frappe.log_error(title="Service Billing Payment Entry failed")

		pay = {
			"payment_date": payment_date or nowdate(),
			"mode": mode or "UPI",
			"amount": amt,
			"reference": reference,
		}
		# payment_entry child field if exists
		meta = frappe.get_meta("Bill Payment")
		if meta.has_field("payment_entry"):
			pay["payment_entry"] = pe_name
		self.append("payments", pay)
		self._recalc_totals()
		if flt(self.outstanding_amount) <= 0.01:
			self.status = "Payment Received"
			self._append_timeline(
				_("Payment received in full{0}").format(_(" via {0}").format(pe_name) if pe_name else "")
			)
		else:
			self.status = "Payment Pending"
			self._append_timeline(
				_("Partial payment {0}{1}").format(amt, f" ({pe_name})" if pe_name else "")
			)
		self.save(ignore_permissions=True)
		self._sync_service_request_payment()
		return self

	def close_billing(self):
		if cint(self.customer_invoice_required) and self.status not in (
			"Payment Received",
			"Invoice Generated",
			"Warranty Settlement",
			"Closed",
		):
			if flt(self.outstanding_amount) > 0.01 and self.status != "Invoice Generated":
				frappe.throw(_("Clear outstanding payments before closing"))
		self.status = "Closed"
		self._append_timeline(_("Commercial settlement closed"))
		self.save(ignore_permissions=True)
		self._maybe_request_feedback()
		return self

	def _maybe_request_feedback(self):
		try:
			from swiftservice.swiftservice.doctype.customer_feedback.customer_feedback import (
				generate_from_source,
			)

			generate_from_source(
				service_request=self.service_request,
				service_report=self.service_report,
				service_billing=self.name,
				repair_order=self.repair_order,
			)
		except Exception:
			frappe.log_error(title="Auto Customer Feedback create failed")

	def create_credit_note(self, amount=None, reason=None):
		if not self.sales_invoice:
			frappe.throw(_("Sales Invoice required before credit note"))
		amt = flt(amount) if amount is not None else flt(self.invoice_amount)
		if amt > flt(self.invoice_amount) + 0.01:
			frappe.throw(_("Credit note cannot exceed original invoice amount"))
		# create return invoice if possible
		try:
			from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

			cn = make_sales_return(self.sales_invoice)
			if amt and flt(cn.grand_total) and abs(flt(cn.grand_total)) > amt:
				# scale not trivial — leave full return; store link
				pass
			cn.insert(ignore_permissions=True)
			self.credit_note = cn.name
			self._append_timeline(_("Credit note {0} created").format(cn.name), reason or "")
			self.save(ignore_permissions=True)
			return cn.name
		except Exception:
			# fallback stub link field only
			self._append_timeline(_("Credit note requested"), reason or str(amt))
			self.save(ignore_permissions=True)
			frappe.log_error(title="Service Billing credit note failed")
			return None

	def advance_status(self, status=None):
		if status:
			helpers = {
				"Commercial Review": self.start_commercial_review,
				"Customer Approval": self.request_customer_approval,
				"Approved": self.approve_billing,
				"Invoice Generated": self.generate_sales_invoice,
				"Warranty Settlement": self.mark_warranty_settlement,
				"Payment Received": lambda: self.record_payment(self.outstanding_amount or self.invoice_amount),
				"Closed": self.close_billing,
			}
			fn = helpers.get(status)
			if fn:
				return fn()
			self._assert_transition(self.status, status)
			self.status = status
			self._append_timeline(_("Status → {0}").format(status))
			self.save(ignore_permissions=True)
			return self

		cur = self.status
		# smart path for fully covered
		if cur == "Draft" and not cint(self.customer_invoice_required):
			self.start_commercial_review()
			return self.mark_warranty_settlement()

		if cur not in STATUS_ORDER:
			cur = "Draft"
		idx = STATUS_ORDER.index(cur)
		while idx < len(STATUS_ORDER) - 1:
			nxt = STATUS_ORDER[idx + 1]
			if nxt == "Customer Approval" and (
				not cint(self.customer_invoice_required) or self.customer_approval in ("Approved", "Not Required")
			):
				idx += 1
				continue
			if nxt == "Payment Pending" and flt(self.invoice_amount) <= 0:
				idx += 1
				continue
			if nxt == "Payment Received" and flt(self.invoice_amount) <= 0:
				idx += 1
				continue
			return self.advance_status(nxt)
		return self

	def _sync_service_request_payment(self):
		if not self.service_request:
			return
		try:
			sr = frappe.get_doc("Swift Service Request", self.service_request)
			if sr.docstatus != 1:
				return
			# do not force Closed — leave Feedback / Closure modules to finish
			if flt(self.outstanding_amount) <= 0.01 and sr.status not in ("Closed", "Cancelled", "Completed"):
				# soft signal only
				pass
		except Exception:
			pass


def generate_from_source(
	service_request=None,
	service_report=None,
	repair_order=None,
	replacement_case=None,
	force=False,
):
	if not service_request and service_report:
		service_request = frappe.db.get_value("Service Report", service_report, "service_request")
	if not service_request and repair_order:
		service_request = frappe.db.get_value("Repair Order", repair_order, "service_request")
	if not service_request:
		frappe.throw(_("service_request is required"))

	if service_report and not force:
		existing = frappe.db.get_value(
			"Service Billing",
			{
				"service_report": service_report,
				"docstatus": ["<", 2],
				"status": ["not in", ["Cancelled", "Closed"]],
			},
			"name",
		)
		if existing:
			return frappe.get_doc("Service Billing", existing)

	# prefer billing-ready report
	if not service_report:
		service_report = frappe.db.get_value(
			"Service Report",
			{
				"service_request": service_request,
				"status": ["in", ["Billing Ready", "Submitted", "Customer Signed", "Manager Verification"]],
				"docstatus": ["<", 2],
			},
			"name",
			order_by="modified desc",
		)

	doc = frappe.get_doc(
		{
			"doctype": "Service Billing",
			"naming_series": "BILL-.YYYY.-.#####",
			"service_request": service_request,
			"service_report": service_report,
			"repair_order": repair_order,
			"replacement_case": replacement_case,
			"status": "Draft",
			"billing_date": nowdate(),
		}
	)
	doc.populate_from_sources()
	doc.insert(ignore_permissions=True)
	doc.start_commercial_review()
	return doc
