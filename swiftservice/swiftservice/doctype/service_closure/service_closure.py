import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, now_datetime, nowdate, time_diff_in_hours


TERMINAL_OK = {"Closed", "Completed", "Cancelled", "Consumed", "Submitted", "Archived", "Warranty Settlement", "Payment Received", "Invoice Generated"}
OPEN_BLOCKING = {
	"Spare Request": {"Draft", "Submitted", "Approved", "Reserved", "Issued", "Partially Issued", "In Transit", "Waiting Stock"},
	"Repair Order": {
		"Draft",
		"Awaiting Pickup",
		"Picked Up",
		"Received at Workshop",
		"Initial Inspection",
		"Estimate Pending",
		"Customer Approval",
		"Repair In Progress",
		"Waiting Spare",
		"Repair Completed",
		"Testing",
		"Quality Inspection",
		"Ready for Dispatch",
		"Dispatched",
		"Installed",
	},
	"Replacement Case": {"Draft", "Pending Approval", "Approved", "Dispatched", "In Progress"},
	"Service Report": {"Draft", "Generated", "Engineer Review", "Customer Review", "Customer Signed", "Manager Verification"},
	"Service Billing": {"Draft", "Commercial Review", "Customer Approval", "Approved", "Payment Pending", "Disputed"},
	"Customer Feedback": {"Draft", "Feedback Requested", "Customer Responded", "Escalation"},
}

ALLOWED_TRANSITIONS = {
	"Draft": {"Validation", "Cancelled"},
	"Validation": {"Manager Review", "Validation Failed", "Draft", "Cancelled"},
	"Validation Failed": {"Validation", "Draft", "Cancelled"},
	"Manager Review": {"Approved", "Validation Failed", "Cancelled"},
	"Approved": {"Closed", "Manager Review", "Cancelled"},
	"Closed": {"Archived", "Reopen Requested"},
	"Archived": {"Reopen Requested"},
	"Reopen Requested": {"Reopened", "Closed", "Archived", "Cancelled"},
	"Reopened": set(),
	"Cancelled": set(),
}

# Feedback optional by default for closure (configurable via flag)
REQUIRE_FEEDBACK = False
REQUIRE_PAYMENT = False
REQUIRE_SIGNATURE = True


