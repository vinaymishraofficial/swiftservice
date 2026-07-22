import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, now_datetime, time_diff_in_hours


STATUS_ALIASES = {
	"Open": "Draft",
	"Reviewed": "Analysis",
}

ALLOWED_TRANSITIONS = {
	"Draft": {"Inspection", "Cancelled"},
	"Inspection": {"Analysis", "Draft", "Cancelled"},
	"Analysis": {"Root Cause Identified", "Inspection", "Cancelled"},
	"Root Cause Identified": {"Corrective Action", "Analysis", "Cancelled"},
	"Corrective Action": {"Verification", "Root Cause Identified", "Cancelled"},
	"Verification": {"Approved", "Corrective Action", "Cancelled"},
	"Approved": {"Closed", "Verification"},
	"Closed": set(),
	"Cancelled": set(),
	"Open": {"Inspection", "Analysis", "Cancelled"},
	"Reviewed": {"Root Cause Identified", "Corrective Action", "Cancelled"},
}

COMPLEX_OUTCOMES = {
	"Spare Required",
	"Repair",
	"Workshop Repair",
	"Replacement",
	"Design Issue",
	"Supplier Issue",
	"Manufacturing Defect",
	"Calibration",
	"Software Update",
	"Firmware Update",
}

REPEAT_WINDOW_DAYS = 30


