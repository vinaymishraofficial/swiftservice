import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, now_datetime


STATUS_ALIASES = {
	"Planned": "Scheduled",
	"Confirmed": "Scheduled",
	"Travel": "Travel Started",
	"In Progress": "GPS Check-In",
}

ALLOWED_TRANSITIONS = {
	"Draft": {"Scheduled", "Cancelled"},
	"Scheduled": {"Travel Started", "Draft", "Cancelled"},
	"Travel Started": {"Reached Site", "Scheduled", "Cancelled"},
	"Reached Site": {"GPS Check-In", "Travel Started", "Cancelled"},
	"GPS Check-In": {"Inspection", "Diagnosis", "Cancelled"},
	"Inspection": {"Diagnosis", "GPS Check-In", "Cancelled"},
	"Diagnosis": {"Repair", "Testing", "Completed", "Cancelled"},
	"Repair": {"Testing", "Diagnosis", "Cancelled"},
	"Testing": {"Customer Verification", "Repair", "Cancelled"},
	"Customer Verification": {"GPS Check-Out", "Testing", "Cancelled"},
	"GPS Check-Out": {"Completed", "Customer Verification", "Cancelled"},
	"Completed": set(),
	"Cancelled": set(),
	# legacy
	"Planned": {"Travel Started", "Scheduled", "Cancelled"},
	"Confirmed": {"Travel Started", "Scheduled", "Cancelled"},
	"Travel": {"Reached Site", "GPS Check-In", "Cancelled"},
	"In Progress": {"Inspection", "Diagnosis", "GPS Check-Out", "Completed", "Cancelled"},
}

CHECK_IN_RADIUS_M = 100


def _google_maps_api_key():
	try:
		return (
			frappe.db.get_single_value("SwiftService Settings", "google_maps_api_key")
			or ""
		).strip()
	except Exception:
		return ""


def reverse_geocode(lat, lng):
	"""Resolve lat/lng to a short address (Google preferred, OSM fallback)."""
	lat, lng = flt(lat), flt(lng)
	if abs(lat) < 0.00001 and abs(lng) < 0.00001:
		return ""
	try:
		import requests

		api_key = _google_maps_api_key()
		if api_key:
			res = requests.get(
				"https://maps.googleapis.com/maps/api/geocode/json",
				params={
					"latlng": f"{lat},{lng}",
					"key": api_key,
				},
				timeout=8,
			)
			if res.status_code == 200:
				payload = res.json() or {}
				if payload.get("status") == "OK" and (payload.get("results") or []):
					return ((payload.get("results") or [])[0].get("formatted_address") or "")[:500]

		res = requests.get(
			"https://nominatim.openstreetmap.org/reverse",
			params={
				"lat": lat,
				"lon": lng,
				"format": "json",
				"zoom": 18,
				"addressdetails": 1,
			},
			headers={"User-Agent": "SwiftService/1.0 (field-service GPS)"},
			timeout=8,
		)
		if res.status_code != 200:
			return ""
		data = res.json() or {}
		addr = data.get("address") or {}
		# Prefer a readable street-level line
		parts = [
			addr.get("road") or addr.get("pedestrian") or addr.get("neighbourhood"),
			addr.get("suburb") or addr.get("village") or addr.get("town") or addr.get("city"),
			addr.get("state"),
			addr.get("postcode"),
			addr.get("country"),
		]
		line = ", ".join([p for p in parts if p])
		return (line or data.get("display_name") or "")[:500]
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Engineer Visit reverse_geocode")
		return ""