class ServiceClosure(Document):
	def validate(self):
		self._set_defaults()
		self._calc_financials()

	def before_submit(self):
		if self.status in (None, "", "Draft", "Validation", "Manager Review", "Approved"):
			if self.status != "Closed":
				self.status = "Approved"

	def on_submit(self):
		self._append_timeline(_("Service Closure submitted"))

	def on_cancel(self):
		self.status = "Cancelled"

	def on_update_after_submit(self):
		if self.has_value_changed("status"):
			old = self.get_doc_before_save()
			if old:
				self._assert_transition(old.status, self.status)

	def _set_defaults(self):
		if not self.naming_series:
			self.naming_series = "SCL-.YYYY.-.#####"
		if not self.status:
			self.status = "Draft"
		if not self.closure_date:
			self.closure_date = nowdate()
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)
		if not self.closure_reason:
			self.closure_reason = "Successfully Resolved"

	def _calc_financials(self):
		self.total_cost = flt(self.labour_cost) + flt(self.material_cost) + flt(self.travel_cost)
		self.gross_margin = flt(self.invoice_value) - flt(self.total_cost)

	def _assert_transition(self, old_status, new_status):
		if old_status == new_status:
			return
		allowed = ALLOWED_TRANSITIONS.get(old_status) or set()
		if new_status not in allowed and "System Manager" not in frappe.get_roles():
			frappe.throw(_("Cannot change closure status from {0} to {1}").format(old_status, new_status))

	def _append_timeline(self, activity, remarks=""):
		self.append(
			"closure_timeline",
			{
				"activity": activity,
				"user": frappe.session.user,
				"time": now_datetime(),
				"remarks": remarks,
			},
		)

	def populate_from_sources(self):
		if not self.service_request:
			return self
		meta = frappe.get_meta("Swift Service Request")
		wanted = [
			"customer",
			"company",
			"branch",
			"installed_base",
			"serial_no",
			"item_code",
			"creation",
			"assignment_date",
			"closed_on",
		]
		fields = [f for f in wanted if f == "creation" or meta.has_field(f)]
		sr = frappe.db.get_value(
			"Swift Service Request",
			self.service_request,
			fields,
			as_dict=True,
		)
		if sr:
			for src, dst in (
				("customer", "customer"),
				("company", "company"),
				("branch", "branch"),
				("installed_base", "installed_base"),
				("serial_no", "serial_no"),
				("item_code", "item_code"),
			):
				if not self.get(dst) and sr.get(src):
					self.set(dst, sr.get(src))
			# SLA soft calc
			try:
				assigned = sr.get("assignment_date")
				if sr.creation and assigned:
					self.response_time_hours = flt(time_diff_in_hours(assigned, sr.creation), 2)
				end = sr.get("closed_on") or now_datetime()
				if sr.creation:
					self.resolution_time_hours = flt(time_diff_in_hours(end, sr.creation), 2)
				# default: met if resolution < 72h (placeholder SLA)
				if self.resolution_time_hours and self.resolution_time_hours <= 72:
					self.sla_met = 1
					self.sla_breach = 0
				elif self.resolution_time_hours:
					self.sla_met = 0
					self.sla_breach = 1
			except Exception:
				pass

		if not self.service_report:
			self.service_report = frappe.db.get_value(
				"Service Report",
				{"service_request": self.service_request, "docstatus": ["<", 2]},
				"name",
				order_by="modified desc",
			)
		if not self.service_billing:
			self.service_billing = frappe.db.get_value(
				"Service Billing",
				{"service_request": self.service_request, "docstatus": ["<", 2]},
				"name",
				order_by="modified desc",
			)
		if not self.customer_feedback:
			self.customer_feedback = frappe.db.get_value(
				"Customer Feedback",
				{"service_request": self.service_request, "docstatus": ["<", 2]},
				"name",
				order_by="modified desc",
			)
		if not self.repair_order:
			self.repair_order = frappe.db.get_value(
				"Repair Order",
				{"service_request": self.service_request, "docstatus": ["<", 2]},
				"name",
				order_by="modified desc",
			)
		if not self.replacement_case:
			self.replacement_case = frappe.db.get_value(
				"Replacement Case",
				{"service_request": self.service_request, "docstatus": ["<", 2]},
				"name",
				order_by="modified desc",
			)

		if self.service_billing and frappe.db.exists("Service Billing", self.service_billing):
			b = frappe.db.get_value(
				"Service Billing",
				self.service_billing,
				["labour_cost", "material_cost", "travel_cost", "total_cost", "invoice_amount", "gross_margin"],
				as_dict=True,
			)
			if b:
				self.labour_cost = flt(b.labour_cost)
				self.material_cost = flt(b.material_cost)
				self.travel_cost = flt(b.travel_cost)
				self.total_cost = flt(b.total_cost) or (
					flt(self.labour_cost) + flt(self.material_cost) + flt(self.travel_cost)
				)
				self.invoice_value = flt(b.invoice_amount)
				self.gross_margin = flt(b.gross_margin)
		self._calc_financials()
		return self

	# —— validation engine ——

	def run_validation(self):
		"""Populate checklist + pending issues. Returns True if all blocking checks pass."""
		self.status = "Validation"
		self.checklist = []
		self.pending_issues = []
		self.documents_verified = []
		self.validation_passed = 0

		checks = []
		checks += self._check_operational()
		checks += self._check_inventory()
		checks += self._check_commercial()
		checks += self._check_customer()
		checks += self._check_linked_docs()

		for c in checks:
			self.append("checklist", c)
			if c.get("status") == "Fail" and cint(c.get("blocking", 1)):
				self.append(
					"pending_issues",
					{
						"module": c.get("section"),
						"reference": c.get("remarks") or "",
						"issue": c.get("verification"),
						"blocking": 1,
						"resolved": 0,
					},
				)

		blocking_fails = [c for c in checks if c.get("status") == "Fail" and cint(c.get("blocking", 1))]
		self.validation_passed = 0 if blocking_fails else 1
		if self.validation_passed:
			self.status = "Manager Review"
			self._append_timeline(_("Validation passed — ready for manager review"))
		else:
			self.status = "Validation Failed"
			self._append_timeline(
				_("Validation failed"),
				_("{0} blocking issue(s)").format(len(blocking_fails)),
			)
		self.save(ignore_permissions=True)
		return bool(self.validation_passed)

	def _add_check(self, section, verification, ok, remarks="", blocking=1, na=False):
		if na:
			status = "NA"
		else:
			status = "Pass" if ok else "Fail"
		return {
			"section": section,
			"verification": verification,
			"status": status,
			"blocking": blocking if not na else 0,
			"remarks": remarks or "",
		}

	def _check_operational(self):
		out = []
		ssr = self.service_request
		# visits
		visits = frappe.get_all(
			"Engineer Visit",
			filters={"service_request": ssr, "docstatus": ["<", 2]},
			fields=["name", "status", "docstatus"],
		)
		open_visits = [v for v in visits if v.status not in ("Completed", "Cancelled") and cint(v.docstatus) != 1]
		out.append(
			self._add_check(
				"Operational",
				"Engineer Visit Completed",
				not open_visits and bool(visits),
				remarks=", ".join(v.name for v in open_visits) if open_visits else (visits[0].name if visits else "No visit"),
				blocking=1 if visits else 0,
				na=not visits,
			)
		)

		# service report
		if self.service_report and frappe.db.exists("Service Report", self.service_report):
			r = frappe.db.get_value(
				"Service Report",
				self.service_report,
				["status", "customer_signature", "customer_verification", "signature_refused", "docstatus"],
				as_dict=True,
			)
			ok_status = r.status in ("Billing Ready", "Submitted", "Approved", "Closed") or cint(r.docstatus) == 1
			out.append(self._add_check("Operational", "Service Report Approved", ok_status, remarks=r.status))
			sig_ok = bool(r.customer_signature) or cint(r.customer_verification) or cint(r.signature_refused)
			out.append(
				self._add_check(
					"Operational",
					"Customer Signature",
					sig_ok,
					remarks="Refused" if cint(r.signature_refused) else "",
					blocking=1 if REQUIRE_SIGNATURE else 0,
				)
			)
			self.append(
				"documents_verified",
				{
					"document_type": "Service Report",
					"document_name": self.service_report,
					"doc_status": r.status,
					"verified": 1 if ok_status else 0,
				},
			)
		else:
			out.append(self._add_check("Operational", "Service Report Approved", False, remarks="Missing", blocking=1))

		# repair
		if self.repair_order:
			st = frappe.db.get_value("Repair Order", self.repair_order, "status")
			ok = st in ("Closed", "Cancelled", "Dispatched", "Installed", "Replacement Recommended", "Not Repairable")
			out.append(self._add_check("Operational", "Repair Completed", ok, remarks=f"{self.repair_order}: {st}"))
		else:
			out.append(self._add_check("Operational", "Repair Completed", True, na=True))

		# replacement
		if self.replacement_case:
			meta = frappe.get_meta("Replacement Case")
			st_field = "approval_status" if meta.has_field("approval_status") else "status"
			st = frappe.db.get_value("Replacement Case", self.replacement_case, st_field)
			ok = (st or "") in ("Completed", "Closed", "Cancelled", "Installed", "Approved")
			if st is None:
				out.append(self._add_check("Operational", "Replacement Completed", True, na=True))
			else:
				out.append(
					self._add_check(
						"Operational", "Replacement Completed", ok, remarks=f"{self.replacement_case}: {st}"
					)
				)
		else:
			out.append(self._add_check("Operational", "Replacement Completed", True, na=True))

		return out

	def _check_inventory(self):
		out = []
		open_spr = frappe.get_all(
			"Spare Request",
			filters={
				"service_request": self.service_request,
				"docstatus": ["<", 2],
				"status": ["not in", ["Closed", "Cancelled", "Completed", "Consumed"]],
			},
			pluck="name",
		)
		out.append(
			self._add_check(
				"Inventory",
				"Spare Requests Closed",
				not open_spr,
				remarks=", ".join(open_spr) if open_spr else "OK",
			)
		)
		out.append(self._add_check("Inventory", "Spare Consumption Completed", not open_spr, remarks="Linked to open SPR"))
		return out

	def _check_commercial(self):
		out = []
		if self.service_billing and frappe.db.exists("Service Billing", self.service_billing):
			b = frappe.db.get_value(
				"Service Billing",
				self.service_billing,
				["status", "customer_invoice_required", "outstanding_amount", "sales_invoice"],
				as_dict=True,
			)
			terminal = b.status in (
				"Closed",
				"Payment Received",
				"Warranty Settlement",
				"Invoice Generated",
				"Cancelled",
			)
			out.append(self._add_check("Commercial", "Billing Completed", terminal, remarks=b.status))
			if cint(b.customer_invoice_required):
				out.append(
					self._add_check(
						"Commercial",
						"Sales Invoice Generated",
						bool(b.sales_invoice) or b.status in ("Invoice Generated", "Payment Received", "Closed"),
						remarks=b.sales_invoice or b.status,
						blocking=0,  # site may block SI insert
					)
				)
				pay_ok = flt(b.outstanding_amount) <= 0.01 or b.status in ("Payment Received", "Closed", "Warranty Settlement")
				out.append(
					self._add_check(
						"Commercial",
						"Payment Received",
						pay_ok,
						remarks=str(b.outstanding_amount),
						blocking=1 if REQUIRE_PAYMENT else 0,
					)
				)
			else:
				out.append(self._add_check("Commercial", "Sales Invoice Generated", True, na=True))
				out.append(self._add_check("Commercial", "Payment Received", True, na=True))
			self.append(
				"documents_verified",
				{
					"document_type": "Service Billing",
					"document_name": self.service_billing,
					"doc_status": b.status,
					"verified": 1 if terminal else 0,
				},
			)
		else:
			# no billing — allowed for warranty FOC if no chargeable work
			out.append(self._add_check("Commercial", "Billing Completed", True, remarks="No billing doc", blocking=0))
		return out

	def _check_customer(self):
		out = []
		if self.customer_feedback and frappe.db.exists("Customer Feedback", self.customer_feedback):
			f = frappe.db.get_value(
				"Customer Feedback",
				self.customer_feedback,
				["status", "csat_rating", "nps_score", "escalation_required", "escalation_status"],
				as_dict=True,
			)
			ok = f.status in ("Closed", "Reviewed", "Cancelled")
			out.append(self._add_check("Customer", "Feedback Received", ok, remarks=f.status, blocking=1 if REQUIRE_FEEDBACK else 0))
			out.append(
				self._add_check("Customer", "CSAT Recorded", bool(f.csat_rating), remarks=str(f.csat_rating or ""), blocking=0)
			)
			out.append(
				self._add_check(
					"Customer",
					"NPS Recorded",
					f.nps_score not in (None, ""),
					remarks=str(f.nps_score if f.nps_score is not None else ""),
					blocking=0,
				)
			)
			esc_ok = not cint(f.escalation_required) or f.escalation_status in ("Resolved", "Not Required", None, "")
			out.append(self._add_check("Customer", "Escalation Closed", esc_ok, remarks=f.escalation_status or "N/A"))
			self.append(
				"documents_verified",
				{
					"document_type": "Customer Feedback",
					"document_name": self.customer_feedback,
					"doc_status": f.status,
					"verified": 1 if ok else 0,
				},
			)
		else:
			out.append(
				self._add_check(
					"Customer",
					"Feedback Received",
					not REQUIRE_FEEDBACK,
					remarks="No feedback",
					blocking=1 if REQUIRE_FEEDBACK else 0,
					na=not REQUIRE_FEEDBACK,
				)
			)
		return out

	def _check_linked_docs(self):
		"""Generic open-doc scan."""
		out = []
		for doctype, open_statuses in OPEN_BLOCKING.items():
			if not frappe.db.exists("DocType", doctype):
				continue
			filters = {"service_request": self.service_request, "docstatus": ["<", 2]}
			meta = frappe.get_meta(doctype)
			status_field = "status"
			if doctype == "Replacement Case" and meta.has_field("approval_status"):
				status_field = "approval_status"
			if not meta.has_field(status_field):
				continue
			open_docs = frappe.get_all(doctype, filters=filters, fields=["name", status_field], limit=20)
			blocking = []
			for d in open_docs:
				st = d.get(status_field)
				if st in open_statuses:
					blocking.append(f"{d.name} ({st})")
			# Spare/Repair already covered — still list as inventory/ops summary
			if doctype in ("Spare Request", "Repair Order", "Service Report", "Service Billing", "Customer Feedback"):
				continue
			out.append(
				self._add_check(
					"Documents",
					f"No open {doctype}",
					not blocking,
					remarks=", ".join(blocking[:5]) if blocking else "OK",
					blocking=1 if blocking else 0,
				)
			)
		return out

	# —— workflow ——

	def send_for_manager_review(self):
		if not cint(self.validation_passed):
			self.run_validation()
		if not cint(self.validation_passed):
			frappe.throw(_("Fix pending issues before manager review"))
		self.reviewed_by = frappe.session.user
		self.reviewed_on = now_datetime()
		self.status = "Manager Review"
		self._append_timeline(_("Sent for manager review"))
		self.save(ignore_permissions=True)
		return self

	def approve_closure(self, remarks=None):
		if self.status == "Validation Failed" or not cint(self.validation_passed):
			# re-run
			self.run_validation()
		if not cint(self.validation_passed):
			frappe.throw(_("Cannot approve — validation has blocking failures"))
		self.approved_by = frappe.session.user
		self.approved_on = now_datetime()
		if remarks:
			self.approval_remarks = remarks
		self.status = "Approved"
		self._append_timeline(_("Closure approved"))
		self.save(ignore_permissions=True)
		return self

	def execute_close(self):
		"""Final close — freezes SSR and updates Installed Base."""
		if self.status not in ("Approved", "Closed"):
			if cint(self.validation_passed):
				self.approve_closure()
			else:
				frappe.throw(_("Closure must be Approved before final close"))
		if not self.closure_reason:
			frappe.throw(_("Closure reason is mandatory"))

		self.closed_by = frappe.session.user
		self.closed_on = now_datetime()
		self.status = "Closed"
		self._append_timeline(_("Service lifecycle closed"), self.closure_reason)
		self.save(ignore_permissions=True)

		self._close_service_request()
		self._update_installed_base()
		self._notify_closure()
		return self

	def archive(self):
		if self.status not in ("Closed", "Archived"):
			frappe.throw(_("Close before archiving"))
		self.archived = 1
		self.archived_on = now_datetime()
		self.status = "Archived"
		self._append_timeline(_("Archived — audit record frozen"))
		self.save(ignore_permissions=True)
		return self

	def _close_service_request(self):
		if not self.service_request or not frappe.db.exists("Swift Service Request", self.service_request):
			return
		sr = frappe.get_doc("Swift Service Request", self.service_request)
		if sr.status == "Closed":
			return
		# allow Completed → Closed; also allow from Customer Verification via Completed first
		if sr.status not in ("Completed", "Closed"):
			if sr.status in ("Customer Verification", "Customer Approval", "Testing"):
				sr.status = "Completed"
				sr.flags.ignore_validate_update_after_submit = True
				sr.save(ignore_permissions=True)
		sr.reload()
		sr.flags.ignore_validate_update_after_submit = True
		sr.flags.service_closure_approved = True
		sr.status = "Closed"
		if hasattr(sr, "closure_reason") and self.closure_reason:
			sr.closure_reason = self.closure_reason
		sr.closed_by = self.closed_by
		sr.closed_on = self.closed_on
		sr.save(ignore_permissions=True)

	def _update_installed_base(self):
		if not self.installed_base or not frappe.db.exists("Installed Base", self.installed_base):
			return
		try:
			ib = frappe.get_doc("Installed Base", self.installed_base)
			changed = False
			if hasattr(ib, "last_visit_date"):
				ib.last_visit_date = getdate()
				changed = True
			if self.service_report and frappe.db.exists("Service Report", self.service_report):
				fw = frappe.db.get_value("Service Report", self.service_report, "firmware_version")
				sw = frappe.db.get_value("Service Report", self.service_report, "software_version")
				if fw and hasattr(ib, "firmware_version"):
					ib.firmware_version = fw
					changed = True
				if sw and hasattr(ib, "software_version"):
					ib.software_version = sw
					changed = True
			if changed:
				ib.save(ignore_permissions=True)
				self._append_timeline(_("Installed Base {0} updated").format(self.installed_base))
				self.db_update()
		except Exception:
			frappe.log_error(title="Service Closure Installed Base update failed")

	def _notify_closure(self):
		try:
			email = self.email_id if hasattr(self, "email_id") else None
			if not email and self.customer:
				email = frappe.db.get_value("Customer", self.customer, "email_id")
			if email:
				frappe.sendmail(
					recipients=[email],
					subject=_("Service Request {0} closed").format(self.service_request),
					message=_("Your service request {0} has been closed. Reason: {1}").format(
						self.service_request, self.closure_reason or ""
					),
					delayed=True,
				)
		except Exception:
			pass

	def request_reopen(self, reason=None):
		if self.status not in ("Closed", "Archived"):
			frappe.throw(_("Only closed/archived closures can be reopened"))
		if not reason:
			frappe.throw(_("Reopen reason is mandatory"))
		self.reopen_requested = 1
		self.reopen_reason = reason
		self.status = "Reopen Requested"
		self._append_timeline(_("Reopen requested"), reason)
		self.save(ignore_permissions=True)
		return self

	def approve_reopen(self):
		if self.status != "Reopen Requested":
			frappe.throw(_("No reopen request pending"))
		if not self.reopen_reason:
			frappe.throw(_("Reopen reason is mandatory"))
		self.reopen_approved_by = frappe.session.user
		self.reopen_approved_on = now_datetime()
		self.reopened = 1
		self.status = "Reopened"
		self._append_timeline(_("Reopen approved — Service Request restored to Completed"))
		self.save(ignore_permissions=True)

		sr = frappe.get_doc("Swift Service Request", self.service_request)
		sr.flags.ignore_validate_update_after_submit = True
		sr.flags.service_closure_reopen = True
		# Closed has no outgoing transition — System Manager path / flag
		sr.status = "Completed"
		sr.save(ignore_permissions=True)
		return self

	def advance_status(self, status=None):
		if status:
			helpers = {
				"Validation": self.run_validation,
				"Manager Review": self.send_for_manager_review,
				"Approved": self.approve_closure,
				"Closed": self.execute_close,
				"Archived": self.archive,
			}
			fn = helpers.get(status)
			if fn:
				return fn()
			self._assert_transition(self.status, status)
			self.status = status
			self._append_timeline(_("Status → {0}").format(status))
			self.save(ignore_permissions=True)
			return self
		order = ["Draft", "Validation", "Manager Review", "Approved", "Closed", "Archived"]
		cur = self.status
		if cur == "Validation Failed":
			return self.run_validation()
		if cur not in order:
			cur = "Draft"
		idx = order.index(cur)
		if idx < len(order) - 1:
			return self.advance_status(order[idx + 1])
		return self


def generate_from_source(service_request=None, force=False, run_validation=True):
	"""System-generated governance document — not meant for blank manual create."""
	if not service_request:
		frappe.throw(_("service_request is required"))

	existing = frappe.db.get_value(
		"Service Closure",
		{
			"service_request": service_request,
			"docstatus": ["<", 2],
			"status": ["not in", ["Cancelled", "Reopened"]],
		},
		"name",
	)
	if existing and not force:
		doc = frappe.get_doc("Service Closure", existing)
		if run_validation and doc.status in ("Draft", "Validation Failed", "Validation"):
			doc.populate_from_sources()
			doc.run_validation()
		return doc

	doc = frappe.get_doc(
		{
			"doctype": "Service Closure",
			"naming_series": "SCL-.YYYY.-.#####",
			"service_request": service_request,
			"status": "Draft",
			"closure_date": nowdate(),
			"closure_reason": "Successfully Resolved",
		}
	)
	doc.populate_from_sources()
	doc.insert(ignore_permissions=True)
	if run_validation:
		doc.run_validation()
	else:
		doc._append_timeline(_("Service Closure generated"))
		doc.save(ignore_permissions=True)
	return doc


def assert_can_close_service_request(service_request):
	"""Called before SSR → Closed. Requires Approved/Closed Service Closure."""
	ok = frappe.db.exists(
		"Service Closure",
		{
			"service_request": service_request,
			"docstatus": ["<", 2],
			"status": ["in", ["Approved", "Closed", "Archived"]],
			"validation_passed": 1,
		},
	)
	if not ok and "System Manager" not in frappe.get_roles():
		frappe.throw(
			_(
				"Service Closure governance document required before closing Service Request. "
				"Generate and approve Service Closure first."
			)
		)
	return True
