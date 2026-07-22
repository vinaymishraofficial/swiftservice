import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, now_datetime, nowdate, time_diff_in_hours


STATUS_ALIASES = {
	"Approved": "Billing Ready",
	"Closed": "Submitted",
}

ALLOWED_TRANSITIONS = {
	"Draft": {"Generated", "Cancelled"},
	"Generated": {"Engineer Review", "Draft", "Cancelled"},
	"Engineer Review": {"Customer Review", "Generated", "Cancelled"},
	"Customer Review": {"Customer Signed", "Engineer Review", "Cancelled"},
	"Customer Signed": {"Manager Verification", "Billing Ready", "Customer Review", "Cancelled"},
	"Manager Verification": {"Billing Ready", "Customer Signed", "Cancelled"},
	"Billing Ready": {"Submitted", "Manager Verification", "Cancelled"},
	"Submitted": set(),
	"Cancelled": set(),
	# legacy
	"Approved": {"Submitted", "Billing Ready"},
	"Closed": set(),
}

STATUS_ORDER = [
	"Draft",
	"Generated",
	"Engineer Review",
	"Customer Review",
	"Customer Signed",
	"Manager Verification",
	"Billing Ready",
	"Submitted",
]

TERMINAL = {"Submitted", "Cancelled", "Closed"}


class ServiceReport(Document):
	def validate(self):
		self._set_defaults()
		self._calc_charges()
		self._calc_hours_from_logs()
		if self.status in TERMINAL and self.has_value_changed("status") is False:
			# allow timeline appends only once submitted via helper
			pass

	def before_submit(self):
		self._validate_before_final_submit()
		if self.status not in ("Billing Ready", "Submitted", "Approved"):
			self.status = "Submitted"

	def on_submit(self):
		self.status = "Submitted"
		self._append_timeline(_("Service Report submitted — immutable record"))
		self.db_set("status", "Submitted", update_modified=False)

	def on_cancel(self):
		self.status = "Cancelled"

	def on_update_after_submit(self):
		if self.has_value_changed("status"):
			old = self.get_doc_before_save()
			if old:
				self._assert_transition(old.status, self.status)

	def _set_defaults(self):
		if not self.naming_series:
			self.naming_series = "SRPT-.YYYY.-.#####"
		if not self.status:
			self.status = "Draft"
		if not self.report_date:
			self.report_date = nowdate()
		if not self.revision:
			self.revision = 1
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)

	def _calc_charges(self):
		self.total_charges = (
			flt(self.labour_amount)
			+ flt(self.travel_amount)
			+ flt(self.spare_amount)
			+ flt(self.misc_amount)
			+ flt(self.tax_amount)
		)

	def _calc_hours_from_logs(self):
		if self.time_logs and not self.total_hours:
			self.total_hours = sum(flt(r.hours) for r in self.time_logs)

	def _assert_transition(self, old_status, new_status):
		if old_status == new_status:
			return
		allowed = ALLOWED_TRANSITIONS.get(old_status) or set()
		if new_status not in allowed and "System Manager" not in frappe.get_roles():
			frappe.throw(_("Cannot change report status from {0} to {1}").format(old_status, new_status))

	def _append_timeline(self, activity, remarks=""):
		self.append(
			"report_timeline",
			{
				"activity": activity,
				"user": frappe.session.user,
				"time": now_datetime(),
				"remarks": remarks,
			},
		)

	def _validate_work(self):
		if not (self.work_done or "").strip() and not self.work_activities:
			frappe.throw(_("Work performed cannot be blank"))

	def _validate_signature(self):
		if cint(self.signature_refused):
			if not (self.refusal_reason or "").strip():
				frappe.throw(_("Refusal reason is required when customer declines to sign"))
			return
		if not self.customer_signature and not cint(self.customer_verification):
			frappe.throw(_("Customer signature or verification is required (or record refusal)"))

	def _validate_before_final_submit(self):
		self._validate_work()
		self._validate_signature()
		if self.status not in ("Billing Ready", "Submitted", "Approved", "Manager Verification", "Customer Signed"):
			# allow submit from Billing Ready primarily
			pass

	def _require_visit_completed(self):
		# Workshop / replacement reports may not have a field visit
		if self.repair_order or self.replacement_case:
			return
		if not self.engineer_visit:
			frappe.throw(_("At least one completed Service Visit is required"))
		vstatus = frappe.db.get_value("Engineer Visit", self.engineer_visit, "status")
		vdocstatus = frappe.db.get_value("Engineer Visit", self.engineer_visit, "docstatus")
		if cint(vdocstatus) == 1:
			return
		if vstatus in ("Completed", "GPS Check-Out", "Customer Verification"):
			return
		frappe.throw(_("Service Visit must be completed before generating Service Report"))

	# —— workflow ——

	def mark_generated(self):
		self._require_visit_completed()
		self._validate_work()
		self.status = "Generated"
		self._append_timeline(_("Report generated from linked documents"))
		self.save(ignore_permissions=True)
		return self

	def engineer_review(self):
		self.engineer_declaration = 1
		if not self.engineer_signed_on:
			self.engineer_signed_on = now_datetime()
		self.status = "Engineer Review"
		self._append_timeline(_("Engineer reviewed and certified"))
		self.save(ignore_permissions=True)
		return self

	def send_for_customer_review(self):
		self.status = "Customer Review"
		self._append_timeline(_("Sent for customer review"))
		self.save(ignore_permissions=True)
		return self

	def capture_customer_signature(self, signature=None, refused=0, refusal_reason=None, contact_name=None):
		if cint(refused):
			self.signature_refused = 1
			self.refusal_reason = refusal_reason or self.refusal_reason
			if not (self.refusal_reason or "").strip():
				frappe.throw(_("Refusal reason is required"))
		else:
			if signature:
				self.customer_signature = signature
			self.customer_verification = 1
			self.customer_signed_on = now_datetime()
			if contact_name:
				self.customer_contact_name = contact_name
		self._validate_signature()
		self.status = "Customer Signed"
		self._append_timeline(_("Customer signed") if not cint(refused) else _("Customer refused signature"))
		self.save(ignore_permissions=True)
		return self

	def manager_verify(self, remarks=None):
		self.verified_by = frappe.session.user
		self.verified_on = now_datetime()
		if remarks:
			self.manager_remarks = remarks
		self.status = "Manager Verification"
		self._append_timeline(_("Manager verified"))
		self.save(ignore_permissions=True)
		return self

	def mark_billing_ready(self):
		if self.status not in ("Customer Signed", "Manager Verification", "Billing Ready", "Approved"):
			frappe.throw(_("Customer signature and/or manager verification required before billing"))
		if not cint(self.signature_refused):
			self._validate_signature()
		self.status = "Billing Ready"
		self._append_timeline(_("Billing enabled"))
		self.save(ignore_permissions=True)
		self._maybe_create_billing()
		return self

	def _maybe_create_billing(self):
		try:
			from swiftservice.swiftservice.doctype.service_billing.service_billing import generate_from_source

			generate_from_source(
				service_request=self.service_request,
				service_report=self.name,
				repair_order=self.repair_order,
			)
		except Exception:
			frappe.log_error(title="Auto Service Billing create failed")

	def finalize(self):
		self.mark_billing_ready()
		if self.docstatus == 0:
			self.submit()
		return self

	def create_revision(self):
		"""Immutable original — create Revision N+1 snapshot."""
		if self.docstatus != 1 and self.status != "Submitted":
			frappe.throw(_("Only submitted reports can be revised"))
		new = frappe.copy_doc(self)
		new.naming_series = self.naming_series or "SRPT-.YYYY.-.#####"
		new.revised_from = self.name
		new.revision = cint(self.revision) + 1
		new.status = "Draft"
		new.amended_from = None
		new.verified_by = None
		new.verified_on = None
		new.customer_signed_on = None
		new.report_timeline = []
		new.insert(ignore_permissions=True)
		new._append_timeline(_("Revision {0} created from {1}").format(new.revision, self.name))
		new.save(ignore_permissions=True)
		return new

	def advance_status(self, status=None):
		cur = STATUS_ALIASES.get(self.status, self.status)
		if status:
			status = STATUS_ALIASES.get(status, status)
			helpers = {
				"Generated": self.mark_generated,
				"Engineer Review": self.engineer_review,
				"Customer Review": self.send_for_customer_review,
				"Customer Signed": lambda: self.capture_customer_signature(
					signature=self.customer_signature,
					refused=self.signature_refused,
					refusal_reason=self.refusal_reason,
				),
				"Manager Verification": self.manager_verify,
				"Billing Ready": self.mark_billing_ready,
				"Submitted": self.finalize,
			}
			fn = helpers.get(status)
			if fn:
				return fn()
			self._assert_transition(self.status, status)
			self.status = status
			self._append_timeline(_("Status → {0}").format(status))
			self.save(ignore_permissions=True)
			return self

		if cur not in STATUS_ORDER:
			cur = "Draft"
		idx = STATUS_ORDER.index(cur)
		if idx < len(STATUS_ORDER) - 1:
			return self.advance_status(STATUS_ORDER[idx + 1])
		return self

	def populate_from_sources(self):
		"""Pull snapshot data from Visit / Diagnosis / Spare / Repair."""
		self._populate_from_visit()
		self._populate_from_service_request()
		self._populate_from_diagnosis()
		self._populate_spares()
		self._populate_from_repair()
		self._calc_charges()
		self._calc_hours_from_logs()
		return self

	def _populate_from_service_request(self):
		if not self.service_request or not frappe.db.exists("Swift Service Request", self.service_request):
			return
		sr = frappe.db.get_value(
			"Swift Service Request",
			self.service_request,
			[
				"customer",
				"contact_person",
				"mobile_no",
				"email_id",
				"installed_base",
				"item_code",
				"model_no",
				"serial_no",
				"company",
				"branch",
				"priority",
				"subject",
			],
			as_dict=True,
		)
		if not sr:
			return
		for src, dst in (
			("customer", "customer"),
			("contact_person", "contact_person"),
			("mobile_no", "mobile_no"),
			("email_id", "email_id"),
			("installed_base", "installed_base"),
			("item_code", "item_code"),
			("model_no", "model_no"),
			("serial_no", "serial_no"),
			("company", "company"),
			("branch", "branch"),
			("priority", "priority"),
		):
			if not self.get(dst) and sr.get(src):
				self.set(dst, sr.get(src))
		if not self.complaint and sr.get("subject"):
			self.complaint = sr.subject
		if self.customer and not self.customer_name:
			self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")

	def _populate_from_visit(self):
		if not self.engineer_visit or not frappe.db.exists("Engineer Visit", self.engineer_visit):
			return
		v = frappe.get_doc("Engineer Visit", self.engineer_visit)
		if not self.service_request:
			self.service_request = v.service_request
		if not self.engineer_assignment:
			ea = v.engineer_assignment
			if ea and frappe.db.get_value("Engineer Assignment", ea, "docstatus") != 2:
				self.engineer_assignment = ea
		for src, dst in (
			("engineer", "primary_engineer"),
			("visit_date", "visit_date"),
			("check_in_time", "start_time"),
			("check_out_time", "end_time"),
			("customer", "customer"),
			("contact_person", "contact_person"),
			("mobile_no", "mobile_no"),
			("email_id", "email_id"),
			("site_address", "site_address"),
			("installed_base", "installed_base"),
			("item_code", "item_code"),
			("model_no", "model_no"),
			("serial_no", "serial_no"),
			("company", "company"),
			("branch", "branch"),
			("error_code", "error_code"),
			("root_cause", "root_cause"),
			("failure_category", "failure_category"),
			("observation", "observation"),
			("running_hours", "running_hours"),
			("temperature", "temperature"),
			("voltage", "voltage"),
			("pressure", "pressure"),
			("cycle_count", "cycle_count"),
			("customer_contact_name", "customer_contact_name"),
			("customer_designation", "customer_designation"),
			("customer_signature", "customer_signature"),
		):
			if not self.get(dst) and v.get(src):
				self.set(dst, v.get(src))
		if not self.work_done:
			self.work_done = v.get("work_done") or v.get("observation") or v.get("diagnosis_notes")
		if not self.recommendation and v.get("suggestions"):
			self.recommendation = v.suggestions
			self.append("recommendations", {"recommendation": v.suggestions, "priority": "Medium"})

		if self.start_time and self.end_time and not self.total_hours:
			try:
				self.total_hours = flt(time_diff_in_hours(self.end_time, self.start_time), 2)
			except Exception:
				pass

		if not self.work_activities and self.work_done:
			self.append(
				"work_activities",
				{
					"activity": (self.work_done or "")[:140],
					"engineer": self.primary_engineer,
					"hours": self.total_hours or 0,
					"status": "Completed",
				},
			)

		# checklist
		if not self.checklist_items:
			for row in v.get("checklist_items") or []:
				result = row.get("result") or "Pass"
				if result == "N/A":
					result = "NA"
				self.append(
					"checklist_items",
					{
						"checklist_type": "Inspection",
						"item": row.get("activity") or "Checklist item",
						"result": result if result in ("Pass", "Fail", "NA", "Pending") else "Pass",
						"remarks": row.get("remark") or row.get("remarks"),
					},
				)

		# photos
		stage_map = {
			"Before Repair": "Before Service",
			"During Repair": "During Service",
			"After Repair": "After Service",
			"Other": "Other",
		}
		if not self.photos:
			for row in v.get("photos") or []:
				img = row.get("image") or row.get("photo")
				if not img:
					continue
				stage = row.get("stage") or "During Repair"
				self.append(
					"photos",
					{
						"image": img,
						"category": stage_map.get(stage, "During Service"),
						"caption": row.get("caption") or row.get("remarks"),
					},
				)

		# labour → time logs
		if not self.time_logs:
			for row in v.get("labour_logs") or []:
				self.append(
					"time_logs",
					{
						"engineer": row.get("engineer") or self.primary_engineer,
						"activity": row.get("activity") or row.get("work_type") or "Labour",
						"start_time": row.get("start_time"),
						"end_time": row.get("end_time"),
						"hours": flt(row.get("hours") or row.get("duration")),
						"remarks": row.get("remarks"),
					},
				)
			if not self.time_logs and (self.start_time or self.end_time):
				self.append(
					"time_logs",
					{
						"engineer": self.primary_engineer,
						"activity": "Service Visit",
						"start_time": self.start_time,
						"end_time": self.end_time,
						"hours": self.total_hours or 0,
					},
				)

		# visit spare used
		for row in v.get("spare_used") or []:
			if not row.get("item_code"):
				continue
			exists = any(s.item_code == row.item_code for s in (self.spare_used or []))
			if exists:
				continue
			self.append(
				"spare_used",
				{
					"item_code": row.item_code,
					"qty": flt(row.get("qty") or 1),
					"serial_no": row.get("serial_no"),
					"batch_no": row.get("batch_no"),
					"cost": flt(row.get("cost")),
				},
			)

		if v.get("customer_signature"):
			self.customer_verification = 1

	def _populate_from_diagnosis(self):
		filters = {"docstatus": ["<", 2]}
		if self.engineer_visit:
			filters["engineer_visit"] = self.engineer_visit
		elif self.service_request:
			filters["service_request"] = self.service_request
		else:
			return
		name = frappe.db.get_value("Failure Analysis", filters, "name", order_by="modified desc")
		if not name:
			return
		d = frappe.db.get_value(
			"Failure Analysis",
			name,
			[
				"root_cause",
				"failure_category",
				"failure_sub_category",
				"root_cause_category",
				"observation",
				"serial_no",
				"item_code",
				"error_code",
				"downtime_hours",
				"recommendation",
				"firmware",
				"software",
			],
			as_dict=True,
		)
		if not d:
			return
		for src, dst in (
			("root_cause", "root_cause"),
			("failure_category", "failure_category"),
			("observation", "observation"),
			("serial_no", "serial_no"),
			("item_code", "item_code"),
			("error_code", "error_code"),
			("downtime_hours", "downtime_hours"),
			("firmware", "firmware_version"),
			("software", "software_version"),
		):
			if not self.get(dst) and d.get(src):
				self.set(dst, d.get(src))
		if not self.failure_mode:
			self.failure_mode = d.get("failure_sub_category") or d.get("root_cause_category")
		if d.get("recommendation") and not self.recommendation:
			self.recommendation = d.recommendation
			self.append("recommendations", {"recommendation": d.recommendation, "priority": "Medium"})

	def _populate_spares(self):
		if not self.service_request:
			return
		sprs = frappe.get_all(
			"Spare Request",
			filters={"service_request": self.service_request, "docstatus": ["<", 2]},
			pluck="name",
		)
		for spr_name in sprs:
			spr = frappe.get_doc("Spare Request", spr_name)
			rows = spr.get("consumed_items") or []
			if not rows:
				rows = [
					r
					for r in (spr.get("requested_items") or [])
					if flt(r.get("consumed_qty") or r.get("issued_qty")) > 0
				]
			for row in rows:
				item = row.get("item_code")
				if not item:
					continue
				qty = flt(row.get("qty_used") or row.get("consumed_qty") or row.get("issued_qty") or row.get("qty") or 1)
				exists = any(
					s.item_code == item and s.spare_request == spr_name for s in (self.spare_used or [])
				)
				if exists:
					continue
				self.append(
					"spare_used",
					{
						"item_code": item,
						"qty": qty,
						"serial_no": row.get("serial_no"),
						"batch_no": row.get("batch_no"),
						"chargeable": cint(row.get("chargeable")),
						"warranty_claimable": cint(row.get("warranty_claimable")),
						"spare_request": spr_name,
						"cost": flt(row.get("actual_cost") or row.get("cost")),
					},
				)
			self.spare_amount = flt(self.spare_amount) + sum(
				flt(r.get("actual_cost") or r.get("cost") or 0) for r in rows
			)

		# legacy text
		if self.spare_used and not self.parts_used:
			self.parts_used = ", ".join(f"{r.item_code} x {flt(r.qty)}" for r in self.spare_used)

	def _populate_from_repair(self):
		if not self.repair_order:
			name = None
			if self.service_request:
				name = frappe.db.get_value(
					"Repair Order",
					{"service_request": self.service_request, "docstatus": ["<", 2]},
					"name",
					order_by="modified desc",
				)
			if name:
				self.repair_order = name
		if not self.repair_order or not frappe.db.exists("Repair Order", self.repair_order):
			return
		ro = frappe.get_doc("Repair Order", self.repair_order)
		if not self.work_done and ro.get("work_done"):
			self.work_done = ro.work_done
		for op in ro.get("repair_operations") or []:
			self.append(
				"work_activities",
				{
					"activity": op.get("operation") or "Repair",
					"engineer": op.get("technician") or self.primary_engineer,
					"hours": 0,
					"status": op.get("status") or "Completed",
				},
			)
		for row in ro.get("spare_used") or []:
			if not row.get("item_code"):
				continue
			exists = any(s.item_code == row.item_code for s in (self.spare_used or []))
			if exists:
				continue
			self.append(
				"spare_used",
				{
					"item_code": row.item_code,
					"qty": flt(row.qty or 1),
					"serial_no": row.get("serial_no"),
					"batch_no": row.get("batch_no"),
					"chargeable": cint(row.get("chargeable")),
					"warranty_claimable": cint(row.get("warranty_claimable")),
					"cost": flt(row.get("cost")),
				},
			)