class FailureAnalysis(Document):
	def validate(self):
		self._set_defaults()
		self._fetch_from_links()
		self._calc_downtime()
		self._detect_repeat_failure()

	def before_submit(self):
		self._validate_before_close_or_submit()
		if self.status in (None, "", "Draft", "Open"):
			self.status = "Approved"

	def on_submit(self):
		self._append_timeline(_("Diagnosis submitted"))
		self._apply_outcomes()
		self._notify_stakeholders()

	def on_update_after_submit(self):
		if self.has_value_changed("status"):
			old = self.get_doc_before_save()
			if old:
				self._assert_transition(old.status, self.status)
			if self.status == "Closed":
				self._validate_before_close_or_submit()

	def on_cancel(self):
		self.db_set("status", "Cancelled", update_modified=True)

	def _set_defaults(self):
		if not self.naming_series:
			self.naming_series = "DX-.YYYY.-.#####"
		if not self.status:
			self.status = "Draft"
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)
		if self.status in STATUS_ALIASES and self.is_new():
			self.status = STATUS_ALIASES[self.status]

	def _fetch_from_links(self):
		if self.engineer_visit and frappe.db.exists("Engineer Visit", self.engineer_visit):
			v = frappe.db.get_value(
				"Engineer Visit",
				self.engineer_visit,
				[
					"service_request",
					"customer",
					"installed_base",
					"item_code",
					"model_no",
					"serial_no",
					"company",
					"branch",
					"diagnosis_result",
					"failure_category",
					"root_cause",
					"component",
					"observation",
					"diagnosis_notes",
					"error_code",
					"alarm_code",
					"running_hours",
					"voltage",
					"temperature",
					"pressure",
					"power_supply",
					"environment",
					"work_done",
				],
				as_dict=True,
			)
			if v:
				for src, dst in (
					("service_request", "service_request"),
					("installed_base", "installed_base"),
					("item_code", "item_code"),
					("model_no", "model_no"),
					("serial_no", "serial_no"),
					("company", "company"),
					("branch", "branch"),
					("failure_category", "failure_category"),
					("root_cause", "root_cause"),
					("component", "component"),
					("observation", "observation"),
					("error_code", "error_code"),
					("alarm_code", "alarm_code"),
					("running_hours", "running_hours"),
					("voltage", "voltage"),
					("temperature", "temperature"),
					("pressure", "pressure"),
					("power_supply", "power_supply"),
					("environment", "environment"),
				):
					if not self.get(dst) and v.get(src):
						self.set(dst, v.get(src))
				if not self.investigation_notes and v.get("diagnosis_notes"):
					self.investigation_notes = v.diagnosis_notes
				if not self.action_taken and v.get("work_done"):
					self.action_taken = v.work_done
				if not self.diagnosis_result and v.get("diagnosis_result"):
					self.diagnosis_result = _map_visit_outcome(v.diagnosis_result)
				if not self.source:
					self.source = "Service Visit"

		if self.service_request and frappe.db.exists("Swift Service Request", self.service_request):
			sr = frappe.db.get_value(
				"Swift Service Request",
				self.service_request,
				["installed_base", "item_code", "model_no", "serial_no", "company", "branch"],
				as_dict=True,
			)
			if sr:
				for src, dst in (
					("installed_base", "installed_base"),
					("item_code", "item_code"),
					("model_no", "model_no"),
					("serial_no", "serial_no"),
					("company", "company"),
					("branch", "branch"),
				):
					if not self.get(dst) and sr.get(src):
						self.set(dst, sr.get(src))

	def _calc_downtime(self):
		if self.failure_start_time and self.failure_end_time:
			try:
				self.downtime_hours = flt(time_diff_in_hours(self.failure_end_time, self.failure_start_time), 2)
			except Exception:
				pass

	def _detect_repeat_failure(self):
		if not self.service_request and not self.serial_no and not self.installed_base:
			return
		filters = {"name": ["!=", self.name or ""], "docstatus": ["<", 2]}
		or_filters = []
		if self.serial_no:
			or_filters.append(["serial_no", "=", self.serial_no])
		if self.installed_base:
			or_filters.append(["installed_base", "=", self.installed_base])
		if self.service_request:
			# same customer asset via prior diagnoses on related SRs with same IB/serial preferred
			pass
		if not or_filters:
			return
		since = frappe.utils.add_days(getdate(), -REPEAT_WINDOW_DAYS)
		rows = frappe.get_all(
			"Failure Analysis",
			filters={**filters, "creation": [">=", since]},
			or_filters=or_filters,
			pluck="name",
		)
		count = len(rows)
		self.failure_repeat_count = count
		self.is_repeat_failure = 1 if count >= 1 else 0
		if self.is_repeat_failure and self.service_request:
			try:
				frappe.db.set_value(
					"Swift Service Request",
					self.service_request,
					"priority",
					"Urgent",
					update_modified=False,
				)
			except Exception:
				pass

	def _validate_before_close_or_submit(self):
		if not self.root_cause:
			frappe.throw(_("Root Cause is required before submit/close"))
		if not self.action_taken:
			frappe.throw(_("Corrective Action (Action Taken) is required before submit/close"))
		if self.status == "Closed" and not self.verification_notes:
			frappe.throw(_("Verification Notes are required before close"))
		if self.safety_risk_level in ("High", "Critical") and not self.rca_approval_by:
			frappe.throw(_("Safety-critical failures require RCA Approval By (management)"))

	def _assert_transition(self, old_status, new_status):
		if old_status == new_status:
			return
		allowed = ALLOWED_TRANSITIONS.get(old_status) or set()
		if new_status not in allowed and "System Manager" not in frappe.get_roles():
			frappe.throw(_("Cannot change diagnosis status from {0} to {1}").format(old_status, new_status))

	def _append_timeline(self, activity, remarks=""):
		self.append(
			"diagnosis_timeline",
			{
				"activity": activity,
				"user": frappe.session.user,
				"time": now_datetime(),
				"remarks": remarks,
			},
		)

	def advance_status(self, status=None):
		order = [
			"Draft",
			"Inspection",
			"Analysis",
			"Root Cause Identified",
			"Corrective Action",
			"Verification",
			"Approved",
			"Closed",
		]
		cur = STATUS_ALIASES.get(self.status, self.status)
		if status:
			status = STATUS_ALIASES.get(status, status)
			self._assert_transition(self.status, status)
			self.status = status
		elif cur in order:
			idx = order.index(cur)
			if idx < len(order) - 1:
				nxt = order[idx + 1]
				self._assert_transition(self.status, nxt)
				self.status = nxt
		self._append_timeline(_("Status → {0}").format(self.status))
		self.save(ignore_permissions=True)
		return self

	def _apply_outcomes(self):
		result = self.diagnosis_result
		if not result or not self.service_request:
			return
		try:
			from swiftservice.api import update_diagnosis

			map_to_ssr = {
				"Fixed": "Issue Fixed",
				"Spare Required": "Spare Required",
				"Repair": "Factory Repair",
				"Workshop Repair": "Factory Repair",
				"Replacement": "Replacement Required",
				"No Fault Found": "No Fault Found",
				"Calibration": "Issue Fixed",
				"Software Update": "Issue Fixed",
				"Firmware Update": "Issue Fixed",
				"Design Issue": "Factory Repair",
				"Supplier Issue": "Spare Required",
				"Customer Misuse": "No Fault Found",
				"Manufacturing Defect": "Factory Repair",
			}
			ssr_diag = map_to_ssr.get(result)
			if ssr_diag:
				update_diagnosis(
					self.service_request,
					ssr_diag,
					resolution_summary=self.action_taken or self.root_cause,
				)
		except Exception:
			frappe.log_error(title="Diagnosis outcome sync failed")

		# Soft refs for quality / supplier / engineering
		if result in ("Manufacturing Defect", "Design Issue") and not self.capa_reference:
			self.db_set("capa_reference", f"PENDING-CAPA-{self.name}", update_modified=False)
		if result == "Supplier Issue" and not self.supplier_complaint_reference:
			self.db_set("supplier_complaint_reference", f"PENDING-SC-{self.name}", update_modified=False)
		if result == "Design Issue" and not self.engineering_change_request:
			self.db_set("engineering_change_request", f"PENDING-ECR-{self.name}", update_modified=False)

	def _notify_stakeholders(self):
		# Soft notifications — create ToDo / comment style, no hard email dependency
		try:
			if self.root_cause_category == "Supplier Issue" or self.diagnosis_result == "Supplier Issue":
				_soft_notify("Purchase Manager", f"Supplier issue on Diagnosis {self.name}")
			if self.root_cause_category == "Design Defect" or self.diagnosis_result == "Design Issue":
				_soft_notify("R&D", f"Design issue on Diagnosis {self.name}")
			if self.is_repeat_failure:
				_soft_notify("Quality Head", f"Repeat failure flagged on Diagnosis {self.name}")
			if self.safety_risk_level in ("High", "Critical"):
				_soft_notify("Management", f"Safety-critical Diagnosis {self.name}")
		except Exception:
			pass