def geocode_address(address):
	"""Forward-geocode a free-text address to (lat, lng, display_name)."""
	address = (address or "").strip()
	if not address or len(address) < 5:
		return None
	try:
		import requests

		api_key = _google_maps_api_key()
		if api_key:
			res = requests.get(
				"https://maps.googleapis.com/maps/api/geocode/json",
				params={
					"address": address,
					"key": api_key,
				},
				timeout=10,
			)
			if res.status_code == 200:
				payload = res.json() or {}
				if payload.get("status") == "OK" and (payload.get("results") or []):
					first = (payload.get("results") or [])[0]
					loc = (first.get("geometry") or {}).get("location") or {}
					lat, lng = flt(loc.get("lat")), flt(loc.get("lng"))
					if abs(lat) >= 0.00001 or abs(lng) >= 0.00001:
						return {
							"lat": lat,
							"lng": lng,
							"display_name": (first.get("formatted_address") or address)[:500],
						}

		res = requests.get(
			"https://nominatim.openstreetmap.org/search",
			params={
				"q": address,
				"format": "json",
				"limit": 1,
				"addressdetails": 1,
			},
			headers={"User-Agent": "SwiftService/1.0 (field-service GPS)"},
			timeout=10,
		)
		if res.status_code != 200:
			return None
		rows = res.json() or []
		if not rows:
			return None
		row = rows[0]
		lat, lng = flt(row.get("lat")), flt(row.get("lon"))
		if abs(lat) < 0.00001 and abs(lng) < 0.00001:
			return None
		return {
			"lat": lat,
			"lng": lng,
			"display_name": (row.get("display_name") or address)[:500],
		}
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Engineer Visit geocode_address")
		return None


def is_valid_geo(lat, lng):
	lat, lng = flt(lat), flt(lng)
	if abs(lat) < 0.00001 and abs(lng) < 0.00001:
		return False
	return -90 <= lat <= 90 and -180 <= lng <= 180