def generate_from_source(
	service_request=None,
	engineer_visit=None,
	repair_order=None,
	replacement_case=None,
	work_done=None,
	force=False,
):
	"""Create Service Report snapshot. Manual blank create is discouraged — use this."""
	if not service_request and engineer_visit:
		service_request = frappe.db.get_value("Engineer Visit", engineer_visit, "service_request")
	if not service_request and repair_order:
		service_request = frappe.db.get_value("Repair Order", repair_order, "service_request")
	if not service_request:
		frappe.throw(_("service_request is required"))

	if engineer_visit and not force:
		existing = frappe.db.get_value(
			"Service Report",
			{
				"engineer_visit": engineer_visit,
				"docstatus": ["<", 2],
				"status": ["not in", ["Cancelled"]],
			},
			"name",
		)
		if existing:
			return frappe.get_doc("Service Report", existing)

	# prefer latest completed visit if not provided
	if not engineer_visit:
		engineer_visit = frappe.db.get_value(
			"Engineer Visit",
			{
				"service_request": service_request,
				"status": ["in", ["Completed", "GPS Check-Out", "Customer Verification"]],
				"docstatus": ["<", 2],
			},
			"name",
			order_by="modified desc",
		) or frappe.db.get_value(
			"Engineer Visit",
			{"service_request": service_request, "docstatus": 1},
			"name",
			order_by="modified desc",
		)

	doc = frappe.get_doc(
		{
			"doctype": "Service Report",
			"naming_series": "SRPT-.YYYY.-.#####",
			"service_request": service_request,
			"engineer_visit": engineer_visit,
			"repair_order": repair_order,
			"replacement_case": replacement_case,
			"status": "Draft",
			"revision": 1,
			"report_date": nowdate(),
			"work_done": work_done,
		}
	)
	doc.populate_from_sources()
	if work_done and not doc.work_done:
		doc.work_done = work_done
	doc.insert(ignore_permissions=True)
	try:
		doc.mark_generated()
	except Exception:
		doc._append_timeline(_("Generated in Draft — complete visit / work before advancing"))
		doc.save(ignore_permissions=True)
	return doc