def _map_visit_outcome(visit_result):
	return {
		"Fixed": "Fixed",
		"Spare Required": "Spare Required",
		"Workshop Repair": "Workshop Repair",
		"Replacement": "Replacement",
		"Software Issue": "Software Update",
		"Calibration Needed": "Calibration",
		"No Fault Found": "No Fault Found",
		"Customer Not Available": "No Fault Found",
	}.get(visit_result, visit_result)


def _soft_notify(role_or_label, subject):
	# Prefer creating a Comment on the doc; role-based email is optional later
	frappe.logger("swiftservice").info(f"[Diagnosis notify:{role_or_label}] {subject}")


def should_create_standalone(visit_doc):
	"""Complex cases get a standalone Diagnosis record."""
	result = getattr(visit_doc, "diagnosis_result", None)
	if result in COMPLEX_OUTCOMES:
		return True
	# repeat / safety heuristics can be added by caller
	return False


def create_from_visit(visit_name, force=False):
	visit = frappe.get_doc("Engineer Visit", visit_name)
	existing = frappe.db.get_value(
		"Failure Analysis",
		{"engineer_visit": visit_name, "docstatus": ["<", 2]},
		"name",
	)
	if existing:
		return frappe.get_doc("Failure Analysis", existing)
	if not force and not should_create_standalone(visit) and visit.diagnosis_result == "Fixed":
		# Routine fixed visit — optional skip unless forced
		pass
	doc = frappe.get_doc(
		{
			"doctype": "Failure Analysis",
			"naming_series": "DX-.YYYY.-.#####",
			"engineer_visit": visit.name,
			"service_request": visit.service_request,
			"status": "Draft",
			"source": "Service Visit",
			"diagnosis_result": _map_visit_outcome(visit.diagnosis_result),
		}
	)
	doc.insert(ignore_permissions=True)
	return doc
