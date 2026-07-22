import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate


STATUS_ALIASES = {
	"Requested": "Pending Approval",
	"Received": "Received by Engineer",
	"Returned": "Closed",
}

ALLOWED_TRANSITIONS = {
	"Draft": {"Pending Approval", "Cancelled"},
	"Pending Approval": {"Approved", "Draft", "Cancelled"},
	"Approved": {"Stock Check", "Reserved", "Pending Purchase", "Cancelled"},
	"Stock Check": {"Reserved", "Pending Purchase", "Approved", "Cancelled"},
	"Reserved": {"Issued", "Pending Purchase", "Cancelled"},
	"Issued": {"In Transit", "Received by Engineer", "Consumed", "Cancelled"},
	"In Transit": {"Received by Engineer", "Issued", "Cancelled"},
	"Received by Engineer": {"Consumed", "Completed", "Cancelled"},
	"Consumed": {"Completed", "Closed"},
	"Completed": {"Closed"},
	"Closed": set(),
	"Cancelled": set(),
	"Pending Purchase": {"Reserved", "Approved", "Cancelled"},
	# legacy
	"Requested": {"Approved", "Cancelled"},
	"Received": {"Consumed", "Closed"},
	"Returned": set(),
}

RESERVATION_DAYS = 7


class SpareRequest(Document):
	def validate(self):
		self._set_defaults()
		self._fetch_from_links()
		self._sync_legacy_item_row()
		self._fetch_item_names()
		self._calc_totals()
		self._validate_qtys()

	def before_submit(self):
		if not self.requested_items and not self.item_code:
			frappe.throw(_("Add at least one requested part"))
		if self.status in (None, "", "Draft"):
			self.status = "Pending Approval"

	def on_submit(self):
		self._append_timeline(_("Spare Request submitted"))
		if self.status == "Pending Approval":
			pass
		self._sync_service_request()

	def on_cancel(self):
		self._release_reservations()
		self.status = "Cancelled"

	def on_update_after_submit(self):
		if self.has_value_changed("status"):
			old = self.get_doc_before_save()
			if old:
				self._assert_transition(old.status, self.status)

	def _set_defaults(self):
		if not self.naming_series:
			self.naming_series = "SPR-.YYYY.-.#####"
		if not self.status:
			self.status = "Draft"
		if not self.posting_date:
			self.posting_date = getdate()
		if not self.requested_by:
			self.requested_by = frappe.session.user
		if not self.requested_date:
			self.requested_date = now_datetime()
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)

	def _fetch_from_links(self):
		if self.service_request and frappe.db.exists("Swift Service Request", self.service_request):
			sr = frappe.db.get_value(
				"Swift Service Request",
				self.service_request,
				["customer", "installed_base", "item_code", "model_no", "serial_no", "company", "branch", "warranty_status"],
				as_dict=True,
			)
			if sr:
				for src, dst in (
					("customer", "customer"),
					("installed_base", "installed_base"),
					("model_no", "model_no"),
					("serial_no", "serial_no"),
					("company", "company"),
					("branch", "branch"),
					("warranty_status", "warranty_status"),
				):
					if not self.get(dst) and sr.get(src):
						self.set(dst, sr.get(src))

		if self.engineer_visit and frappe.db.exists("Engineer Visit", self.engineer_visit):
			v = frappe.db.get_value(
				"Engineer Visit",
				self.engineer_visit,
				["service_request", "engineer_assignment"],
				as_dict=True,
			)
			if v:
				if not self.service_request and v.service_request:
					self.service_request = v.service_request
				if not self.engineer_assignment and v.engineer_assignment:
					self.engineer_assignment = v.engineer_assignment

		if self.diagnosis and frappe.db.exists("Failure Analysis", self.diagnosis):
			d = frappe.db.get_value(
				"Failure Analysis",
				self.diagnosis,
				["service_request", "engineer_visit"],
				as_dict=True,
			)
			if d:
				if not self.service_request and d.service_request:
					self.service_request = d.service_request
				if not self.engineer_visit and d.engineer_visit:
					self.engineer_visit = d.engineer_visit

	def _sync_legacy_item_row(self):
		"""Keep legacy header item_code/qty in sync with first child row."""
		if self.item_code and not self.requested_items:
			self.append(
				"requested_items",
				{
					"item_code": self.item_code,
					"required_qty": flt(self.qty) or 1,
					"approved_qty": 0,
					"warehouse": self.warehouse,
					"stock_status": self.stock_status or "Unknown",
				},
			)
		elif self.requested_items and not self.item_code:
			row = self.requested_items[0]
			self.item_code = row.item_code
			self.qty = row.required_qty
			if row.warehouse:
				self.warehouse = row.warehouse

	def _fetch_item_names(self):
		for row in self.requested_items or []:
			if row.item_code and not row.item_name:
				row.item_name = frappe.db.get_value("Item", row.item_code, "item_name")
			if row.item_code and not row.uom:
				row.uom = frappe.db.get_value("Item", row.item_code, "stock_uom")

	def _calc_totals(self):
		est = 0
		act = 0
		for row in self.requested_items or []:
			est += flt(row.estimated_cost) * flt(row.required_qty)
			act += flt(row.actual_cost) * flt(row.issued_qty or row.consumed_qty)
		self.estimated_total = est
		self.actual_total = act

	def _validate_qtys(self):
		for row in self.requested_items or []:
			if flt(row.issued_qty) > flt(row.approved_qty or row.required_qty) + 0.0001:
				frappe.throw(_("Issued qty cannot exceed approved qty for {0}").format(row.item_code))
			if flt(row.consumed_qty) > flt(row.issued_qty) + 0.0001 and flt(row.issued_qty) > 0:
				frappe.throw(_("Consumed qty cannot exceed issued qty for {0}").format(row.item_code))
			if flt(row.returned_qty) > flt(row.issued_qty) - flt(row.consumed_qty) + 0.0001 and flt(row.issued_qty) > 0:
				frappe.throw(_("Return qty cannot exceed unused qty for {0}").format(row.item_code))

	def _assert_transition(self, old_status, new_status):
		if old_status == new_status:
			return
		allowed = ALLOWED_TRANSITIONS.get(old_status) or set()
		if new_status not in allowed and "System Manager" not in frappe.get_roles():
			frappe.throw(_("Cannot change spare status from {0} to {1}").format(old_status, new_status))

	def _append_timeline(self, activity, remarks=""):
		# When called after db_set, append needs save — use for in-memory ops
		self.append(
			"spare_timeline",
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
			if sr.docstatus == 1 and sr.status not in ("Completed", "Closed", "Cancelled"):
				if self.status in ("Pending Approval", "Approved", "Reserved", "Issued", "Pending Purchase"):
					if sr.status != "Waiting Spare":
						sr.status = "Waiting Spare"
						sr.flags.ignore_validate_update_after_submit = True
						sr.save(ignore_permissions=True)
		except Exception:
			pass

	def submit_for_approval(self):
		self.status = "Pending Approval"
		self._append_timeline(_("Submitted for approval"))
		self.save(ignore_permissions=True)
		return self

	def approve(self):
		self.status = "Approved"
		self.approver = frappe.session.user
		self.approved_on = now_datetime()
		self.reservation_expiry = add_days(getdate(), RESERVATION_DAYS)
		for row in self.requested_items or []:
			if not flt(row.approved_qty):
				row.approved_qty = flt(row.required_qty) or 1
		self._append_timeline(_("Approved"))
		self.save(ignore_permissions=True)
		self.check_and_reserve()
		return self

	def check_and_reserve(self):
		"""Stock availability check + soft reservation."""
		any_missing = False
		any_available = False
		for row in self.requested_items or []:
			need = flt(row.approved_qty or row.required_qty) or 1
			available = _get_available_qty(row.item_code, row.warehouse or self.warehouse)
			if available >= need:
				row.stock_status = "Available"
				row.reserved_qty = need
				any_available = True
			elif available > 0:
				row.stock_status = "Partial"
				row.reserved_qty = available
				any_available = True
				any_missing = True
			else:
				row.stock_status = "Not Available"
				row.reserved_qty = 0
				any_missing = True

		if any_missing and not any_available:
			self.stock_status = "Not Available"
			self.status = "Pending Purchase"
			self._append_timeline(_("No stock — purchase required"))
			self.save(ignore_permissions=True)
			self.create_purchase_request()
		elif any_missing:
			self.stock_status = "Partial"
			self.status = "Reserved"
			for row in self.requested_items or []:
				if flt(row.reserved_qty):
					row.stock_status = "Reserved" if row.stock_status != "Not Available" else row.stock_status
			self._append_timeline(_("Partial stock reserved"))
			self.save(ignore_permissions=True)
		else:
			self.stock_status = "Reserved"
			self.status = "Reserved"
			for row in self.requested_items or []:
				row.stock_status = "Reserved"
			self._append_timeline(_("Stock reserved"))
			self.save(ignore_permissions=True)
		self._sync_service_request()
		return self

	def create_purchase_request(self):
		if self.purchase_request:
			return self.purchase_request
		items = []
		for row in self.requested_items or []:
			need = flt(row.approved_qty or row.required_qty) - flt(row.reserved_qty)
			if need <= 0 and row.stock_status != "Not Available":
				continue
			qty = need if need > 0 else (flt(row.approved_qty or row.required_qty) or 1)
			items.append({"item_code": row.item_code, "qty": qty, "schedule_date": nowdate()})
		if not items and self.item_code:
			items.append({"item_code": self.item_code, "qty": flt(self.qty) or 1, "schedule_date": nowdate()})
		if not items:
			return None
		try:
			mr = frappe.new_doc("Material Request")
			mr.material_request_type = "Purchase"
			mr.schedule_date = nowdate()
			if self.company:
				mr.company = self.company
			for it in items:
				mr.append("items", it)
			mr.insert(ignore_permissions=True)
			self.purchase_request = mr.name
			self.status = "Pending Purchase"
			self._append_timeline(_("Material Request {0} created").format(mr.name))
			self.save(ignore_permissions=True)
			return mr.name
		except Exception:
			frappe.log_error(title="Spare Request MR create failed")
			return None

	def issue(self, warehouse=None, issue_source="Service Warehouse"):
		if self.status not in ("Reserved", "Approved", "Stock Check", "Pending Purchase", "Issued"):
			if self.status not in ("Issued", "In Transit"):
				frappe.throw(_("Reserve stock before issue (current: {0})").format(self.status))

		from swiftservice.erpnext_integration import create_material_issue, default_warehouse

		wh = warehouse or self.warehouse or default_warehouse(self.company)
		if not wh:
			frappe.throw(
				_("Set Primary Warehouse on Spare Request (or Default Service Warehouse in SwiftService Settings)")
			)
		self.warehouse = wh

		issue_lines = []
		for row in self.requested_items or []:
			to_issue = flt(row.approved_qty or row.required_qty) - flt(row.issued_qty)
			if to_issue <= 0:
				continue
			issue_qty = min(to_issue, flt(row.reserved_qty) or to_issue)
			if issue_qty <= 0:
				continue
			row_wh = row.warehouse or wh
			row.warehouse = row_wh
			row.issued_qty = flt(row.issued_qty) + issue_qty
			issue_lines.append(
				{
					"item_code": row.item_code,
					"qty": issue_qty,
					"warehouse": row_wh,
					"batch_no": row.batch_no,
					"serial_nos": row.serial_nos,
					"_row": row,
				}
			)

		if not issue_lines and self.item_code:
			qty = flt(self.qty) or 1
			issue_lines.append(
				{
					"item_code": self.item_code,
					"qty": qty,
					"warehouse": wh,
					"batch_no": None,
					"serial_nos": None,
					"_row": None,
				}
			)

		if not issue_lines:
			frappe.throw(_("Nothing left to issue"))

		se = create_material_issue(
			company=self.company,
			items=[{k: v for k, v in line.items() if k != "_row"} for line in issue_lines],
			from_warehouse=wh,
			remarks=_("Spare Request issue {0}").format(self.name),
			reference_doctype="Spare Request",
			reference_name=self.name,
		)

		for line in issue_lines:
			self.append(
				"issued_items",
				{
					"item_code": line["item_code"],
					"qty": line["qty"],
					"warehouse": line["warehouse"],
					"batch_no": line.get("batch_no"),
					"serial_nos": line.get("serial_nos"),
					"issue_source": issue_source,
					"issued_on": now_datetime(),
					"stock_entry": se.name,
				},
			)

		self.stock_entry = se.name
		self.status = "Issued"
		self.stock_status = "Available"
		self._append_timeline(
			_("Parts issued via Stock Entry {0} ({1}) from warehouse {2}").format(
				se.name, se.docstatus == 1 and _("Submitted") or _("Draft"), wh
			)
		)
		self.save(ignore_permissions=True)
		self._sync_service_request()
		return self

	def mark_received(self):
		self.status = "Received by Engineer"
		self._append_timeline(_("Engineer confirmed receipt"))
		self.save(ignore_permissions=True)
		return self

	def consume(self, items=None):
		"""items: list of {item_code, qty_used, ...} or consume all issued unused.
		Stock already left warehouse on Material Issue — this only records usage.
		"""
		if items:
			for it in items:
				self.append("consumed_items", it)
		else:
			for row in self.requested_items or []:
				unused = flt(row.issued_qty) - flt(row.consumed_qty) - flt(row.returned_qty)
				if unused <= 0:
					continue
				self.append(
					"consumed_items",
					{
						"item_code": row.item_code,
						"qty_used": unused,
						"engineer_visit": self.engineer_visit,
						"serial_nos": row.serial_nos,
						"reason": "Field consumption",
					},
				)
				row.consumed_qty = flt(row.consumed_qty) + unused

		for c in self.consumed_items or []:
			for row in self.requested_items or []:
				if row.item_code == c.item_code and flt(row.consumed_qty) < flt(c.qty_used):
					row.consumed_qty = flt(c.qty_used)

		self.status = "Consumed"
		self._append_timeline(
			_("Parts consumed (stock already issued from warehouse via {0})").format(
				self.stock_entry or _("Stock Entry")
			)
		)
		self._sync_visit_spare_used()
		self.save(ignore_permissions=True)
		return self

	def return_parts(self, items=None):
		"""Return unused issued parts → Material Receipt (inward) to warehouse."""
		from swiftservice.erpnext_integration import create_material_receipt, default_warehouse

		if items:
			for it in items:
				self.append("returned_items", it)

		return_lines = []
		for r in self.returned_items or []:
			for row in self.requested_items or []:
				if row.item_code == r.item_code:
					row.returned_qty = flt(row.returned_qty) + flt(r.qty)
			wh = getattr(r, "warehouse", None) or self.warehouse or default_warehouse(self.company)
			return_lines.append(
				{
					"item_code": r.item_code,
					"qty": flt(r.qty),
					"warehouse": wh,
					"batch_no": getattr(r, "batch_no", None),
					"serial_nos": getattr(r, "serial_nos", None),
				}
			)

		# Auto-build return from unused issued if no child rows yet
		if not return_lines:
			for row in self.requested_items or []:
				unused = flt(row.issued_qty) - flt(row.consumed_qty) - flt(row.returned_qty)
				if unused <= 0:
					continue
				wh = row.warehouse or self.warehouse or default_warehouse(self.company)
				self.append(
					"returned_items",
					{"item_code": row.item_code, "qty": unused, "warehouse": wh},
				)
				row.returned_qty = flt(row.returned_qty) + unused
				return_lines.append(
					{
						"item_code": row.item_code,
						"qty": unused,
						"warehouse": wh,
						"batch_no": row.batch_no,
						"serial_nos": row.serial_nos,
					}
				)

		receipt_name = None
		if return_lines:
			se = create_material_receipt(
				company=self.company,
				items=return_lines,
				to_warehouse=self.warehouse,
				remarks=_("Spare Request return {0}").format(self.name),
				reference_doctype="Spare Request",
				reference_name=self.name,
			)
			receipt_name = se.name
			self._append_timeline(
				_("Parts returned inward via Stock Entry {0} → warehouse").format(se.name)
			)
		else:
			self._append_timeline(_("Parts returned (no stock movement)"))

		done = True
		for row in self.requested_items or []:
			if flt(row.issued_qty) > flt(row.consumed_qty) + flt(row.returned_qty) + 0.0001:
				done = False
				break
		if done:
			self.status = "Completed"
		self.save(ignore_permissions=True)
		return self

	def complete(self):
		self.status = "Closed"
		self._append_timeline(_("Closed"))
		self.save(ignore_permissions=True)
		return self

	def advance_status(self, status=None):
		order = [
			"Draft",
			"Pending Approval",
			"Approved",
			"Stock Check",
			"Reserved",
			"Issued",
			"In Transit",
			"Received by Engineer",
			"Consumed",
			"Completed",
			"Closed",
		]
		cur = STATUS_ALIASES.get(self.status, self.status)
		if status:
			status = STATUS_ALIASES.get(status, status)
			self._assert_transition(self.status, status)
			self.status = status
			self._append_timeline(_("Status → {0}").format(status))
			self.save(ignore_permissions=True)
			return self
		if cur in order:
			idx = order.index(cur)
			if idx < len(order) - 1:
				nxt = order[idx + 1]
				if nxt == "Approved":
					return self.approve()
				if nxt == "Stock Check":
					return self.check_and_reserve()
				if nxt == "Reserved":
					return self.check_and_reserve()
				if nxt == "Issued":
					return self.issue()
				if nxt == "Received by Engineer":
					return self.mark_received()
				if nxt == "Consumed":
					return self.consume()
				if nxt == "Closed":
					return self.complete()
				self._assert_transition(self.status, nxt)
				self.status = nxt
				self._append_timeline(_("Status → {0}").format(nxt))
				self.save(ignore_permissions=True)
		return self

	def _release_reservations(self):
		for row in self.requested_items or []:
			row.reserved_qty = 0
			if row.stock_status == "Reserved":
				row.stock_status = "Available"

	def _sync_visit_spare_used(self):
		if not self.engineer_visit or not frappe.db.exists("Engineer Visit", self.engineer_visit):
			return
		try:
			visit = frappe.get_doc("Engineer Visit", self.engineer_visit)
			existing = {r.item_code for r in (visit.spare_used or [])}
			for c in self.consumed_items or []:
				if c.item_code in existing:
					continue
				visit.append(
					"spare_used",
					{
						"item_code": c.item_code,
						"qty": c.qty_used,
						"serial_no": (c.serial_nos or "").split("\n")[0] if c.serial_nos else None,
					},
				)
			visit.flags.ignore_validate_update_after_submit = True
			visit.save(ignore_permissions=True)
		except Exception:
			frappe.log_error(title="Spare consume → visit sync failed")


def _get_available_qty(item_code, warehouse=None):
	if not item_code:
		return 0
	try:
		from erpnext.stock.utils import get_stock_balance

		if warehouse:
			return flt(get_stock_balance(item_code, warehouse) or 0)
		bins = frappe.get_all(
			"Bin",
			filters={"item_code": item_code, "actual_qty": [">", 0]},
			fields=["actual_qty", "warehouse"],
			limit=20,
		)
		return sum(flt(b.actual_qty) for b in bins)
	except Exception:
		return 0
