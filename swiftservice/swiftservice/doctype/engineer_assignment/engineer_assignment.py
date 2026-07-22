import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime


ALLOWED_TRANSITIONS = {
	"Draft": {"Pending Assignment", "Assigned", "Cancelled"},
	"Pending Assignment": {"Assigned", "Cancelled"},
	"Assigned": {"Engineer Accepted", "Pending Assignment", "Cancelled"},
	"Engineer Accepted": {"Travel Started", "Assigned", "Cancelled"},
	"Travel Started": {"Reached Customer", "Engineer Accepted", "Cancelled"},
	"Reached Customer": {"Visit Completed", "Travel Started", "Cancelled"},
	"Visit Completed": {"Assignment Closed", "Reached Customer"},
	"Assignment Closed": set(),
	"Cancelled": set(),
}

OPEN_ASSIGNMENT_STATUSES = {
	"Assigned",
	"Engineer Accepted",
	"Travel Started",
	"Reached Customer",
}


class EngineerAssignment(Document):
	def validate(self):
		self._set_defaults()
		self._fetch_from_service_request()
		self._sync_primary_row()
		if self.primary_engineer:
			self._validate_engineer(self.primary_engineer)
		if self.secondary_engineer:
			self._validate_engineer(self.secondary_engineer, role="Secondary")

	def before_submit(self):
		if not self.service_request:
			frappe.throw(_("Service Request is mandatory"))
		if not self.primary_engineer and not self.assigned_engineers:
			frappe.throw(_("Primary Engineer is required before submit"))
		if self.status in (None, "", "Draft", "Pending Assignment"):
			self.status = "Assigned"
		if not self.assignment_date:
			self.assignment_date = now_datetime()
		if not self.assigned_by:
			self.assigned_by = frappe.session.user
		self._append_timeline(_("Assignment submitted"), _("Engineer {0}").format(self.primary_engineer))

	def on_submit(self):
		self._sync_service_request()
		self._ensure_engineer_visit()
		self._notify_engineer_soft()

	def on_update_after_submit(self):
		if self.has_value_changed("status"):
			old = self.get_doc_before_save()
			if old:
				self._assert_transition(old.status, self.status)
			if self.status == "Assignment Closed" and not self.completion_time:
				self.completion_time = now_datetime()
			if self.status in OPEN_ASSIGNMENT_STATUSES | {"Visit Completed", "Assignment Closed"}:
				self._sync_service_request()

	def on_cancel(self):
		self.db_set("status", "Cancelled", update_modified=True)
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": self.doctype,
				"reference_name": self.name,
				"content": _("Assignment cancelled"),
			}
		).insert(ignore_permissions=True)

	def _set_defaults(self):
		if not self.posting_date:
			self.posting_date = getdate()
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)
		if not self.status:
			self.status = "Draft"

	def _fetch_from_service_request(self):
		if not self.service_request:
			return
		sr = frappe.db.get_value(
			"Swift Service Request",
			self.service_request,
			[
				"customer",
				"installed_base",
				"serial_no",
				"amc_contract",
				"warranty_status",
				"priority",
				"company",
				"branch",
				"geo_latitude",
				"geo_longitude",
				"resolution_due",
				"response_due",
			],
			as_dict=True,
		)
		if not sr:
			return
		for src, dst in (
			("customer", "customer"),
			("installed_base", "installed_base"),
			("serial_no", "serial_no"),
			("amc_contract", "amc_contract"),
			("warranty_status", "warranty_status"),
			("company", "company"),
			("branch", "branch"),
		):
			if not self.get(dst) and sr.get(src):
				self.set(dst, sr.get(src))
		if not self.priority and sr.priority:
			self.priority = sr.priority
		if self.customer_latitude is None and sr.geo_latitude is not None:
			self.customer_latitude = sr.geo_latitude
		if self.customer_longitude is None and sr.geo_longitude is not None:
			self.customer_longitude = sr.geo_longitude
		if not self.sla_deadline:
			self.sla_deadline = sr.resolution_due or sr.response_due

	def _sync_primary_row(self):
		"""Keep Assigned Engineers child in sync with primary/secondary."""
		if not self.primary_engineer:
			return
		found = False
		for row in self.assigned_engineers or []:
			if row.engineer == self.primary_engineer:
				row.role = row.role or "Primary"
				found = True
				break
		if not found:
			self.append(
				"assigned_engineers",
				{
					"engineer": self.primary_engineer,
					"role": "Primary",
					"status": "Pending" if self.status in ("Draft", "Pending Assignment", "Assigned") else "Accepted",
				},
			)
		if self.secondary_engineer:
			sec = next((r for r in (self.assigned_engineers or []) if r.engineer == self.secondary_engineer), None)
			if not sec:
				self.append(
					"assigned_engineers",
					{"engineer": self.secondary_engineer, "role": "Secondary", "status": "Pending"},
				)

	def _validate_engineer(self, user, role="Primary"):
		if not frappe.db.exists("User", user):
			frappe.throw(_("Engineer {0} is not a valid User").format(user))
		if not frappe.db.get_value("User", user, "enabled"):
			frappe.throw(_("Engineer {0} is disabled").format(user))

		profile_name = frappe.db.get_value("Engineer Profile", {"engineer": user}, "name")
		if profile_name:
			profile = frappe.get_cached_doc("Engineer Profile", profile_name)
			if profile.status == "Inactive":
				frappe.throw(_("Engineer Profile for {0} is Inactive").format(user))
			if profile.status == "On Leave":
				frappe.throw(_("Engineer {0} is On Leave").format(user))
			max_jobs = cint_or_default(getattr(profile, "max_open_jobs", None), 5)
			workload = cint_or_default(profile.workload, 0)
			# Count open assignments for this engineer excluding self
			open_count = frappe.db.count(
				"Engineer Assignment",
				{
					"primary_engineer": user,
					"status": ["in", list(OPEN_ASSIGNMENT_STATUSES)],
					"docstatus": ["<", 2],
					"name": ["!=", self.name or ""],
				},
			)
			effective = max(workload, open_count)
			if effective >= max_jobs and self.status in ("Draft", "Pending Assignment", "Assigned"):
				frappe.throw(
					_("Engineer {0} has reached maximum workload ({1}/{2})").format(
						user, effective, max_jobs
					)
				)
			if not self.engineer_profile and role == "Primary":
				self.engineer_profile = profile_name

			if self.certification:
				certs = (profile.certifications or "").lower()
				if self.certification.lower() not in certs:
					frappe.msgprint(
						_("Warning: {0} may not have required certification {1}").format(
							user, self.certification
						),
						indicator="orange",
						alert=True,
					)

			if self.max_distance_km and self.distance_km and flt_or_default(self.distance_km) > flt_or_default(
				self.max_distance_km
			):
				frappe.throw(
					_("Distance {0} km exceeds configured max {1} km").format(
						self.distance_km, self.max_distance_km
					)
				)

	def _assert_transition(self, old_status, new_status):
		if old_status == new_status:
			return
		allowed = ALLOWED_TRANSITIONS.get(old_status) or set()
		if new_status not in allowed and "System Manager" not in frappe.get_roles():
			frappe.throw(_("Cannot change status from {0} to {1}").format(old_status, new_status))

	def _append_timeline(self, activity, remarks=""):
		self.append(
			"assignment_timeline",
			{
				"activity": activity,
				"user": frappe.session.user,
				"time": now_datetime(),
				"remarks": remarks,
			},
		)

	def _sync_service_request(self):
		if not self.service_request or not frappe.db.exists("Swift Service Request", self.service_request):
			return
		sr = frappe.get_doc("Swift Service Request", self.service_request)
		changed = False
		if self.primary_engineer and sr.assigned_engineer != self.primary_engineer:
			sr.assigned_engineer = self.primary_engineer
			changed = True
		if self.engineer_profile and sr.engineer_profile != self.engineer_profile:
			sr.engineer_profile = self.engineer_profile
			changed = True
		if self.assignment_date and not sr.assignment_date:
			sr.assignment_date = self.assignment_date
			changed = True
		if self.assigned_by and not sr.assigned_by:
			sr.assigned_by = self.assigned_by
			changed = True
		if self.planned_visit and sr.planned_date != self.planned_visit:
			sr.planned_date = self.planned_visit
			changed = True

		# Map assignment status → SSR status (conservative)
		status_map = {
			"Assigned": "Assigned",
			"Engineer Accepted": "Accepted",
			"Travel Started": "Travel Started",
			"Reached Customer": "Reached Customer",
			"Visit Completed": "Inspection",
			"Assignment Closed": "Completed",
		}
		target = status_map.get(self.status)
		if target and sr.status != target and sr.docstatus == 1:
			sr.status = target
			changed = True
			if self.status == "Engineer Accepted" and not sr.acceptance_time:
				sr.acceptance_time = now_datetime()

		if changed:
			sr.flags.ignore_validate_update_after_submit = True
			sr.save(ignore_permissions=True)

	def _ensure_engineer_visit(self):
		if self.engineer_visit and frappe.db.exists("Engineer Visit", self.engineer_visit):
			return
		if not self.primary_engineer:
			return
		payload = {
			"doctype": "Engineer Visit",
			"naming_series": "SV-.YYYY.-.#####",
			"service_request": self.service_request,
			"engineer": self.primary_engineer,
			"visit_date": self.planned_visit or now_datetime().date(),
			"status": "Scheduled",
			"visit_type": "Breakdown",
		}
		if frappe.get_meta("Engineer Visit").has_field("engineer_assignment"):
			payload["engineer_assignment"] = self.name
		visit = frappe.get_doc(payload).insert(ignore_permissions=True)
		self.db_set("engineer_visit", visit.name, update_modified=False)

	def _notify_engineer_soft(self):
		if not self.primary_engineer:
			return
		email = frappe.db.get_value("User", self.primary_engineer, "email")
		if not email:
			return
		try:
			frappe.sendmail(
				recipients=[email],
				subject=_("New Service Assignment {0}").format(self.name),
				message=_(
					"You have been assigned to Service Request {0}. Priority: {1}. Planned visit: {2}."
				).format(self.service_request, self.priority or "-", self.planned_visit or "-"),
				delayed=True,
				retry=0,
			)
		except Exception:
			frappe.log_error(title="Engineer Assignment notify failed")


def cint_or_default(val, default=0):
	from frappe.utils import cint

	try:
		return cint(val) if val is not None else default
	except Exception:
		return default


def flt_or_default(val, default=0.0):
	from frappe.utils import flt

	try:
		return flt(val) if val is not None else default
	except Exception:
		return default
