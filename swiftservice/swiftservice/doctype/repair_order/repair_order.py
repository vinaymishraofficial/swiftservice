import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, now_datetime, nowdate


STATUS_ALIASES = {
	"Open": "Draft",
	"In Process": "Repair In Progress",
	"Completed": "Repair Completed",
}

ALLOWED_TRANSITIONS = {
	"Draft": {"Awaiting Pickup", "Received at Workshop", "Cancelled"},
	"Awaiting Pickup": {"Picked Up", "Draft", "Cancelled"},
	"Picked Up": {"Received at Workshop", "Awaiting Pickup", "Cancelled"},
	"Received at Workshop": {"Initial Inspection", "Cancelled"},
	"Initial Inspection": {
		"Estimate Pending",
		"Customer Approval",
		"Repair In Progress",
		"Not Repairable",
		"Replacement Recommended",
		"Cancelled",
	},
	"Estimate Pending": {"Customer Approval", "Initial Inspection", "Cancelled"},
	"Customer Approval": {"Repair In Progress", "Estimate Pending", "Cancelled"},
	"Repair In Progress": {"Waiting Spare", "Repair Completed", "Cancelled"},
	"Waiting Spare": {"Repair In Progress", "Cancelled"},
	"Repair Completed": {"Testing", "Quality Inspection", "Cancelled"},
	"Testing": {"Quality Inspection", "Repair In Progress", "Cancelled"},
	"Quality Inspection": {"Ready for Dispatch", "Repair In Progress", "Testing", "Cancelled"},
	"Ready for Dispatch": {"Dispatched", "Quality Inspection", "Cancelled"},
	"Dispatched": {"Installed", "Closed"},
	"Installed": {"Closed"},
	"Closed": set(),
	"Cancelled": set(),
	"Not Repairable": {"Replacement Recommended", "Closed", "Cancelled"},
	"Replacement Recommended": {"Closed", "Cancelled"},
	# legacy
	"Open": {"Awaiting Pickup", "Repair In Progress", "Cancelled"},
	"In Process": {"Repair Completed", "Waiting Spare", "Cancelled"},
	"Completed": {"Closed", "Dispatched"},
}

STATUS_ORDER = [
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
	"Closed",
]


