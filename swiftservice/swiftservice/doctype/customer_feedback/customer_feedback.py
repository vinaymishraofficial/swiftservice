import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate, now_datetime, nowdate


STATUS_ALIASES = {
	"Received": "Customer Responded",
	"Submitted": "Customer Responded",
}

ALLOWED_TRANSITIONS = {
	"Draft": {"Feedback Requested", "Customer Responded", "Cancelled"},
	"Feedback Requested": {"Customer Responded", "Draft", "Cancelled", "Closed"},
	"Customer Responded": {"Reviewed", "Escalation", "Feedback Requested", "Cancelled"},
	"Reviewed": {"Closed", "Escalation", "Customer Responded"},
	"Escalation": {"Reviewed", "Closed", "Cancelled"},
	"Closed": set(),
	"Cancelled": set(),
	# legacy
	"Received": {"Reviewed", "Closed", "Escalation"},
	"Submitted": {"Reviewed", "Closed", "Escalation"},
}

STATUS_ORDER = [
	"Draft",
	"Feedback Requested",
	"Customer Responded",
	"Reviewed",
	"Closed",
]

DEFAULT_CATEGORIES = [
	"Engineer Behaviour",
	"Technical Knowledge",
	"Communication",
	"Response Time",
	"Resolution Quality",
	"Cleanliness",
	"Professionalism",
	"Overall Experience",
]

FEEDBACK_WINDOW_DAYS = 30


class CustomerFeedback(Document):
	def validate(self):
		self._set_defaults()
		self._sync_legacy_fields()
		self._calc_nps_category()
		self._validate_ratings()
		self._eval_escalation_flags()

	def before_submit(self):
		if self.status in (None, "", "Draft", "Feedback Requested"):
			self.status = "Customer Responded"
		if self.status == "Customer Responded":
			pass

	def on_submit(self):
		self._append_timeline(_("Feedback submitted"))

	def on_cancel(self):
		self.status = "Cancelled"

	def on_update_after_submit(self):
		if self.has_value_changed("status"):
			old = self.get_doc_before_save()
			if old:
				self._assert_transition(old.status, self.status)

	def _set_defaults(self):
		if not self.naming_series:
			self.naming_series = "FDBK-.YYYY.-.#####"
		if not self.status:
			self.status = "Draft"
		if not self.feedback_date:
			self.feedback_date = nowdate()
		if not self.revision:
			self.revision = 1
		if not self.channel:
			self.channel = "Portal"
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)

	def _sync_legacy_fields(self):
		if self.csat_rating and not self.rating:
			self.rating = str(self.csat_rating)
		elif self.rating and not self.csat_rating:
			self.csat_rating = str(self.rating)
		if self.would_recommend_us == "Yes":
			self.would_recommend = 1
		elif self.would_recommend_us == "No":
			self.would_recommend = 0
		if self.feedback_text and not self.positive_feedback and not self.complaint_text:
			# leave as legacy dump
			pass

	def _calc_nps_category(self):
		if self.nps_score in (None, ""):
			self.nps_category = None
			return
		score = cint(self.nps_score)
		if score < 0:
			score = 0
		if score > 10:
			score = 10
		self.nps_score = score
		if score >= 9:
			self.nps_category = "Promoter"
		elif score >= 7:
			self.nps_category = "Passive"
		else:
			self.nps_category = "Detractor"
		if self.would_recommend_us in (None, "") and score is not None:
			self.would_recommend_us = "Yes" if score >= 9 else ("No" if score <= 6 else self.would_recommend_us)

	def _validate_ratings(self):
		csat = cint(self.csat_rating or self.rating or 0)
		if csat and csat <= 2:
			has_comment = (
				(self.complaint_text or "").strip()
				or (self.feedback_text or "").strip()
				or (self.suggestions or "").strip()
				or any((r.comment or "").strip() for r in (self.comment_rows or []))
			)
			if self.status in ("Customer Responded", "Reviewed", "Escalation", "Closed", "Submitted", "Received") and not has_comment:
				frappe.throw(_("Comments are mandatory for CSAT ratings of 2 or below"))

	def _eval_escalation_flags(self):
		csat = cint(self.csat_rating or self.rating or 0)
		nps = self.nps_score
		needs = False
		reasons = []
		if csat and csat <= 2:
			needs = True
			reasons.append(_("CSAT ≤ 2"))
		if nps not in (None, "") and cint(nps) <= 6:
			needs = True
			reasons.append(_("NPS ≤ 6 (Detractor)"))
		if self.issue_resolved == "No":
			needs = True
			reasons.append(_("Issue not resolved"))
		if cint(self.complaint_against_engineer):
			needs = True
			reasons.append(_("Complaint against engineer"))
		self.escalation_required = 1 if needs else 0
		if needs and not self.escalation_status:
			self.escalation_status = "Open"
		elif not needs and self.escalation_status in (None, "", "Open"):
			self.escalation_status = "Not Required"
		return reasons

	def _assert_transition(self, old_status, new_status):
		if old_status == new_status:
			return
		allowed = ALLOWED_TRANSITIONS.get(old_status) or set()
		if new_status not in allowed and "System Manager" not in frappe.get_roles():
			frappe.throw(_("Cannot change feedback status from {0} to {1}").format(old_status, new_status))

	def _append_timeline(self, activity, remarks=""):
		self.append(
			"feedback_timeline",
			{
				"activity": activity,
				"user": frappe.session.user,
				"time": now_datetime(),
				"remarks": remarks,
			},
		)

	def _ensure_rating_template(self):
		if self.rating_details:
			return
		for cat in DEFAULT_CATEGORIES:
			self.append("rating_details", {"category": cat, "rating": "5"})

	def populate_from_sources(self):
		if self.service_request and frappe.db.exists("Swift Service Request", self.service_request):
			sr = frappe.db.get_value(
				"Swift Service Request",
				self.service_request,
				["customer", "company", "branch", "contact_person", "mobile_no", "email_id"],
				as_dict=True,
			)
			if sr:
				for src, dst in (
					("customer", "customer"),
					("company", "company"),
					("branch", "branch"),
					("mobile_no", "mobile_no"),
					("email_id", "email_id"),
				):
					if not self.get(dst) and sr.get(src):
						self.set(dst, sr.get(src))
				if sr.contact_person and not self.contact_person:
					self.contact_person = frappe.db.get_value("Contact", sr.contact_person, "first_name") or sr.contact_person

		if self.customer and not self.customer_name:
			self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")

		if self.service_report and frappe.db.exists("Service Report", self.service_report):
			r = frappe.db.get_value(
				"Service Report",
				self.service_report,
				["engineer_visit", "primary_engineer", "repair_order", "customer", "service_request"],
				as_dict=True,
			)
			if r:
				if not self.service_request:
					self.service_request = r.service_request
				if not self.engineer_visit:
					self.engineer_visit = r.engineer_visit
				if not self.engineer:
					self.engineer = r.primary_engineer
				if not self.repair_order:
					self.repair_order = r.repair_order
				if not self.customer and r.customer:
					self.customer = r.customer

		if self.service_billing and frappe.db.exists("Service Billing", self.service_billing):
			b = frappe.db.get_value(
				"Service Billing",
				self.service_billing,
				["service_report", "service_request", "customer", "repair_order"],
				as_dict=True,
			)
			if b:
				if not self.service_report:
					self.service_report = b.service_report
				if not self.service_request:
					self.service_request = b.service_request
				if not self.customer:
					self.customer = b.customer
				if not self.repair_order:
					self.repair_order = b.repair_order

		if not self.engineer_visit and self.service_request:
			self.engineer_visit = frappe.db.get_value(
				"Engineer Visit",
				{"service_request": self.service_request, "docstatus": ["<", 2]},
				"name",
				order_by="modified desc",
			)
		if self.engineer_visit and not self.engineer:
			self.engineer = frappe.db.get_value("Engineer Visit", self.engineer_visit, "engineer")

		self._ensure_rating_template()
		return self

	def _assert_report_ready(self):
		if not self.service_report:
			# allow if any submitted/billing-ready report exists for SSR
			ok = frappe.db.exists(
				"Service Report",
				{
					"service_request": self.service_request,
					"status": ["in", ["Billing Ready", "Submitted", "Customer Signed", "Manager Verification"]],
					"docstatus": ["<", 2],
				},
			)
			if not ok:
				# soft: allow request even without report for call-center edge cases
				return
			return
		st = frappe.db.get_value("Service Report", self.service_report, "status")
		ds = frappe.db.get_value("Service Report", self.service_report, "docstatus")
		if cint(ds) == 2:
			frappe.throw(_("Cannot collect feedback for cancelled Service Report"))
		# window check
		created = frappe.db.get_value("Service Report", self.service_report, "creation")
		if created:
			age = (getdate() - getdate(created)).days
			if age > FEEDBACK_WINDOW_DAYS and self.status == "Draft":
				frappe.msgprint(
					_("Feedback window ({0} days) exceeded — proceeding as exception").format(FEEDBACK_WINDOW_DAYS),
					indicator="orange",
				)

	# —— workflow ——

	def request_feedback(self):
		self._assert_report_ready()
		self.status = "Feedback Requested"
		self._append_timeline(_("Feedback requested from customer"), self.channel or "")
		self.save(ignore_permissions=True)
		self._notify_request()
		return self

	def _notify_request(self):
		"""Best-effort notification — email if address available."""
		recipients = []
		if self.email_id:
			recipients.append(self.email_id)
		elif self.customer:
			email = frappe.db.get_value("Customer", self.customer, "email_id")
			if email:
				recipients.append(email)
		if not recipients:
			return
		try:
			frappe.sendmail(
				recipients=recipients,
				subject=_("We value your feedback — {0}").format(self.service_request),
				message=_(
					"Please rate your recent service for {0}. Feedback reference: {1}"
				).format(self.service_request, self.name),
				delayed=True,
			)
			self._append_timeline(_("Feedback request email queued"), ", ".join(recipients))
			self.db_update()
		except Exception:
			frappe.log_error(title="Customer Feedback request email failed")

	def submit_response(
		self,
		csat_rating=None,
		nps_score=None,
		issue_resolved=None,
		positive_feedback=None,
		complaint_text=None,
		suggestions=None,
		would_recommend_us=None,
		would_call_again=None,
		complaint_against_engineer=0,
		complaint_category=None,
		complaint_details=None,
		rating_details=None,
	):
		if csat_rating not in (None, ""):
			self.csat_rating = str(cint(csat_rating))
			self.rating = self.csat_rating
		if nps_score not in (None, ""):
			self.nps_score = cint(nps_score)
		if issue_resolved:
			self.issue_resolved = issue_resolved
		if positive_feedback:
			self.positive_feedback = positive_feedback
		if complaint_text:
			self.complaint_text = complaint_text
		if suggestions:
			self.suggestions = suggestions
		if would_recommend_us:
			self.would_recommend_us = would_recommend_us
		if would_call_again:
			self.would_call_again = would_call_again
		if cint(complaint_against_engineer):
			self.complaint_against_engineer = 1
			self.complaint_category = complaint_category or self.complaint_category
			self.complaint_details = complaint_details or self.complaint_details
		if rating_details:
			if isinstance(rating_details, str):
				rating_details = frappe.parse_json(rating_details)
			self.rating_details = []
			for row in rating_details:
				self.append("rating_details", row)

		# sync comments table
		for ctype, text in (
			("Positive", self.positive_feedback),
			("Complaint", self.complaint_text),
			("Suggestion", self.suggestions),
			("Improvement", self.improvement_ideas),
		):
			if (text or "").strip():
				self.append(
					"comment_rows",
					{
						"comment_type": ctype,
						"comment": text,
						"entered_by": self.customer_name or self.customer,
						"entered_on": now_datetime(),
					},
				)

		self.status = "Customer Responded"
		self._calc_nps_category()
		reasons = self._eval_escalation_flags()
		self._append_timeline(_("Customer responded"), "; ".join(reasons) if reasons else "")
		self.save(ignore_permissions=True)

		if cint(self.escalation_required):
			self.create_escalation(remarks="; ".join(reasons))
		return self

	def create_escalation(self, remarks=None):
		self.escalation_required = 1
		self.escalation_status = "Open"
		self.status = "Escalation"
		if remarks:
			self.escalation_remarks = remarks
		# Manager ToDo
		try:
			todo = frappe.get_doc(
				{
					"doctype": "ToDo",
					"description": _("Low CSAT/NPS escalation for {0} ({1})").format(
						self.service_request, self.name
					),
					"reference_type": "Customer Feedback",
					"reference_name": self.name,
					"priority": "High",
					"status": "Open",
					"allocated_to": self._service_manager(),
				}
			)
			todo.insert(ignore_permissions=True)
			self.escalation_task = todo.name
		except Exception:
			frappe.log_error(title="Customer Feedback escalation ToDo failed")
		self._append_timeline(_("Escalation created"), remarks or "")
		self.save(ignore_permissions=True)
		return self

	def _service_manager(self):
		users = frappe.get_all(
			"Has Role",
			filters={"role": "Service Manager", "parenttype": "User"},
			pluck="parent",
			limit=5,
		)
		for u in users:
			if u not in ("Administrator", "Guest"):
				return u
		return frappe.session.user

	def mark_reviewed(self, remarks=None):
		self.reviewed_by = frappe.session.user
		self.reviewed_on = now_datetime()
		if remarks:
			self.escalation_remarks = ((self.escalation_remarks or "") + "\n" + remarks).strip()
		if cint(self.escalation_required) and self.escalation_status == "Open":
			self.escalation_status = "In Progress"
		self.status = "Reviewed"
		self._append_timeline(_("Feedback reviewed"))
		self.save(ignore_permissions=True)
		return self

	def resolve_escalation(self, remarks=None):
		self.escalation_status = "Resolved"
		if remarks:
			self.escalation_remarks = ((self.escalation_remarks or "") + "\n" + remarks).strip()
		if self.escalation_task and frappe.db.exists("ToDo", self.escalation_task):
			try:
				frappe.db.set_value("ToDo", self.escalation_task, "status", "Closed")
			except Exception:
				pass
		self.status = "Reviewed"
		self._append_timeline(_("Escalation resolved"), remarks or "")
		self.save(ignore_permissions=True)
		return self

	def close_feedback(self):
		if cint(self.escalation_required) and self.escalation_status in ("Open", "In Progress"):
			frappe.throw(_("Resolve open escalation before closing feedback"))
		self.status = "Closed"
		self._append_timeline(_("Feedback closed — ready for Service Closure"))
		self.save(ignore_permissions=True)
		self._maybe_prepare_closure()
		return self

	def _maybe_prepare_closure(self):
		try:
			from swiftservice.swiftservice.doctype.service_closure.service_closure import generate_from_source

			generate_from_source(service_request=self.service_request, run_validation=True)
		except Exception:
			frappe.log_error(title="Auto Service Closure create failed")

	def create_revision(self):
		new = frappe.copy_doc(self)
		new.naming_series = self.naming_series or "FDBK-.YYYY.-.#####"
		new.revised_from = self.name
		new.revision = cint(self.revision) + 1
		new.status = "Draft"
		new.escalation_task = None
		new.reviewed_by = None
		new.reviewed_on = None
		new.feedback_timeline = []
		new.insert(ignore_permissions=True)
		new._append_timeline(_("Revision {0} from {1}").format(new.revision, self.name))
		new.save(ignore_permissions=True)
		return new

	def advance_status(self, status=None):
		cur = STATUS_ALIASES.get(self.status, self.status)
		if status:
			status = STATUS_ALIASES.get(status, status)
			helpers = {
				"Feedback Requested": self.request_feedback,
				"Customer Responded": lambda: self.submit_response(
					csat_rating=self.csat_rating or self.rating,
					nps_score=self.nps_score,
				),
				"Reviewed": self.mark_reviewed,
				"Escalation": self.create_escalation,
				"Closed": self.close_feedback,
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
			nxt = STATUS_ORDER[idx + 1]
			# skip Escalation in linear advance — only via rules
			return self.advance_status(nxt)
		return self


def generate_from_source(
	service_request=None,
	service_report=None,
	service_billing=None,
	repair_order=None,
	force=False,
	request=True,
):
	if not service_request and service_report:
		service_request = frappe.db.get_value("Service Report", service_report, "service_request")
	if not service_request and service_billing:
		service_request = frappe.db.get_value("Service Billing", service_billing, "service_request")
	if not service_request and repair_order:
		service_request = frappe.db.get_value("Repair Order", repair_order, "service_request")
	if not service_request:
		frappe.throw(_("service_request is required"))

	# one active feedback per service report
	if service_report and not force:
		existing = frappe.db.get_value(
			"Customer Feedback",
			{
				"service_report": service_report,
				"docstatus": ["<", 2],
				"status": ["not in", ["Cancelled", "Closed"]],
			},
			"name",
		)
		if existing:
			return frappe.get_doc("Customer Feedback", existing)

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

	if not service_billing:
		service_billing = frappe.db.get_value(
			"Service Billing",
			{"service_request": service_request, "docstatus": ["<", 2], "status": ["not in", ["Cancelled"]]},
			"name",
			order_by="modified desc",
		)

	doc = frappe.get_doc(
		{
			"doctype": "Customer Feedback",
			"naming_series": "FDBK-.YYYY.-.#####",
			"service_request": service_request,
			"service_report": service_report,
			"service_billing": service_billing,
			"repair_order": repair_order,
			"status": "Draft",
			"feedback_date": nowdate(),
			"revision": 1,
			"channel": "Portal",
		}
	)
	doc.populate_from_sources()
	doc.insert(ignore_permissions=True)
	if request:
		try:
			doc.request_feedback()
		except Exception:
			doc._append_timeline(_("Created in Draft — request when ready"))
			doc.save(ignore_permissions=True)
	return doc