class EngineerVisit(Document):
	def validate(self):
		self._set_defaults()
		self._fetch_from_service_request()
		self._normalize_status()

	def before_submit(self):
		self._validate_before_submit()
		if self.status in (None, "", "Draft", "Scheduled", "Planned", "Confirmed"):
			self.status = "Completed"
		if not self.actual_completion:
			self.actual_completion = now_datetime()

	def on_submit(self):
		self._append_timeline(_("Visit submitted"))
		self._apply_diagnosis_outcomes()
		self._maybe_create_diagnosis()
		self._maybe_create_service_report()
		self._sync_parent_docs()

	def _maybe_create_service_report(self):
		"""Auto-generate report for field-complete outcomes (not workshop/replacement pipelines)."""
		try:
			skip = {"Spare Required", "Workshop Repair", "Replacement", "Customer Not Available"}
			if self.diagnosis_result in skip:
				return
			from swiftservice.swiftservice.doctype.service_report.service_report import generate_from_source

			generate_from_source(
				service_request=self.service_request,
				engineer_visit=self.name,
			)
		except Exception:
			frappe.log_error(title="Auto Service Report create failed")

	def _maybe_create_diagnosis(self):
		try:
			from swiftservice.swiftservice.doctype.failure_analysis.failure_analysis import (
				COMPLEX_OUTCOMES,
				create_from_visit,
			)

			if self.diagnosis_result in COMPLEX_OUTCOMES or cint(getattr(self, "next_visit_required", 0)):
				create_from_visit(self.name, force=True)
		except Exception:
			frappe.log_error(title="Auto Diagnosis create failed")

	def on_update_after_submit(self):
		if self.has_value_changed("status"):
			old = self.get_doc_before_save()
			if old:
				self._assert_transition(old.status, self.status)

	def on_cancel(self):
		self.db_set("status", "Cancelled", update_modified=True)

	def _set_defaults(self):
		if not self.visit_date:
			self.visit_date = getdate()
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)
		if not self.status:
			self.status = "Draft"
		if not self.naming_series:
			self.naming_series = "SV-.YYYY.-.#####"

	def _normalize_status(self):
		if self.status in STATUS_ALIASES and self.is_new():
			# keep legacy labels on existing rows; prefer canonical on new
			pass

	def _fetch_from_service_request(self):
		if not self.service_request:
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
				"batch_no",
				"company",
				"branch",
				"geo_latitude",
				"geo_longitude",
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
			("batch_no", "batch_no"),
			("company", "company"),
			("branch", "branch"),
		):
			if not self.get(dst) and sr.get(src):
				self.set(dst, sr.get(src))

	def _validate_before_submit(self):
		if not self.check_in_time and not self.gps_check_in:
			frappe.throw(_("GPS Check-In is required before submit"))
		if not self.check_out_time and not self.gps_check_out:
			frappe.throw(_("GPS Check-Out is required before submit"))
		if not self.diagnosis_result and not self.diagnosis_notes:
			frappe.throw(_("Diagnosis Result is required before submit"))
		if not self.work_done and not self.diagnosis_notes:
			frappe.throw(_("Work Done is required before submit"))
		if not self.customer_signature and not self.missing_signature_reason:
			frappe.throw(_("Customer Signature or Reason for Missing Signature is required"))

	def _assert_transition(self, old_status, new_status):
		if old_status == new_status:
			return
		allowed = ALLOWED_TRANSITIONS.get(old_status) or set()
		if new_status not in allowed and "System Manager" not in frappe.get_roles():
			frappe.throw(_("Cannot change visit status from {0} to {1}").format(old_status, new_status))

	def _append_timeline(self, activity, remarks=""):
		self.append(
			"visit_timeline",
			{
				"activity": activity,
				"user": frappe.session.user,
				"time": now_datetime(),
				"remarks": remarks,
			},
		)

	def check_in(self, lat=None, lng=None, accuracy=None, force=False):
		lat = flt(lat) if lat not in (None, "") else None
		lng = flt(lng) if lng not in (None, "") else None
		accuracy = flt(accuracy) if accuracy not in (None, "") else None
		# Ignore null-island / unset Float defaults
		if lat is not None and lng is not None and abs(lat) < 0.00001 and abs(lng) < 0.00001:
			lat = None
			lng = None

		distance = None
		if lat is not None and lng is not None and self.service_request:
			cust_lat = frappe.db.get_value("Swift Service Request", self.service_request, "geo_latitude")
			cust_lng = frappe.db.get_value("Swift Service Request", self.service_request, "geo_longitude")
			if cust_lat not in (None, "") and cust_lng not in (None, ""):
				distance = _haversine_m(flt(cust_lat), flt(cust_lng), lat, lng)
				self.distance_from_customer = distance
				if distance > CHECK_IN_RADIUS_M and not force and "System Manager" not in frappe.get_roles():
					frappe.throw(
						_(
							"Check-in is {0}m from customer (limit {1}m). Manager approval / force required."
						).format(int(distance), CHECK_IN_RADIUS_M)
					)

		self.check_in_time = now_datetime()
		self.actual_arrival = self.check_in_time
		if lat is not None:
			self.check_in_latitude = lat
		if lng is not None:
			self.check_in_longitude = lng
		if accuracy is not None:
			self.gps_accuracy = accuracy
		if lat is not None:
			self.gps_check_in = f"{lat},{lng}" if lng is not None else str(lat)
		if lat is not None and lng is not None:
			self.check_in_address = reverse_geocode(lat, lng) or self.check_in_address
		self.status = "GPS Check-In"
		self._append_timeline(_("GPS Check-In"), f"distance={distance}" if distance is not None else "")
		self._set_engineer_busy(True)
		self.save(ignore_permissions=True)
		self._sync_parent_docs()
		return self

	def check_out(self, lat=None, lng=None, diagnosis_notes=None):
		if not self.check_in_time and not self.gps_check_in:
			frappe.throw(_("Check-in required before check-out"))
		lat = flt(lat) if lat not in (None, "") else None
		lng = flt(lng) if lng not in (None, "") else None
		if lat is not None and lng is not None and abs(lat) < 0.00001 and abs(lng) < 0.00001:
			lat = None
			lng = None
		self.check_out_time = now_datetime()
		self.actual_completion = self.check_out_time
		if lat is not None:
			self.check_out_latitude = lat
		if lng is not None:
			self.check_out_longitude = lng
		if lat is not None:
			self.gps_check_out = f"{lat},{lng}" if lng is not None else str(lat)
		if lat is not None and lng is not None:
			self.check_out_address = reverse_geocode(lat, lng) or self.check_out_address
		if diagnosis_notes:
			self.diagnosis_notes = diagnosis_notes
		self.status = "GPS Check-Out"
		self._append_timeline(_("GPS Check-Out"))
		self._set_engineer_busy(False)
		self.save(ignore_permissions=True)
		self._sync_parent_docs()
		return self

	def _set_engineer_busy(self, busy):
		if not self.engineer:
			return
		profile = frappe.db.get_value("Engineer Profile", {"engineer": self.engineer}, "name")
		if not profile:
			return
		# workload bump soft signal; status stays Active unless On Leave
		try:
			doc = frappe.get_doc("Engineer Profile", profile)
			if busy:
				doc.workload = cint(doc.workload) + 1
			else:
				doc.workload = max(cint(doc.workload) - 1, 0)
			doc.save(ignore_permissions=True)
		except Exception:
			pass

	def _apply_diagnosis_outcomes(self):
		result = self.diagnosis_result
		if not result or not self.service_request:
			return
		# Soft stubs — create linked docs when helpers exist
		try:
			if result == "Spare Required" and not frappe.db.exists(
				"Spare Request", {"service_request": self.service_request, "docstatus": ["<", 2]}
			):
				# leave creation to API button; just mark SSR
				pass
			from swiftservice.api import update_diagnosis

			map_to_ssr = {
				"Fixed": "Issue Fixed",
				"Spare Required": "Spare Required",
				"Workshop Repair": "Factory Repair",
				"Replacement": "Replacement Required",
				"No Fault Found": "No Fault Found",
				"Software Issue": "Issue Fixed",
				"Calibration Needed": "Issue Fixed",
				"Customer Not Available": "Spare Required",
			}
			ssr_diag = map_to_ssr.get(result)
			if ssr_diag:
				update_diagnosis(
					self.service_request,
					ssr_diag,
					resolution_summary=self.work_done or self.observation or self.diagnosis_notes,
				)
		except Exception:
			frappe.log_error(title="Service Visit diagnosis outcome failed")

	def _sync_parent_docs(self):
		# SSR status
		if self.service_request and frappe.db.exists("Swift Service Request", self.service_request):
			sr = frappe.get_doc("Swift Service Request", self.service_request)
			changed = False
			status_map = {
				"Travel Started": "Travel Started",
				"Reached Site": "Reached Customer",
				"GPS Check-In": "Reached Customer",
				"Inspection": "Inspection",
				"Diagnosis": "Inspection",
				"Repair": "Repair In Progress",
				"Testing": "Testing",
				"Customer Verification": "Customer Verification",
				"GPS Check-Out": "Completed",
				"Completed": "Completed",
			}
			target = status_map.get(self.status)
			if target and sr.docstatus == 1 and sr.status != target:
				sr.status = target
				changed = True
			if self.check_in_time and not sr.actual_arrival:
				sr.actual_arrival = self.check_in_time
				changed = True
			if self.check_out_time:
				sr.actual_completion = self.check_out_time
				changed = True
			if changed:
				sr.flags.ignore_validate_update_after_submit = True
				sr.save(ignore_permissions=True)

		# Assignment
		if self.engineer_assignment and frappe.db.exists("Engineer Assignment", self.engineer_assignment):
			ea = frappe.get_doc("Engineer Assignment", self.engineer_assignment)
			amap = {
				"Travel Started": "Travel Started",
				"Reached Site": "Reached Customer",
				"GPS Check-In": "Reached Customer",
				"GPS Check-Out": "Visit Completed",
				"Completed": "Visit Completed",
			}
			target = amap.get(self.status)
			if target and ea.docstatus == 1 and ea.status != target:
				ea.status = target
				if self.check_in_time and not ea.arrival_time:
					ea.arrival_time = self.check_in_time
				if self.check_out_time:
					ea.completion_time = self.check_out_time
					ea.visit_status = "Completed"
				ea.save(ignore_permissions=True)


def _haversine_m(lat1, lon1, lat2, lon2):
	from math import asin, cos, radians, sin, sqrt

	r = 6371000
	dlat = radians(lat2 - lat1)
	dlon = radians(lon2 - lon1)
	a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
	return 2 * r * asin(sqrt(a))