class RepairOrder(Document):
	def validate(self):
		self._set_defaults()
		self._fetch_from_links()
		self._calc_estimate()
		self._check_duplicate_serial()

	def before_submit(self):
		if self.status in (None, "", "Draft", "Open"):
			self.status = "Awaiting Pickup" if cint(self.pickup_required) else "Received at Workshop"

	def on_submit(self):
		self._append_timeline(_("Repair Order submitted"))
		self._sync_service_request()

	def on_cancel(self):
		self.status = "Cancelled"

	def on_update_after_submit(self):
		if self.has_value_changed("status"):
			old = self.get_doc_before_save()
			if old:
				self._assert_transition(old.status, self.status)

	def _set_defaults(self):
		if not self.naming_series:
			self.naming_series = "RO-.YYYY.-.#####"
		if not self.status:
			self.status = "Draft"
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)
		if self.repair_type == "Chargeable" and self.customer_approval == "Not Required":
			self.customer_approval = "Pending"
		if self.repair_type in ("Warranty", "AMC", "Internal") and not self.customer_approval:
			self.customer_approval = "Not Required"

	def _fetch_from_links(self):
		if self.service_request and frappe.db.exists("Swift Service Request", self.service_request):
			sr = frappe.db.get_value(
				"Swift Service Request",
				self.service_request,
				[
					"customer",
					"installed_base",
					"item_code",
					"model_no",
					"serial_no",
					"company",
					"branch",
					"warranty_status",
					"amc_contract",
				],
				as_dict=True,
			)
			if sr:
				for src, dst in (
					("customer", "customer"),
					("installed_base", "installed_base"),
					("item_code", "item_code"),
					("model_no", "model_no"),
					("serial_no", "serial_no"),
					("company", "company"),
					("branch", "branch"),
					("warranty_status", "warranty_status"),
					("amc_contract", "amc_contract"),
				):
					if not self.get(dst) and sr.get(src):
						self.set(dst, sr.get(src))

		if self.engineer_visit and frappe.db.exists("Engineer Visit", self.engineer_visit):
			v = frappe.db.get_value(
				"Engineer Visit",
				self.engineer_visit,
				["service_request", "serial_no", "item_code", "failure_category", "root_cause", "observation"],
				as_dict=True,
			)
			if v:
				if not self.service_request and v.service_request:
					self.service_request = v.service_request
				for src, dst in (
					("serial_no", "serial_no"),
					("item_code", "item_code"),
					("failure_category", "failure_category"),
					("root_cause", "root_cause"),
				):
					if not self.get(dst) and v.get(src):
						self.set(dst, v.get(src))

		if self.diagnosis and frappe.db.exists("Failure Analysis", self.diagnosis):
			d = frappe.db.get_value(
				"Failure Analysis",
				self.diagnosis,
				["service_request", "engineer_visit", "failure_category", "root_cause", "serial_no", "item_code"],
				as_dict=True,
			)
			if d:
				for src, dst in (
					("service_request", "service_request"),
					("engineer_visit", "engineer_visit"),
					("failure_category", "failure_category"),
					("root_cause", "root_cause"),
					("serial_no", "serial_no"),
					("item_code", "item_code"),
				):
					if not self.get(dst) and d.get(src):
						self.set(dst, d.get(src))

	def _calc_estimate(self):
		self.total_estimate = (
			flt(self.labour_cost)
			+ flt(self.spare_cost)
			+ flt(self.courier_cost)
			+ flt(self.misc_cost)
			+ flt(self.tax_amount)
		)

	def _check_duplicate_serial(self):
		if not self.serial_no:
			return
		filters = {
			"serial_no": self.serial_no,
			"docstatus": ["<", 2],
			"status": ["not in", ["Closed", "Cancelled"]],
			"name": ["!=", self.name or ""],
		}
		dup = frappe.db.exists("Repair Order", filters)
		if dup:
			frappe.throw(_("Active Repair Order {0} already exists for serial {1}").format(dup, self.serial_no))

	def _assert_transition(self, old_status, new_status):
		if old_status == new_status:
			return
		allowed = ALLOWED_TRANSITIONS.get(old_status) or set()
		if new_status not in allowed and "System Manager" not in frappe.get_roles():
			frappe.throw(_("Cannot change repair status from {0} to {1}").format(old_status, new_status))

	def _append_timeline(self, activity, remarks=""):
		self.append(
			"repair_timeline",
			{
				"activity": activity,
				"user": frappe.session.user,
				"time": now_datetime(),
				"remarks": remarks,
			},
		)

	def _sync_service_request(self):
		if not self.service_request:
			return
		try:
			sr = frappe.get_doc("Swift Service Request", self.service_request)
			if sr.docstatus != 1:
				return
			map_status = {
				"Awaiting Pickup": "Repair In Progress",
				"Received at Workshop": "Repair In Progress",
				"Initial Inspection": "Repair In Progress",
				"Repair In Progress": "Repair In Progress",
				"Waiting Spare": "Waiting Spare",
				"Testing": "Testing",
				"Quality Inspection": "Testing",
				"Ready for Dispatch": "Customer Verification",
				"Dispatched": "Customer Verification",
				"Installed": "Customer Verification",
				"Closed": "Completed",
			}
			target = map_status.get(self.status)
			if target and sr.status != target and sr.status not in ("Completed", "Closed", "Cancelled"):
				sr.status = target
				sr.flags.ignore_validate_update_after_submit = True
				sr.save(ignore_permissions=True)
		except Exception:
			pass

	def _require_receipt(self):
		if not self.received_date and self.status not in (
			"Draft",
			"Awaiting Pickup",
			"Picked Up",
			"Cancelled",
		):
			frappe.throw(_("Workshop receipt is required before this step"))

	def _require_chargeable_approval(self):
		if self.repair_type == "Chargeable" and self.customer_approval not in ("Approved", "Not Required"):
			frappe.throw(_("Customer approval is required before repair for chargeable orders"))

	def _require_quality_pass(self):
		if self.qi_result != "Pass":
			frappe.throw(_("Quality Inspection must Pass before dispatch"))

	def _open_spares_blocking(self):
		if not self.service_request:
			return False
		return bool(
			frappe.db.exists(
				"Spare Request",
				{
					"service_request": self.service_request,
					"docstatus": ["<", 2],
					"status": ["not in", ["Closed", "Cancelled", "Completed", "Consumed"]],
				},
			)
		)

	# —— workflow actions ——

	def mark_picked_up(self):
		self.status = "Picked Up"
		if not self.pickup_date:
			self.pickup_date = getdate()
		self._append_timeline(_("Picked up from customer"))
		self.save(ignore_permissions=True)
		return self

	def mark_received(self):
		self.status = "Received at Workshop"
		self.received_date = now_datetime()
		if not self.received_by:
			self.received_by = frappe.session.user
		self._append_timeline(_("Received at workshop"))
		self.save(ignore_permissions=True)
		self._sync_service_request()
		return self

	def start_inspection(self):
		self._require_receipt()
		self.status = "Initial Inspection"
		self._append_timeline(_("Initial inspection started"))
		self.save(ignore_permissions=True)
		return self

	def recommend_replacement(self, ber=False):
		self.not_repairable = 1
		if ber:
			self.ber_flag = 1
		self.status = "Replacement Recommended"
		self._append_timeline(_("Replacement recommended") + (" (BER)" if ber else ""))
		self.save(ignore_permissions=True)
		return self

	def request_estimate(self):
		self.status = "Estimate Pending"
		self._append_timeline(_("Estimate pending customer approval"))
		self.save(ignore_permissions=True)
		return self

	def approve_estimate(self):
		self.customer_approval = "Approved"
		self.status = "Customer Approval"
		self._append_timeline(_("Customer approved estimate"))
		self.save(ignore_permissions=True)
		return self

	def start_repair(self):
		self._require_receipt()
		self._require_chargeable_approval()
		if cint(self.not_repairable):
			frappe.throw(_("Product marked not repairable"))
		self.status = "Repair In Progress"
		if not self.planned_start:
			self.planned_start = now_datetime()
		self._append_timeline(_("Repair started"))
		self.save(ignore_permissions=True)
		self._sync_service_request()
		return self

	def mark_waiting_spare(self):
		self.status = "Waiting Spare"
		self._append_timeline(_("Waiting for spare"))
		self.save(ignore_permissions=True)
		self._sync_service_request()
		return self

	def complete_repair(self):
		self.status = "Repair Completed"
		self._append_timeline(_("Repair completed — ready for testing"))
		self.save(ignore_permissions=True)
		return self

	def start_testing(self):
		if self.status not in ("Repair Completed", "Testing", "Quality Inspection"):
			frappe.throw(_("Complete repair before testing"))
		self.status = "Testing"
		if not self.test_checklist:
			for t in (
				"Power Test",
				"Functional Test",
				"Safety Test",
				"Performance Test",
			):
				self.append("test_checklist", {"test_name": t, "result": "Pending"})
		self._append_timeline(_("Testing started"))
		self.save(ignore_permissions=True)
		self._sync_service_request()
		return self

	def pass_testing(self):
		failed = [r.test_name for r in (self.test_checklist or []) if r.result == "Fail"]
		if failed:
			frappe.throw(_("Testing failed: {0}").format(", ".join(failed)))
		for r in self.test_checklist or []:
			if r.result == "Pending":
				r.result = "Pass"
		self.status = "Quality Inspection"
		self._append_timeline(_("Testing passed"))
		self.save(ignore_permissions=True)
		return self

	def pass_quality(self, result="Pass"):
		self.qi_result = result
		self.qi_date = now_datetime()
		if not self.qi_inspector:
			self.qi_inspector = frappe.session.user
		self.append(
			"quality_logs",
			{
				"inspector": self.qi_inspector,
				"inspection_date": self.qi_date,
				"result": result,
				"ncr_reference": self.qi_ncr,
				"rework_required": 1 if result in ("Fail", "Rework") else 0,
			},
		)
		if result == "Pass":
			self.qi_rework_required = 0
			self.status = "Ready for Dispatch"
			self._append_timeline(_("Quality inspection passed"))
		else:
			self.qi_rework_required = 1
			self.status = "Repair In Progress"
			self._append_timeline(_("Quality failed — rework"))
		self.save(ignore_permissions=True)
		return self

	def mark_dispatched(self):
		self._require_quality_pass()
		if not self.dispatch_date:
			self.dispatch_date = now_datetime()
		if not self.dispatched_by:
			self.dispatched_by = frappe.session.user
		self.status = "Dispatched"
		self._append_timeline(_("Dispatched to customer"))
		visit = None
		if cint(self.installation_required) and not self.installation_visit:
			visit = self._create_installation_visit()
		self.save(ignore_permissions=True)
		self._sync_service_request()
		return self

	def mark_installed(self):
		self.status = "Installed"
		self._append_timeline(_("Installation completed"))
		self.save(ignore_permissions=True)
		return self

	def close_order(self):
		if self._open_spares_blocking():
			frappe.throw(_("Close open Spare Requests before closing Repair Order"))
		if self.status not in ("Dispatched", "Installed", "Replacement Recommended", "Not Repairable"):
			if self.status != "Ready for Dispatch":
				pass
		if self.status == "Ready for Dispatch":
			frappe.throw(_("Dispatch the product before closing"))
		if self.status not in ("Dispatched", "Installed", "Closed", "Replacement Recommended", "Not Repairable"):
			frappe.throw(_("Cannot close from status {0}").format(self.status))
		if self.status == "Dispatched" and not self.dispatch_date:
			frappe.throw(_("Dispatch details are required before closure"))
		self.status = "Closed"
		self._append_timeline(_("Repair Order closed"))
		self.save(ignore_permissions=True)
		self._sync_service_request()
		self._maybe_create_service_report()
		return self

	def _maybe_create_service_report(self):
		try:
			from swiftservice.swiftservice.doctype.service_report.service_report import generate_from_source

			generate_from_source(
				service_request=self.service_request,
				engineer_visit=self.engineer_visit,
				repair_order=self.name,
			)
		except Exception:
			frappe.log_error(title="Repair Order Service Report create failed")

	def advance_status(self, status=None):
		cur = STATUS_ALIASES.get(self.status, self.status)
		if status:
			status = STATUS_ALIASES.get(status, status)
			self._assert_transition(self.status, status)
			# route through helpers when possible
			helpers = {
				"Picked Up": self.mark_picked_up,
				"Received at Workshop": self.mark_received,
				"Initial Inspection": self.start_inspection,
				"Repair In Progress": self.start_repair,
				"Waiting Spare": self.mark_waiting_spare,
				"Repair Completed": self.complete_repair,
				"Testing": self.start_testing,
				"Quality Inspection": self.pass_testing,
				"Ready for Dispatch": lambda: self.pass_quality("Pass"),
				"Dispatched": self.mark_dispatched,
				"Installed": self.mark_installed,
				"Closed": self.close_order,
				"Replacement Recommended": self.recommend_replacement,
			}
			fn = helpers.get(status)
			if fn:
				return fn()
			self.status = status
			self._append_timeline(_("Status → {0}").format(status))
			self.save(ignore_permissions=True)
			self._sync_service_request()
			return self

		if cur not in STATUS_ORDER:
			cur = "Draft"
		idx = STATUS_ORDER.index(cur)
		# smart skips
		while idx < len(STATUS_ORDER) - 1:
			nxt = STATUS_ORDER[idx + 1]
			if nxt == "Awaiting Pickup" and not cint(self.pickup_required):
				idx += 1
				continue
			if nxt == "Estimate Pending" and self.repair_type != "Chargeable":
				idx += 1
				continue
			if nxt == "Customer Approval" and self.repair_type != "Chargeable":
				idx += 1
				continue
			if nxt == "Waiting Spare":
				idx += 1
				continue
			if nxt == "Installed" and not cint(self.installation_required):
				idx += 1
				continue
			return self.advance_status(nxt)
		return self

	def _create_installation_visit(self):
		try:
			visit = frappe.get_doc(
				{
					"doctype": "Engineer Visit",
					"naming_series": "SV-.YYYY.-.#####",
					"service_request": self.service_request,
					"engineer": self.workshop_technician or frappe.session.user,
					"visit_date": nowdate(),
					"visit_type": "Installation",
					"status": "Scheduled",
					"visit_purpose": f"Installation after Repair Order {self.name}",
				}
			)
			visit.insert(ignore_permissions=True)
			self.installation_visit = visit.name
			self._append_timeline(_("Installation visit {0} created").format(visit.name))
			return visit.name
		except Exception:
			frappe.log_error(title="Repair Order installation visit failed")
			return None


def create_from_source(service_request=None, engineer_visit=None, diagnosis=None, repair_type=None):
	doc = frappe.get_doc(
		{
			"doctype": "Repair Order",
			"naming_series": "RO-.YYYY.-.#####",
			"service_request": service_request,
			"engineer_visit": engineer_visit,
			"diagnosis": diagnosis,
			"repair_type": repair_type or "Warranty",
			"status": "Draft",
			"priority": "Medium",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc
