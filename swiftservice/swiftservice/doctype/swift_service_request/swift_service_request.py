import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime


# Canonical forward path (legacy names kept for data; prefer new names in code)
ALLOWED_TRANSITIONS = {
	"Draft": {"Open", "Under Validation", "Cancelled"},
	"Open": {"Under Validation", "Assigned", "Cancelled"},
	"Under Validation": {"Assigned", "Open", "Cancelled"},
	"Assigned": {"Accepted", "Open", "Cancelled"},
	"Accepted": {"Travel Started", "Assigned", "Cancelled"},
	"Travel Started": {"Reached Customer", "Reached Site", "Accepted", "Cancelled"},
	"Reached Customer": {"Inspection", "Waiting Customer", "Cancelled"},
	"Reached Site": {"Inspection", "Waiting Customer", "Reached Customer", "Cancelled"},
	"Inspection": {
		"Waiting Customer",
		"Waiting Spare",
		"Repair In Progress",
		"Repair",
		"Testing",
		"Completed",
		"Cancelled",
	},
	"Waiting Customer": {"Inspection", "Travel Started", "Cancelled"},
	"Waiting Spare": {"Repair In Progress", "Repair", "Inspection", "Cancelled"},
	"Repair In Progress": {"Testing", "Waiting Spare", "Completed", "Cancelled"},
	"Repair": {"Testing", "Repair In Progress", "Waiting Spare", "Completed", "Cancelled"},
	"Testing": {"Customer Verification", "Customer Approval", "Repair In Progress", "Cancelled"},
	"Customer Verification": {"Completed", "Testing", "Cancelled"},
	"Customer Approval": {"Completed", "Customer Verification", "Testing", "Cancelled"},
	"Completed": {"Closed", "Customer Verification"},
	"Closed": {"Completed"},  # reopen only via Service Closure approve_reopen flag
	"Cancelled": set(),
}

OPEN_STATUSES = {
	"Open",
	"Under Validation",
	"Assigned",
	"Accepted",
	"Travel Started",
	"Reached Customer",
	"Reached Site",
	"Inspection",
	"Waiting Customer",
	"Waiting Spare",
	"Repair In Progress",
	"Repair",
	"Testing",
	"Customer Verification",
	"Customer Approval",
}


class SwiftServiceRequest(Document):
	def validate(self):
		self._set_defaults()
		self._sync_warranty_status()
		self._validate_engineer()
		self._validate_amc()
		self._warn_duplicate_open()
		self._normalize_geo()

	def _normalize_geo(self):
		"""Drop null-island pins; geocode address when pin missing."""
		from frappe.utils import flt
		from swiftservice.swiftservice.doctype.engineer_visit.engineer_visit import (
			geocode_address,
			is_valid_geo,
		)

		lat, lng = flt(self.geo_latitude), flt(self.geo_longitude)
		if not is_valid_geo(lat, lng):
			self.geo_latitude = None
			self.geo_longitude = None
			if self.customer_address and len(str(self.customer_address).strip()) >= 8:
				hit = geocode_address(self.customer_address)
				if hit:
					self.geo_latitude = hit["lat"]
					self.geo_longitude = hit["lng"]
		elif not self.customer_address:
			from swiftservice.swiftservice.doctype.engineer_visit.engineer_visit import (
				reverse_geocode,
			)

			addr = reverse_geocode(lat, lng)
			if addr:
				self.customer_address = addr

	def before_submit(self):
		self._validate_before_submit()
		if self.status in (None, "", "Draft"):
			self.status = "Open"

	def on_submit(self):
		self._add_timeline(_("Service Request submitted and opened."))
		self._notify_coordinator_soft()

	def on_update_after_submit(self):
		# Status transition checks when status changed on submitted doc
		if self.has_value_changed("status"):
			old = self.get_doc_before_save()
			if old:
				self._assert_transition(old.status, self.status)
			if self.status == "Closed" and old and old.status != "Closed":
				if not getattr(self.flags, "service_closure_approved", False):
					from swiftservice.swiftservice.doctype.service_closure.service_closure import (
						assert_can_close_service_request,
					)

					assert_can_close_service_request(self.name)
				self.closed_by = frappe.session.user
				self.closed_on = now_datetime()
			if self.status == "Completed" and old and old.status == "Closed":
				if not getattr(self.flags, "service_closure_reopen", False):
					if "System Manager" not in frappe.get_roles():
						frappe.throw(_("Reopen Service Request only via approved Service Closure reopen"))
				self._add_timeline(_("Service Request reopened"))

	def on_cancel(self):
		self.db_set("status", "Cancelled", update_modified=True)
		self._add_timeline(_("Service Request cancelled."))

	def _set_defaults(self):
		if not self.posting_date:
			self.posting_date = getdate()
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)

	def _validate_before_submit(self):
		if not self.customer:
			frappe.throw(_("Customer is mandatory before submit"))
		if not self.subject and not self.complaint_description:
			frappe.throw(_("Subject or Complaint Description is mandatory"))
		if not self.priority:
			frappe.throw(_("Priority is mandatory"))
		if not self.installed_base and not self.serial_no:
			frappe.msgprint(
				_("Installed Product or Serial Number is recommended before submit"),
				indicator="orange",
				alert=True,
			)

	def _sync_warranty_status(self):
		if not self.warranty_end:
			return
		today = getdate()
		end = getdate(self.warranty_end)
		if today <= end:
			self.warranty_applicable = 1
			if self.warranty_status in (None, "", "Out of Warranty", "Not Applicable"):
				self.warranty_status = "In Warranty"
		else:
			if self.warranty_status == "In Warranty":
				self.warranty_status = "Out of Warranty"

	def _validate_engineer(self):
		if not self.assigned_engineer:
			return
		enabled = frappe.db.get_value("User", self.assigned_engineer, "enabled")
		if not enabled:
			frappe.throw(_("Assigned Engineer {0} is not an active user").format(self.assigned_engineer))

	def _validate_amc(self):
		if not self.amc_contract:
			return
		if self.amc_status == "Active" and self.remaining_visits is not None and self.remaining_visits <= 0:
			frappe.throw(_("AMC Contract has no remaining visits"))

	def _warn_duplicate_open(self):
		if not self.customer:
			return
		filters = {
			"customer": self.customer,
			"status": ["in", list(OPEN_STATUSES)],
			"docstatus": ["<", 2],
			"name": ["!=", self.name or ""],
		}
		if self.serial_no:
			filters["serial_no"] = self.serial_no
		if self.complaint_category:
			filters["complaint_category"] = self.complaint_category
		elif self.complaint_type:
			filters["complaint_type"] = self.complaint_type

		existing = frappe.db.exists("Swift Service Request", filters)
		if existing:
			frappe.msgprint(
				_("Open Service Request {0} already exists for this customer / serial / category").format(
					existing
				),
				indicator="orange",
				alert=True,
			)

	def _assert_transition(self, old_status, new_status):
		if not old_status or old_status == new_status:
			return
		allowed = ALLOWED_TRANSITIONS.get(old_status)
		if allowed is None:
			return
		if new_status not in allowed and new_status != old_status:
			# Soft warning for API bulk moves / aliases — still allow System Manager
			if "System Manager" not in frappe.get_roles():
				frappe.throw(
					_("Cannot move status from {0} to {1}").format(old_status, new_status)
				)

	def _add_timeline(self, content):
		try:
			self.add_comment("Info", content)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "SSR Timeline")

	def _notify_coordinator_soft(self):
		email = None
		if self.service_coordinator:
			email = frappe.db.get_value("User", self.service_coordinator, "email")
		if not email and self.email_id:
			email = self.email_id
		if not email:
			return
		try:
			frappe.sendmail(
				recipients=[email],
				subject=_("Service Request {0} submitted").format(self.name),
				message=_("Service Request <b>{0}</b> for customer <b>{1}</b> is now Open.").format(
					self.name, self.customer or "—"
				),
				delayed=True,
				retry=1,
			)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "SSR Notify")
