import json
import math

import frappe
from frappe import _
from frappe.utils import cint, flt, get_url, now_datetime, nowdate


ALLOWED_DOCTYPES = {
	"Swift Service Request",
	"Installed Base",
	"Engineer Visit",
	"Engineer Assignment",
	"Spare Request",
	"RMA Case",
	"Replacement Case",
	"Preventive Maintenance Visit",
	"AMC Contract",
	"Calibration Certificate",
	"Repair Order",
	"Service Report",
	"Customer Feedback",
	"Failure Analysis",
	"SwiftService Settings",
	"Engineer Profile",
	"Van Inventory",
	"Knowledge Base Article",
	"Service Estimate",
	"Service Billing",
	"Service Closure",
}

SERVICE_REQUEST_STATUSES = [
	"Draft",
	"Open",
	"Under Validation",
	"Assigned",
	"Accepted",
	"Travel Started",
	"Reached Customer",
	"Reached Site",  # legacy
	"Inspection",
	"Waiting Customer",
	"Waiting Spare",
	"Repair In Progress",
	"Repair",  # legacy
	"Testing",
	"Customer Verification",
	"Customer Approval",  # legacy
	"Completed",
	"Closed",
	"Cancelled",
]

# Legacy / alias statuses → canonical (prefer new names)
STATUS_ALIASES = {
	"Spare Required": "Waiting Spare",
	"Factory Repair": "Repair In Progress",
	"Replacement Required": "Customer Verification",
	"In Progress": "Inspection",
	"Resolved": "Completed",
	"Reached Site": "Reached Customer",
	"Repair": "Repair In Progress",
	"Customer Approval": "Customer Verification",
}

# Allowed forward/side moves for API advance (superset used with controller)
STATUS_TRANSITIONS = {
	"Draft": ["Open", "Under Validation", "Cancelled"],
	"Open": ["Under Validation", "Assigned", "Cancelled"],
	"Under Validation": ["Assigned", "Open", "Cancelled"],
	"Assigned": ["Accepted", "Open", "Cancelled"],
	"Accepted": ["Travel Started", "Assigned", "Cancelled"],
	"Travel Started": ["Reached Customer", "Accepted", "Cancelled"],
	"Reached Customer": ["Inspection", "Waiting Customer", "Cancelled"],
	"Reached Site": ["Inspection", "Reached Customer", "Waiting Customer", "Cancelled"],
	"Inspection": [
		"Waiting Customer",
		"Waiting Spare",
		"Repair In Progress",
		"Testing",
		"Completed",
		"Cancelled",
	],
	"Waiting Customer": ["Inspection", "Travel Started", "Cancelled"],
	"Waiting Spare": ["Repair In Progress", "Inspection", "Cancelled"],
	"Repair In Progress": ["Testing", "Waiting Spare", "Completed", "Cancelled"],
	"Repair": ["Testing", "Repair In Progress", "Waiting Spare", "Completed", "Cancelled"],
	"Testing": ["Customer Verification", "Repair In Progress", "Cancelled"],
	"Customer Verification": ["Completed", "Testing", "Cancelled"],
	"Customer Approval": ["Completed", "Customer Verification", "Testing", "Cancelled"],
	"Completed": ["Closed"],
	"Closed": [],
	"Cancelled": [],
}


def _ensure_allowed(doctype):
	if doctype not in ALLOWED_DOCTYPES:
		frappe.throw(f"DocType {doctype} is not allowed in SwiftService SPA")


def _normalize_status(status):
	if not status:
		return status
	return STATUS_ALIASES.get(status, status)




def _user_image_url(path):
	if not path:
		return ""
	if path.startswith(("http://", "https://", "//")):
		return path
	return get_url(path)

def _normalize_service_request_doc(doc):
	"""Fix legacy invalid status values so SPA save/workflow work."""
	if getattr(doc, "doctype", None) == "Swift Service Request" and doc.status:
		normalized = _normalize_status(doc.status)
		if normalized != doc.status:
			doc.status = normalized
			# persist quietly when reading a broken record
			try:
				frappe.db.set_value(
					"Swift Service Request",
					doc.name,
					"status",
					normalized,
					update_modified=False,
				)
			except Exception:
				pass
	return doc


@frappe.whitelist()
def quick_create_link(doctype, title=None, values=None):
	"""Minimal create for SPA Link 'Create New' (CRM-style)."""
	_ensure_allowed_create(doctype)
	title = (title or "").strip()
	values = frappe.parse_json(values) if isinstance(values, str) else (values or {})
	if not title and not values:
		frappe.throw("Name is required")

	payload = {"doctype": doctype, **values}
	if doctype == "Customer":
		payload.setdefault("customer_name", title)
		payload.setdefault("customer_type", "Company")
	elif doctype == "Supplier":
		payload.setdefault("supplier_name", title)
		payload.setdefault("supplier_type", "Company")
	elif doctype == "Item":
		payload.setdefault("item_code", title)
		payload.setdefault("item_name", title)
		payload.setdefault("item_group", "All Item Groups")
		payload.setdefault("stock_uom", "Nos")
	elif doctype == "Contact":
		payload.setdefault("first_name", title)
	elif doctype == "Address":
		payload.setdefault("address_title", title)
		payload.setdefault("address_type", "Billing")
		payload.setdefault("address_line1", title)
		payload.setdefault("city", "—")
		payload.setdefault("country", frappe.db.get_default("country") or "India")
	elif doctype == "Lead":
		payload.setdefault("first_name", title)
		payload.setdefault("status", "Lead")
	else:
		meta = frappe.get_meta(doctype)
		if meta.title_field and title:
			payload.setdefault(meta.title_field, title)
		elif meta.autoname in (None, "", "Prompt") and title:
			payload.setdefault("name", title)
		elif title and meta.has_field("subject"):
			payload.setdefault("subject", title)

	doc = frappe.get_doc(payload)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	meta = frappe.get_meta(doctype)
	label = title
	if not label and meta.title_field:
		label = doc.get(meta.title_field)
	label = label or doc.name
	return {"value": doc.name, "label": label}


def _ensure_allowed_create(doctype):
	blocked = {"User", "Company", "DocType", "Role", "Currency"}
	if doctype in blocked:
		frappe.throw(f"Cannot create {doctype} from here")
	# Allow common masters + SwiftService doctypes
	if doctype in ALLOWED_DOCTYPES:
		return
	ok = {
		"Customer",
		"Supplier",
		"Item",
		"Contact",
		"Address",
		"Lead",
		"Warehouse",
		"Batch",
		"Serial No",
		"Employee",
		"Project",
		"Territory",
		"Brand",
		"Item Group",
	}
	if doctype not in ok:
		frappe.throw(f"Create New is not enabled for {doctype}")


@frappe.whitelist()
def search_link(doctype, txt="", filters=None, limit=20):
	"""ERPNext-compatible link search for SPA pickers (Customer, Item, User, …)."""
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	txt = (txt or "").strip()
	limit = cint(limit) or 20

	# Prefer Frappe's standard link search (same as Desk Link fields)
	try:
		from frappe.desk.search import search_link as desk_search_link

		results = desk_search_link(
			doctype=doctype,
			txt=txt or "",
			filters=filters or None,
			page_length=limit,
			ignore_user_permissions=True,
		)
		out = []
		for r in results or []:
			value = r.get("value") or r.get("name")
			if not value:
				continue
			desc = (r.get("description") or "").strip()
			label = r.get("label") or value
			if desc and desc != value and label == value:
				short = desc.split(",")[0].strip()
				label = f"{short} ({value})" if short and short != value else value
			out.append({"value": value, "label": label})
		if out:
			return out
		# empty txt with no results — fall through to recent records
		if txt:
			return out
	except Exception:
		frappe.log_error(title="SwiftService search_link desk fallback")

	# Fallback: direct query with title / common name fields
	meta = frappe.get_meta(doctype)
	title_field = meta.get("title_field") or "name"
	search_fields = ["name"]
	for f in (
		title_field,
		"customer_name",
		"item_name",
		"item_code",
		"full_name",
		"email",
		"user_name",
		"supplier_name",
		"employee_name",
		"serial_no",
		"warehouse_name",
	):
		if f and f not in search_fields and (f == "name" or meta.has_field(f)):
			search_fields.append(f)

	or_filters = []
	if txt:
		for f in search_fields:
			or_filters.append([doctype, f, "like", f"%{txt}%"])

	fields = list({*search_fields[:5]})
	rows = frappe.get_all(
		doctype,
		filters=filters or None,
		or_filters=or_filters or None,
		fields=fields,
		limit_page_length=limit,
		order_by="modified desc",
		ignore_permissions=True,
	)
	out = []
	for r in rows:
		label = None
		for f in search_fields:
			if r.get(f):
				label = r.get(f)
				break
		label = label or r.name
		out.append(
			{
				"value": r.name,
				"label": label if label == r.name else f"{label} ({r.name})",
			}
		)
	return out


@frappe.whitelist()
def ensure_demo_masters():
	"""Create a few Customers/Items/Serials if site has none — so Link pickers are usable."""
	created = {"customers": [], "items": [], "serials": [], "engineers": []}
	if frappe.db.count("Customer") == 0:
		customer_group = (
			frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
			or frappe.db.get_value("Customer Group", {}, "name")
		)
		territory = (
			frappe.db.get_value("Territory", {"is_group": 0}, "name")
			or frappe.db.get_value("Territory", {}, "name")
		)
		for name in ("Acme Medical Pvt Ltd", "Horizon Industries", "Swift Demo Customer"):
			if not frappe.db.exists("Customer", {"customer_name": name}):
				doc = frappe.get_doc(
					{
						"doctype": "Customer",
						"customer_name": name,
						"customer_type": "Company",
						"customer_group": customer_group,
						"territory": territory,
					}
				)
				doc.insert(ignore_permissions=True)
				created["customers"].append(doc.name)
	if frappe.db.count("Item") < 2:
		item_group = (
			frappe.db.get_value("Item Group", {"is_group": 0}, "name")
			or frappe.db.get_value("Item Group", {}, "name")
			or "All Item Groups"
		)
		for code, item_name, stock in (
			("SVC-LABOUR", "Service Labour", 0),
			("SPARE-DEMO-01", "Demo Spare Part", 1),
			("MACHINE-DEMO-01", "Demo Machine", 1),
		):
			if not frappe.db.exists("Item", code):
				doc = frappe.get_doc(
					{
						"doctype": "Item",
						"item_code": code,
						"item_name": item_name,
						"item_group": item_group,
						"stock_uom": "Nos",
						"is_stock_item": stock,
						"is_sales_item": 1,
						"has_serial_no": 1 if code == "MACHINE-DEMO-01" else 0,
					}
				)
				doc.insert(ignore_permissions=True)
				created["items"].append(doc.name)

	# Demo serial numbers for machine item
	if frappe.db.exists("Item", "MACHINE-DEMO-01") and frappe.db.count("Serial No") == 0:
		for sn in ("SN-DEMO-0001", "SN-DEMO-0002", "SN-DEMO-0003"):
			if not frappe.db.exists("Serial No", sn):
				try:
					doc = frappe.get_doc(
						{
							"doctype": "Serial No",
							"serial_no": sn,
							"item_code": "MACHINE-DEMO-01",
						}
					)
					doc.insert(ignore_permissions=True)
					created["serials"].append(doc.name)
				except Exception:
					frappe.log_error(title="SwiftService serial seed skipped")

	# Engineer profile for Administrator
	if frappe.db.exists("DocType", "Engineer Profile") and not frappe.db.exists(
		"Engineer Profile", "Administrator"
	):
		territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "India"
		try:
			doc = frappe.get_doc(
				{
					"doctype": "Engineer Profile",
					"engineer": "Administrator",
					"full_name": "Administrator",
					"region": territory,
					"status": "Active",
				}
			)
			doc.insert(ignore_permissions=True)
			created["engineers"].append(doc.name)
		except Exception:
			pass

	frappe.db.commit()
	return created


@frappe.whitelist()
def get_workflow_actions(doctype, name):
	"""Return ERPNext Workflow transitions for SPA (approvals configured in Desk)."""
	_ensure_allowed(doctype)
	from frappe.model.workflow import get_transitions, get_workflow, get_workflow_name

	doc = frappe.get_doc(doctype, name)
	wf_name = get_workflow_name(doctype)
	if not wf_name:
		return {
			"has_workflow": False,
			"transitions": [],
			"workflow_state": None,
			"docstatus": doc.docstatus,
			"is_submittable": cint(frappe.get_meta(doctype).is_submittable),
		}

	workflow = get_workflow(doctype)
	state_field = workflow.workflow_state_field
	transitions = []
	try:
		for t in get_transitions(doc, workflow=workflow) or []:
			transitions.append(
				{
					"action": t.get("action"),
					"next_state": t.get("next_state"),
					"allowed": t.get("allowed"),
				}
			)
	except Exception as e:
		frappe.log_error(title="SwiftService get_workflow_actions")
		return {
			"has_workflow": True,
			"transitions": [],
			"workflow_state": doc.get(state_field),
			"docstatus": doc.docstatus,
			"is_submittable": cint(frappe.get_meta(doctype).is_submittable),
			"error": str(e),
		}

	return {
		"has_workflow": True,
		"workflow_name": wf_name,
		"workflow_state": doc.get(state_field),
		"state_field": state_field,
		"transitions": transitions,
		"docstatus": doc.docstatus,
		"is_submittable": cint(frappe.get_meta(doctype).is_submittable),
	}


@frappe.whitelist()
def apply_workflow_action(doctype, name, action):
	"""Apply an ERPNext Workflow action (Approve / Reject / etc.)."""
	_ensure_allowed(doctype)
	from frappe.model.workflow import apply_workflow

	doc = frappe.get_doc(doctype, name)
	apply_workflow(doc, action)
	frappe.db.commit()
	return frappe.get_doc(doctype, name).as_dict()


@frappe.whitelist()
def get_doctype_list_meta(doctype):
	"""DocType-driven list columns, standard filters, naming & submit flags for SPA."""
	_ensure_allowed(doctype)
	meta = frappe.get_meta(doctype)
	list_fields = []
	standard_filters = []
	form_hint_fields = []

	for df in meta.fields:
		if df.fieldtype in (
			"Section Break",
			"Column Break",
			"Tab Break",
			"Fold",
			"Heading",
			"HTML",
			"Button",
			"Table",
			"Table MultiSelect",
		):
			continue
		info = {
			"fieldname": df.fieldname,
			"label": df.label or df.fieldname,
			"fieldtype": df.fieldtype,
			"options": df.options or "",
			"reqd": cint(df.reqd),
			"read_only": cint(df.read_only),
			"allow_on_submit": cint(df.allow_on_submit),
			"in_list_view": cint(df.in_list_view),
			"in_standard_filter": cint(df.in_standard_filter),
			"in_filter": cint(df.in_filter),
		}
		if df.fieldtype == "Select" and df.options:
			info["select_options"] = [
				{"label": o, "value": o} for o in df.options.split("\n") if o
			]
		if cint(df.in_list_view):
			list_fields.append(info)
		if cint(df.in_standard_filter) or cint(df.in_filter):
			standard_filters.append(info)
		if df.fieldname == "naming_series" or df.fieldtype in (
			"Link",
			"Select",
			"Date",
			"Datetime",
			"Data",
			"Check",
			"Int",
			"Float",
			"Currency",
			"Text",
			"Small Text",
		):
			form_hint_fields.append(info)

	# Always expose ID column first
	columns = [{"key": "name", "label": "ID", "width": "11rem", "fieldtype": "Data"}]
	for f in list_fields:
		if f["fieldname"] == "name":
			continue
		columns.append(
			{
				"key": f["fieldname"],
				"label": f["label"],
				"width": "12rem",
				"fieldtype": f["fieldtype"],
			}
		)
	# Fallback if DocType has no in_list_view flags
	if len(columns) == 1:
		for f in meta.fields:
			if f.fieldtype in ("Link", "Data", "Select", "Date", "Dynamic Link") and f.fieldname not in (
				"naming_series",
				"amended_from",
			):
				columns.append(
					{
						"key": f.fieldname,
						"label": f.label or f.fieldname,
						"width": "12rem",
						"fieldtype": f.fieldtype,
					}
				)
				if len(columns) >= 6:
					break
		columns.append({"key": "modified", "label": "Modified", "width": "10rem", "fieldtype": "Datetime"})

	quick_filters = []
	for f in standard_filters:
		qf = {
			"fieldname": f["fieldname"],
			"label": f["label"],
			"type": f["fieldtype"],
			"options": f.get("options") or "",
		}
		if f["fieldtype"] == "Select":
			qf["options"] = f.get("select_options") or []
		quick_filters.append(qf)

	naming_series_options = []
	ns = meta.get_field("naming_series")
	if ns and ns.options:
		naming_series_options = [o for o in ns.options.split("\n") if o]

	# Always expose ID + docstatus
	fields_out = ["name", "docstatus", "modified"]
	for c in columns:
		if c["key"] not in fields_out:
			fields_out.append(c["key"])

	field_flags = {}
	for df in meta.fields:
		if df.fieldtype in (
			"Section Break",
			"Column Break",
			"Tab Break",
			"Fold",
			"Heading",
			"HTML",
			"Button",
		):
			continue
		field_flags[df.fieldname] = {
			"read_only": cint(df.read_only),
			"allow_on_submit": cint(df.allow_on_submit),
			"reqd": cint(df.reqd),
		}

	# All filterable / listable fields for Columns + Customize Quick Filters pickers
	all_fields = []
	for df in meta.fields:
		if df.fieldtype in (
			"Section Break",
			"Column Break",
			"Tab Break",
			"Fold",
			"Heading",
			"HTML",
			"Button",
			"Table",
			"Table MultiSelect",
			"Attach",
			"Attach Image",
			"Image",
			"Signature",
			"Color",
			"Geolocation",
			"Password",
		):
			continue
		row = {
			"label": df.label or df.fieldname,
			"value": df.fieldname,
			"fieldname": df.fieldname,
			"fieldtype": df.fieldtype,
			"options": df.options or "",
		}
		if df.fieldtype == "Select" and df.options:
			row["select_options"] = [
				{"label": o, "value": o} for o in df.options.split("\n") if o
			]
		all_fields.append(row)
	# Standard system fields always available
	for std in (
		{"label": "ID", "value": "name", "fieldname": "name", "fieldtype": "Data", "options": ""},
		{
			"label": "Modified",
			"value": "modified",
			"fieldname": "modified",
			"fieldtype": "Datetime",
			"options": "",
		},
		{
			"label": "Created",
			"value": "creation",
			"fieldname": "creation",
			"fieldtype": "Datetime",
			"options": "",
		},
		{
			"label": "Owner",
			"value": "owner",
			"fieldname": "owner",
			"fieldtype": "Link",
			"options": "User",
		},
	):
		if not any(f["value"] == std["value"] for f in all_fields):
			all_fields.insert(0 if std["value"] == "name" else len(all_fields), std)

	return {
		"doctype": doctype,
		"autoname": meta.autoname or "",
		"title_field": meta.title_field or "name",
		"is_submittable": cint(meta.is_submittable),
		"is_tree": cint(getattr(meta, "is_tree", 0)),
		"sort_field": meta.sort_field or "modified",
		"sort_order": (meta.sort_order or "DESC").lower(),
		"columns": columns,
		"quick_filters": quick_filters,
		"all_fields": all_fields,
		"fields": fields_out,
		"field_flags": field_flags,
		"naming_series_options": naming_series_options,
		"has_naming_series": bool(ns),
	}


def _find_amendment(doctype, cancelled_name):
	"""Return latest non-cancelled amendment of a cancelled document, if any."""
	if not cancelled_name or not frappe.db.exists(doctype, cancelled_name):
		return None
	if cint(frappe.db.get_value(doctype, cancelled_name, "docstatus")) != 2:
		return None
	meta = frappe.get_meta(doctype)
	if not meta.get_field("amended_from"):
		return None
	rows = frappe.get_all(
		doctype,
		filters={"amended_from": cancelled_name, "docstatus": ["<", 2]},
		fields=["name", "docstatus", "modified"],
		order_by="modified desc",
		limit_page_length=1,
	)
	return rows[0].name if rows else None


def _resolve_active_link(doctype, name):
	"""If name is cancelled and an amendment exists, return amendment name."""
	if not name:
		return name
	if not frappe.db.exists(doctype, name):
		return name
	if cint(frappe.db.get_value(doctype, name, "docstatus")) != 2:
		return name
	return _find_amendment(doctype, name) or name


def _remap_cancelled_links(doc):
	"""Point Link fields away from cancelled docs onto their amendments when available."""
	changed = []
	for df in doc.meta.get_link_fields():
		val = doc.get(df.fieldname)
		if not val or not df.options:
			continue
		if not frappe.db.exists("DocType", df.options):
			continue
		if not frappe.get_meta(df.options).is_submittable:
			continue
		if cint(frappe.db.get_value(df.options, val, "docstatus")) != 2:
			continue
		active = _find_amendment(df.options, val)
		if active and active != val:
			doc.set(df.fieldname, active)
			changed.append(f"{df.label or df.fieldname}: {val} → {active}")
	return changed


def _count_outbound_links(doctype, name):
	"""Count docs that still link to this document (for cancel warning)."""
	CONN = {
		"Swift Service Request": [
			("Engineer Assignment", "service_request"),
			("Engineer Visit", "service_request"),
			("Failure Analysis", "service_request"),
			("Spare Request", "service_request"),
			("RMA Case", "service_request"),
			("Replacement Case", "service_request"),
			("Repair Order", "service_request"),
			("Service Estimate", "service_request"),
			("Service Billing", "service_request"),
			("Service Report", "service_request"),
			("Customer Feedback", "service_request"),
		],
		"Engineer Assignment": [
			("Engineer Visit", "engineer_assignment"),
		],
		"Engineer Visit": [
			("Failure Analysis", "engineer_visit"),
			("Spare Request", "engineer_visit"),
			("Repair Order", "engineer_visit"),
			("Service Report", "engineer_visit"),
		],
		"Repair Order": [
			("Spare Request", "repair_order"),
		],
	}
	total = 0
	details = []
	for linked_dt, fieldname in CONN.get(doctype, []):
		if not frappe.db.exists("DocType", linked_dt):
			continue
		n = frappe.db.count(linked_dt, {fieldname: name})
		if n:
			total += n
			details.append({"doctype": linked_dt, "count": n})
	return {"total": total, "details": details}


@frappe.whitelist()
def get_cancel_impact(doctype, name):
	_ensure_allowed(doctype)
	return _count_outbound_links(doctype, name)


@frappe.whitelist()
def amend_doc(doctype, name):
	"""Create amended document from a cancelled one (Desk Amend)."""
	_ensure_allowed(doctype)
	source = frappe.get_doc(doctype, name)
	if source.docstatus != 2:
		frappe.throw("Only cancelled documents can be amended")
	# Reuse existing open amendment if present
	existing = _find_amendment(doctype, name)
	if existing:
		return frappe.get_doc(doctype, existing).as_dict()

	amended = frappe.copy_doc(source)
	amended.docstatus = 0
	if amended.meta.get_field("amended_from"):
		amended.amended_from = source.name
	if amended.meta.get_field("status") and amended.status in (None, "", "Cancelled"):
		# restore a sensible draft/open status
		if doctype == "Swift Service Request":
			amended.status = "Open"
		elif doctype == "Engineer Assignment":
			amended.status = "Draft"
	amended.name = None
	amended.insert(ignore_permissions=True)
	frappe.db.commit()
	return amended.as_dict()


@frappe.whitelist()
def bulk_delete(doctype, names):
	_ensure_allowed(doctype)
	names = frappe.parse_json(names) if isinstance(names, str) else names
	deleted = []
	errors = []
	for name in names or []:
		try:
			doc = frappe.get_doc(doctype, name)
			if cint(doc.docstatus) == 1:
				errors.append(f"{name}: submitted — cancel first")
				continue
			doc.delete(ignore_permissions=True)
			deleted.append(name)
		except Exception as e:
			errors.append(f"{name}: {e}")
	frappe.db.commit()
	return {"deleted": deleted, "errors": errors}


@frappe.whitelist()
def bulk_assign(doctype, names, users):
	_ensure_allowed(doctype)
	names = frappe.parse_json(names) if isinstance(names, str) else names
	users = frappe.parse_json(users) if isinstance(users, str) else users
	from frappe.desk.form.assign_to import add

	if isinstance(users, str):
		users = [users]
	assigned = []
	for name in names or []:
		add(
			{
				"assign_to": users,
				"doctype": doctype,
				"name": name,
				"description": f"Bulk assigned via SwiftService",
				"notify": 1,
			}
		)
		assigned.append(name)
	return {"assigned": assigned}


@frappe.whitelist()
def submit_doc(doctype, name):
	_ensure_allowed(doctype)
	doc = frappe.get_doc(doctype, name)
	doc.submit()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def cancel_doc(doctype, name, force=0):
	_ensure_allowed(doctype)
	doc = frappe.get_doc(doctype, name)
	impact = _count_outbound_links(doctype, name)
	if impact["total"] and not cint(force):
		frappe.throw(
			(
				"This document has {0} linked record(s). "
				"Cancel or retarget those first, or pass force=1 to cancel anyway. "
				"Links: {1}"
			).format(
				impact["total"],
				", ".join(f"{d['doctype']} ({d['count']})" for d in impact["details"]),
			)
		)
	doc.cancel()
	# Keep ops status in sync when field exists
	if doc.meta.get_field("status") and hasattr(doc, "status"):
		try:
			doc.db_set("status", "Cancelled", update_modified=False)
		except Exception:
			pass
	frappe.db.commit()
	out = doc.as_dict()
	out["_link_impact"] = impact
	return out


@frappe.whitelist()
def get_connections(doctype, name):
	"""Desk-like Connections: linked docs with counts for SPA detail page."""
	_ensure_allowed(doctype)
	if not frappe.db.exists(doctype, name):
		frappe.throw(f"{doctype} {name} not found")

	# connection map: parent doctype -> list of {doctype, fieldname, label, route}
	CONN = {
		"Swift Service Request": [
			{"doctype": "Engineer Assignment", "fieldname": "service_request", "label": "Engineer Assignments", "route": "engineer-assignments"},
			{"doctype": "Engineer Visit", "fieldname": "service_request", "label": "Service Visits", "route": "engineer-visits"},
			{"doctype": "Failure Analysis", "fieldname": "service_request", "label": "Diagnosis / RCA", "route": "diagnoses"},
			{"doctype": "Spare Request", "fieldname": "service_request", "label": "Spare Requests", "route": "spare-requests"},
			{"doctype": "RMA Case", "fieldname": "service_request", "label": "RMA", "route": "rma"},
			{"doctype": "Replacement Case", "fieldname": "service_request", "label": "Replacements", "route": "replacements"},
			{"doctype": "Repair Order", "fieldname": "service_request", "label": "Repair Orders", "route": "repair-orders"},
			{"doctype": "Service Estimate", "fieldname": "service_request", "label": "Estimates", "route": "estimates"},
			{"doctype": "Service Billing", "fieldname": "service_request", "label": "Billing", "route": "billing"},
			{"doctype": "Service Report", "fieldname": "service_request", "label": "Service Reports", "route": "service-reports"},
			{"doctype": "Customer Feedback", "fieldname": "service_request", "label": "Feedback", "route": "feedback"},
			{"doctype": "Service Closure", "fieldname": "service_request", "label": "Service Closure", "route": "service-closures"},
		],
		"Installed Base": [
			{"doctype": "Swift Service Request", "fieldname": "installed_base", "label": "Service Requests", "route": "service-requests"},
			{"doctype": "Preventive Maintenance Visit", "fieldname": "installed_base", "label": "PM Visits", "route": "pm-visits"},
			{"doctype": "AMC Contract", "fieldname": "installed_base", "label": "AMC Contracts", "route": "amc-contracts"},
			{"doctype": "Calibration Certificate", "fieldname": "installed_base", "label": "Calibrations", "route": "calibrations"},
		],
		"Engineer Assignment": [
			{"doctype": "Engineer Visit", "fieldname": "engineer_assignment", "label": "Service Visits", "route": "engineer-visits"},
			{"doctype": "Swift Service Request", "fieldname": "name", "label": "Service Request", "route": "service-requests", "link_field": "service_request"},
		],
		"Engineer Visit": [
			{"doctype": "Failure Analysis", "fieldname": "engineer_visit", "label": "Diagnosis / RCA", "route": "diagnoses"},
			{"doctype": "Spare Request", "fieldname": "engineer_visit", "label": "Spare Requests", "route": "spare-requests"},
			{"doctype": "Repair Order", "fieldname": "engineer_visit", "label": "Repair Orders", "route": "repair-orders"},
			{"doctype": "Service Report", "fieldname": "engineer_visit", "label": "Service Reports", "route": "service-reports"},
			{"doctype": "Engineer Assignment", "fieldname": "name", "label": "Assignment", "route": "engineer-assignments", "link_field": "engineer_assignment"},
		],
		"Failure Analysis": [
			{"doctype": "Swift Service Request", "fieldname": "name", "label": "Service Request", "route": "service-requests", "link_field": "service_request"},
			{"doctype": "Engineer Visit", "fieldname": "name", "label": "Service Visit", "route": "engineer-visits", "link_field": "engineer_visit"},
			{"doctype": "Spare Request", "fieldname": "diagnosis", "label": "Spare Requests", "route": "spare-requests"},
			{"doctype": "Repair Order", "fieldname": "diagnosis", "label": "Repair Orders", "route": "repair-orders"},
		],
		"Spare Request": [
			{"doctype": "Swift Service Request", "fieldname": "name", "label": "Service Request", "route": "service-requests", "link_field": "service_request"},
			{"doctype": "Engineer Visit", "fieldname": "name", "label": "Service Visit", "route": "engineer-visits", "link_field": "engineer_visit"},
			{"doctype": "Failure Analysis", "fieldname": "name", "label": "Diagnosis", "route": "diagnoses", "link_field": "diagnosis"},
			{"doctype": "Repair Order", "fieldname": "name", "label": "Repair Order", "route": "repair-orders", "link_field": "repair_order"},
		],
		"Repair Order": [
			{"doctype": "Swift Service Request", "fieldname": "name", "label": "Service Request", "route": "service-requests", "link_field": "service_request"},
			{"doctype": "Engineer Visit", "fieldname": "name", "label": "Service Visit", "route": "engineer-visits", "link_field": "engineer_visit"},
			{"doctype": "Failure Analysis", "fieldname": "name", "label": "Diagnosis", "route": "diagnoses", "link_field": "diagnosis"},
			{"doctype": "Spare Request", "fieldname": "repair_order", "label": "Spare Requests", "route": "spare-requests"},
			{"doctype": "Service Report", "fieldname": "repair_order", "label": "Service Reports", "route": "service-reports"},
		],
		"Service Report": [
			{"doctype": "Swift Service Request", "fieldname": "name", "label": "Service Request", "route": "service-requests", "link_field": "service_request"},
			{"doctype": "Engineer Visit", "fieldname": "name", "label": "Service Visit", "route": "engineer-visits", "link_field": "engineer_visit"},
			{"doctype": "Repair Order", "fieldname": "name", "label": "Repair Order", "route": "repair-orders", "link_field": "repair_order"},
			{"doctype": "Service Billing", "fieldname": "service_report", "label": "Billing", "route": "billing"},
			{"doctype": "Customer Feedback", "fieldname": "service_report", "label": "Feedback", "route": "feedback"},
			{"doctype": "Service Estimate", "fieldname": "service_request", "label": "Estimates / Billing", "route": "estimates"},
			{"doctype": "Service Closure", "fieldname": "service_report", "label": "Service Closure", "route": "service-closures"},
		],
		"Service Billing": [
			{"doctype": "Swift Service Request", "fieldname": "name", "label": "Service Request", "route": "service-requests", "link_field": "service_request"},
			{"doctype": "Service Report", "fieldname": "name", "label": "Service Report", "route": "service-reports", "link_field": "service_report"},
			{"doctype": "Repair Order", "fieldname": "name", "label": "Repair Order", "route": "repair-orders", "link_field": "repair_order"},
			{"doctype": "Customer Feedback", "fieldname": "service_billing", "label": "Feedback", "route": "feedback"},
			{"doctype": "Service Closure", "fieldname": "service_billing", "label": "Service Closure", "route": "service-closures"},
		],
		"Customer Feedback": [
			{"doctype": "Swift Service Request", "fieldname": "name", "label": "Service Request", "route": "service-requests", "link_field": "service_request"},
			{"doctype": "Service Report", "fieldname": "name", "label": "Service Report", "route": "service-reports", "link_field": "service_report"},
			{"doctype": "Service Billing", "fieldname": "name", "label": "Billing", "route": "billing", "link_field": "service_billing"},
			{"doctype": "Engineer Visit", "fieldname": "name", "label": "Service Visit", "route": "engineer-visits", "link_field": "engineer_visit"},
			{"doctype": "Service Closure", "fieldname": "customer_feedback", "label": "Service Closure", "route": "service-closures"},
		],
		"Service Closure": [
			{"doctype": "Swift Service Request", "fieldname": "name", "label": "Service Request", "route": "service-requests", "link_field": "service_request"},
			{"doctype": "Service Report", "fieldname": "name", "label": "Service Report", "route": "service-reports", "link_field": "service_report"},
			{"doctype": "Service Billing", "fieldname": "name", "label": "Billing", "route": "billing", "link_field": "service_billing"},
			{"doctype": "Customer Feedback", "fieldname": "name", "label": "Feedback", "route": "feedback", "link_field": "customer_feedback"},
		],
	}

	out = []
	for conf in CONN.get(doctype, []):
		linked_dt = conf["doctype"]
		if not frappe.db.exists("DocType", linked_dt):
			continue
		# Special: open parent via link_field on current doc
		if conf.get("link_field"):
			parent_name = frappe.db.get_value(doctype, name, conf["link_field"])
			count = 1 if parent_name else 0
			items = [{"name": parent_name}] if parent_name else []
			fieldname = conf.get("link_field")
		else:
			items = frappe.get_all(
				linked_dt,
				filters={conf["fieldname"]: name},
				fields=["name"],
				order_by="modified desc",
				limit_page_length=20,
				ignore_permissions=True,
			)
			count = frappe.db.count(linked_dt, {conf["fieldname"]: name})
			fieldname = conf["fieldname"]
		out.append(
			{
				"doctype": linked_dt,
				"label": conf["label"],
				"route": conf["route"],
				"fieldname": fieldname,
				"count": count,
				"items": items,
				"is_parent_link": bool(conf.get("link_field")),
			}
		)
	return out


@frappe.whitelist()
def get_comments(doctype, name, comment_type="Comment"):
	"""User comments / notes on a document (Comment doctype)."""
	_ensure_allowed(doctype)
	frappe.get_doc(doctype, name).check_permission("read")
	ctype = comment_type or "Comment"
	rows = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": doctype,
			"reference_name": name,
			"comment_type": ctype,
		},
		fields=[
			"name",
			"content",
			"creation",
			"modified",
			"owner",
			"comment_by",
			"comment_email",
			"comment_type",
		],
		order_by="creation desc",
		limit_page_length=100,
	)
	out = []
	for r in rows:
		user = r.get("comment_email") or r.get("owner")
		info = (
			frappe.db.get_value("User", user, ["full_name", "user_image"], as_dict=True) or {}
			if user
			else {}
		)
		out.append(
			{
				"name": r.name,
				"content": r.content or "",
				"creation": r.creation,
				"owner": user,
				"owner_name": r.get("comment_by") or info.get("full_name") or user,
				"image": _user_image_url(info.get("user_image")),
				"comment_type": r.get("comment_type") or ctype,
			}
		)
	return out


@frappe.whitelist()
def get_emails(doctype, name, limit=50):
	"""Communication emails linked to a document."""
	_ensure_allowed(doctype)
	frappe.get_doc(doctype, name).check_permission("read")
	limit = cint(limit) or 50
	try:
		from frappe.desk.form.load import get_communication_data

		rows = get_communication_data(doctype, name, start=0, limit=limit) or []
	except Exception:
		rows = frappe.get_all(
			"Communication",
			filters={
				"reference_doctype": doctype,
				"reference_name": name,
				"communication_medium": "Email",
			},
			fields=[
				"name",
				"subject",
				"sender",
				"recipients",
				"cc",
				"bcc",
				"content",
				"communication_date",
				"creation",
				"sent_or_received",
			],
			order_by="creation desc",
			limit_page_length=limit,
		)
	out = []
	for c in rows:
		out.append(
			{
				"name": c.get("name"),
				"subject": c.get("subject") or "",
				"sender": c.get("sender") or "",
				"recipients": c.get("recipients") or "",
				"cc": c.get("cc") or "",
				"bcc": c.get("bcc") or "",
				"content": c.get("content") or c.get("text_content") or "",
				"creation": c.get("communication_date") or c.get("creation"),
				"sent_or_received": c.get("sent_or_received") or "",
			}
		)
	return out


@frappe.whitelist()
def get_email_contacts(txt=""):
	"""Contact / user emails for To/CC/BCC autocomplete (ERPNext-style)."""
	try:
		from frappe.email import get_contact_list

		return get_contact_list(txt=txt or "", page_length=20) or []
	except Exception:
		# Fallback: enabled Users with email
		filters = {"enabled": 1, "user_type": "System User"}
		kwargs = {
			"filters": filters,
			"fields": ["name", "email", "full_name"],
			"limit_page_length": 20,
		}
		if txt:
			kwargs["or_filters"] = [
				["email", "like", f"%{txt}%"],
				["full_name", "like", f"%{txt}%"],
				["name", "like", f"%{txt}%"],
			]
		users = frappe.get_all("User", **kwargs)
		out = []
		for u in users:
			email = u.email or u.name
			if not email or "@" not in str(email):
				continue
			out.append(
				{
					"value": email,
					"label": u.full_name or email,
					"description": email,
				}
			)
		return out


@frappe.whitelist()
def get_email_accounts():
	"""Outgoing email accounts for From selector."""
	accounts = frappe.get_all(
		"Email Account",
		filters={"enable_outgoing": 1},
		fields=["email_id", "name", "default_outgoing"],
		order_by="default_outgoing desc, name asc",
	)
	out = []
	for a in accounts:
		if a.email_id:
			out.append({"value": a.email_id, "label": a.email_id, "default": cint(a.default_outgoing)})
	# Always allow current user email
	user = frappe.session.user
	user_email = frappe.db.get_value("User", user, "email") or user
	if user_email and not any(x["value"] == user_email for x in out):
		out.insert(0, {"value": user_email, "label": user_email, "default": 0})
	return out


@frappe.whitelist()
def send_email(
	doctype,
	name,
	recipients,
	subject,
	content,
	cc=None,
	bcc=None,
	attachments=None,
	sender=None,
	send_me_a_copy=0,
	in_reply_to=None,
):
	"""Send an email linked to a document (ERPNext Communication.make)."""
	_ensure_allowed(doctype)
	doc = frappe.get_doc(doctype, name)
	try:
		doc.check_permission("email")
	except Exception:
		doc.check_permission("write")

	recipients = (recipients or "").strip()
	cc = (cc or "").strip()
	bcc = (bcc or "").strip()
	subject = (subject or "").strip()
	content = (content or "").strip()

	if not (recipients or cc or bcc):
		frappe.throw("At least one of To, CC, or BCC is required")
	if not subject:
		frappe.throw("Subject is required")
	if not content:
		frappe.throw("Message is required")

	# attachments: list of File names (JSON string or list)
	if isinstance(attachments, str):
		try:
			attachments = json.loads(attachments) if attachments else []
		except Exception:
			attachments = [a.strip() for a in attachments.split(",") if a.strip()]
	attachments = attachments or []

	sender = (sender or "").strip() or None
	sender_full_name = None
	if sender:
		sender_full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user

	from frappe.core.doctype.communication.email import make

	result = make(
		doctype=doctype,
		name=name,
		recipients=recipients,
		cc=cc,
		bcc=bcc,
		subject=subject,
		content=content,
		send_email=1,
		sender=sender,
		sender_full_name=sender_full_name,
		attachments=attachments,
		send_me_a_copy=cint(send_me_a_copy),
		in_reply_to=in_reply_to or None,
	)
	return result


@frappe.whitelist()
def add_comment(doctype, name, content, comment_type="Comment"):
	"""Add a Comment / Info note on a document (fires @mention notifications)."""
	_ensure_allowed(doctype)
	content = (content or "").strip()
	if not content:
		frappe.throw("Comment cannot be empty")

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")

	# Ensure mentioned users can receive Notification Log (Frappe filters on this flag)
	_enable_mention_recipients(content)

	user = frappe.session.user
	ctype = comment_type or "Comment"
	comment = frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": ctype,
			"reference_doctype": doctype,
			"reference_name": name,
			"content": content,
			"comment_email": user,
			"comment_by": frappe.db.get_value("User", user, "full_name") or user,
		}
	)
	comment.insert(ignore_permissions=True)
	frappe.db.commit()
	info = frappe.db.get_value("User", user, ["full_name", "user_image"], as_dict=True) or {}
	return {
		"name": comment.name,
		"content": comment.content or "",
		"creation": comment.creation,
		"owner": user,
		"owner_name": info.get("full_name") or user,
		"image": _user_image_url(info.get("user_image")),
		"comment_type": ctype,
	}


def _enable_mention_recipients(content):
	"""Turn on allowed_in_mentions for users referenced in mention spans."""
	try:
		from bs4 import BeautifulSoup
	except ImportError:
		return
	soup = BeautifulSoup(content or "", "html.parser")
	for mention in soup.find_all(class_="mention"):
		uid = mention.get("data-id")
		if not uid or mention.get("data-is-group") == "true":
			continue
		if not frappe.db.exists("User", uid):
			continue
		if not cint(frappe.db.get_value("User", uid, "allowed_in_mentions")):
			frappe.db.set_value("User", uid, "allowed_in_mentions", 1, update_modified=False)


@frappe.whitelist()
def get_attachments(doctype, name):
	"""Files attached to a document."""
	_ensure_allowed(doctype)
	frappe.get_doc(doctype, name).check_permission("read")
	return frappe.get_all(
		"File",
		filters={"attached_to_doctype": doctype, "attached_to_name": name},
		fields=["name", "file_name", "file_url", "creation", "file_size", "is_private"],
		order_by="creation desc",
		limit_page_length=100,
	)


@frappe.whitelist()
def delete_attachment(doctype, name, file_name):
	"""Remove a File attached to a document."""
	_ensure_allowed(doctype)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	if not file_name:
		frappe.throw("File is required")
	f = frappe.get_doc("File", file_name)
	if f.attached_to_doctype != doctype or f.attached_to_name != name:
		frappe.throw("File is not attached to this document")
	f.delete()
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def get_activity(doctype, name, limit=50):
	"""Mixed activity feed: comments + version / assignment / attachment notes."""
	_ensure_allowed(doctype)
	frappe.get_doc(doctype, name).check_permission("read")
	limit = int(limit or 50)

	comment_types = [
		"Comment",
		"Info",
		"Workflow",
		"Label",
		"Attachment",
		"Attachment Removed",
		"Assigned",
		"Assignment Completed",
		"Shared",
		"Unshared",
		"Like",
	]
	comments = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": doctype,
			"reference_name": name,
			"comment_type": ["in", comment_types],
		},
		fields=["name", "content", "creation", "owner", "comment_type", "comment_by", "comment_email"],
		order_by="creation desc",
		limit_page_length=limit,
	)

	versions = frappe.get_all(
		"Version",
		filters={"ref_doctype": doctype, "docname": name},
		fields=["name", "creation", "owner", "data"],
		order_by="creation desc",
		limit_page_length=limit,
	)

	feed = []
	for c in comments:
		user = c.get("comment_email") or c.get("owner")
		info = (
			frappe.db.get_value("User", user, ["full_name", "user_image"], as_dict=True) or {}
			if user
			else {}
		)
		feed.append(
			{
				"type": "comment" if c.comment_type == "Comment" else "event",
				"subtype": c.comment_type,
				"name": c.name,
				"content": c.content or "",
				"creation": c.creation,
				"owner": user,
				"owner_name": c.get("comment_by") or info.get("full_name") or user,
				"image": _user_image_url(info.get("user_image")),
			}
		)

	for v in versions:
		info = frappe.db.get_value("User", v.owner, ["full_name", "user_image"], as_dict=True) or {}
		changed = []
		try:
			data = frappe.parse_json(v.data) if isinstance(v.data, str) else (v.data or {})
			for row in data.get("changed") or []:
				# [fieldname, old, new]
				if isinstance(row, (list, tuple)) and len(row) >= 3:
					changed.append({"field": row[0], "old": row[1], "new": row[2]})
		except Exception:
			changed = []
		feed.append(
			{
				"type": "version",
				"subtype": "Version",
				"name": v.name,
				"content": "",
				"changed": changed[:8],
				"creation": v.creation,
				"owner": v.owner,
				"owner_name": info.get("full_name") or v.owner,
				"image": _user_image_url(info.get("user_image")),
			}
		)

	# Emails / communications (ERPNext form timeline)
	try:
		from frappe.desk.form.load import get_communication_data

		comms = get_communication_data(doctype, name, start=0, limit=limit) or []
		for c in comms:
			sender = c.get("sender") or c.get("owner") or ""
			feed.append(
				{
					"type": "email",
					"subtype": c.get("communication_medium") or c.get("communication_type") or "Email",
					"name": c.get("name"),
					"subject": c.get("subject") or "",
					"content": c.get("content") or "",
					"creation": c.get("communication_date") or c.get("creation"),
					"owner": sender,
					"owner_name": c.get("sender_full_name") or sender,
					"image": "",
					"recipients": c.get("recipients") or "",
					"delivery_status": c.get("delivery_status") or "",
				}
			)
	except Exception:
		pass

	# Notifications linked to this document
	try:
		if frappe.db.exists("DocType", "Notification Log"):
			notifs = frappe.get_all(
				"Notification Log",
				filters={
					"document_type": doctype,
					"document_name": name,
				},
				fields=["name", "subject", "email_content", "creation", "from_user", "type", "for_user"],
				order_by="creation desc",
				limit_page_length=limit,
			)
			for n in notifs:
				user = n.get("from_user") or n.get("for_user")
				info = (
					frappe.db.get_value("User", user, ["full_name", "user_image"], as_dict=True) or {}
					if user
					else {}
				)
				feed.append(
					{
						"type": "notification",
						"subtype": n.get("type") or "Notification",
						"name": n.name,
						"content": n.get("subject") or n.get("email_content") or "",
						"creation": n.creation,
						"owner": user,
						"owner_name": info.get("full_name") or user,
						"image": _user_image_url(info.get("user_image")),
					}
				)
	except Exception:
		pass

	feed.sort(key=lambda x: x.get("creation") or "", reverse=True)
	return feed[:limit]


@frappe.whitelist()
def get_mention_users(txt=""):
	"""Users for @mention — System Users allowed in mentions, with display names."""
	txt = (txt or "").strip()
	filters = {
		"enabled": 1,
		"user_type": "System User",
		"allowed_in_mentions": 1,
	}
	or_filters = None
	if txt:
		or_filters = [
			["name", "like", f"%{txt}%"],
			["full_name", "like", f"%{txt}%"],
			["first_name", "like", f"%{txt}%"],
			["last_name", "like", f"%{txt}%"],
			["email", "like", f"%{txt}%"],
		]
	rows = frappe.get_all(
		"User",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "full_name", "first_name", "last_name", "user_image", "email"],
		order_by="full_name asc",
		limit_page_length=50,
		ignore_permissions=True,
	)
	# Fallback if none are flagged for mentions (dev sites often leave this off)
	if not rows and not txt:
		rows = frappe.get_all(
			"User",
			filters={"enabled": 1, "user_type": "System User"},
			fields=["name", "full_name", "first_name", "last_name", "user_image", "email"],
			order_by="full_name asc",
			limit_page_length=50,
			ignore_permissions=True,
		)
	out = []
	for r in rows:
		if r.name == "Guest":
			continue
		label = (
			(r.full_name or "").strip()
			or " ".join(filter(None, [r.first_name, r.last_name])).strip()
			or (r.email or r.name).split("@")[0]
		)
		out.append(
			{
				"id": r.name,
				"value": r.name,
				"name": r.name,
				"label": label,
				"full_name": label,
				"email": r.email or r.name,
				"image": _user_image_url(r.user_image),
			}
		)
	return out


@frappe.whitelist()
def get_apps():
	"""Apps list for SPA switcher (Desk + installed apps)."""
	from frappe.apps import get_apps as frappe_get_apps

	apps = [
		{
			"name": "frappe",
			"title": "Desk",
			"route": "/app",
			"logo": "/assets/frappe/images/framework.png",
		}
	]
	for a in frappe_get_apps() or []:
		if a.get("name") == "swiftservice":
			continue
		apps.append(
			{
				"name": a.get("name"),
				"title": a.get("title") or a.get("name"),
				"route": a.get("route") or f"/app",
				"logo": a.get("logo") or "/assets/frappe/images/framework.png",
			}
		)
	return apps


@frappe.whitelist()
def get_assignments(doctype, name):
	"""Frappe ToDo assignments for a document (CRM-style Assign To)."""
	_ensure_allowed(doctype)
	from frappe.desk.form.assign_to import get as get_assigned

	rows = get_assigned({"doctype": doctype, "name": name}) or []
	out = []
	for row in rows:
		user = row.get("owner")
		if not user:
			continue
		info = frappe.db.get_value(
			"User", user, ["full_name", "user_image"], as_dict=True
		) or {}
		out.append(
			{
				"name": user,
				"label": info.get("full_name") or user,
				"image": _user_image_url(info.get("user_image")),
				"todo": row.get("name"),
			}
		)
	return out


@frappe.whitelist()
def assign_to(doctype, name, users, description=None):
	"""Assign document to one or more users via Frappe ToDo."""
	_ensure_allowed(doctype)
	from frappe.desk.form.assign_to import add

	users = frappe.parse_json(users) if isinstance(users, str) else users
	if not users:
		frappe.throw("Select at least one user")
	if isinstance(users, str):
		users = [users]
	add(
		{
			"assign_to": users,
			"doctype": doctype,
			"name": name,
			"description": description or f"Assigned via SwiftService: {doctype} {name}",
			"notify": 1,
		}
	)
	return get_assignments(doctype, name)


@frappe.whitelist()
def remove_assignment(doctype, name, user):
	"""Remove a user assignment from a document."""
	_ensure_allowed(doctype)
	from frappe.desk.form.assign_to import remove

	remove(doctype, name, user)
	return get_assignments(doctype, name)


@frappe.whitelist()
def get_list(
	doctype,
	fields=None,
	filters=None,
	order_by="modified desc",
	limit_page_length=20,
	search=None,
	search_fields=None,
):
	"""List for SPA with free-text search across fields."""
	_ensure_allowed(doctype)
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	fields = frappe.parse_json(fields) if isinstance(fields, str) else (fields or ["name"])
	search_fields = frappe.parse_json(search_fields) if isinstance(search_fields, str) else search_fields
	or_filters = None
	if search:
		search_fields = search_fields or ["name"]
		or_filters = [[doctype, f, "like", f"%{search}%"] for f in search_fields if f]
	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by=order_by or "modified desc",
		limit_page_length=cint(limit_page_length) or 20,
	)
	_attach_assignments(doctype, rows)
	count_filters = filters
	total = frappe.db.count(doctype, filters=count_filters) if not search else len(
		frappe.get_all(
			doctype,
			filters=filters,
			or_filters=or_filters,
			pluck="name",
			limit_page_length=1000,
		)
	)
	return {"data": rows, "total": total}


def _attach_assignments(doctype, rows):
	"""Attach CRM-style _assign avatars (name, label, image) from open ToDos."""
	if not rows:
		return
	names = [r.get("name") for r in rows if r.get("name")]
	if not names:
		return
	todos = frappe.get_all(
		"ToDo",
		filters={
			"reference_type": doctype,
			"reference_name": ["in", names],
			"status": ("not in", ("Cancelled", "Closed")),
		},
		fields=["reference_name", "allocated_to"],
	)
	by_doc = {}
	all_users = set()
	for t in todos:
		if not t.allocated_to:
			continue
		by_doc.setdefault(t.reference_name, []).append(t.allocated_to)
		all_users.add(t.allocated_to)

	user_map = {}
	if all_users:
		for u in frappe.get_all(
			"User",
			filters={"name": ["in", list(all_users)]},
			fields=["name", "full_name", "user_image"],
		):
			user_map[u.name] = u

	for r in rows:
		users = by_doc.get(r.get("name"), [])
		# unique preserve order
		seen = set()
		avatars = []
		for user in users:
			if user in seen:
				continue
			seen.add(user)
			info = user_map.get(user) or {}
			avatars.append(
				{
					"name": user,
					"label": info.get("full_name") or user,
					"image": _user_image_url(info.get("user_image")),
				}
			)
		r["_assign"] = avatars
		r["assigned_to"] = ", ".join(a["label"] for a in avatars) if avatars else ""


@frappe.whitelist()
def get_doc(doctype, name):
	_ensure_allowed(doctype)
	doc = frappe.get_doc(doctype, name)
	_normalize_service_request_doc(doc)
	# Auto-heal cancelled parent links → amendment (keeps detail/process pages usable)
	remapped = []
	for df in doc.meta.get_link_fields():
		val = doc.get(df.fieldname)
		if not val or not df.options:
			continue
		if not frappe.db.exists("DocType", df.options):
			continue
		if not frappe.get_meta(df.options).is_submittable:
			continue
		if cint(frappe.db.get_value(df.options, val, "docstatus")) != 2:
			continue
		active = _find_amendment(df.options, val)
		if active and active != val:
			frappe.db.set_value(doctype, name, df.fieldname, active, update_modified=False)
			doc.set(df.fieldname, active)
			remapped.append(f"{df.label or df.fieldname}: {val} → {active}")
	if remapped:
		frappe.db.commit()
	data = doc.as_dict()
	if remapped:
		data["_remapped_links"] = remapped
	if cint(doc.docstatus) == 2:
		data["_amendment"] = _find_amendment(doctype, name)
		data["_is_cancelled"] = 1
	# Site GPS for visit map / geofence UI
	if doctype == "Engineer Visit" and doc.get("service_request"):
		site = frappe.db.get_value(
			"Swift Service Request",
			doc.service_request,
			["geo_latitude", "geo_longitude", "customer_address", "customer", "mobile_no"],
			as_dict=True,
		)
		if site:
			lat, lng = flt(site.geo_latitude), flt(site.geo_longitude)
			# Treat null-island as missing — engineers cannot navigate to 0,0
			if abs(lat) < 0.00001 and abs(lng) < 0.00001:
				data["_site_latitude"] = None
				data["_site_longitude"] = None
			else:
				data["_site_latitude"] = lat
				data["_site_longitude"] = lng
			data["_site_address"] = site.customer_address or ""
			if not data.get("site_address") and site.customer_address:
				data["site_address"] = site.customer_address
			if not data.get("customer") and site.customer:
				data["customer"] = site.customer
			if not data.get("mobile_no") and site.mobile_no:
				data["mobile_no"] = site.mobile_no
		# Backfill missing addresses when coords exist
		try:
			from swiftservice.swiftservice.doctype.engineer_visit.engineer_visit import reverse_geocode

			changed = False
			if (
				not data.get("check_in_address")
				and data.get("check_in_latitude")
				and data.get("check_in_longitude")
				and abs(flt(data.check_in_latitude)) > 0.00001
			):
				addr = reverse_geocode(data.check_in_latitude, data.check_in_longitude)
				if addr:
					frappe.db.set_value(
						"Engineer Visit", name, "check_in_address", addr, update_modified=False
					)
					data["check_in_address"] = addr
					changed = True
			if (
				not data.get("check_out_address")
				and data.get("check_out_latitude")
				and data.get("check_out_longitude")
				and abs(flt(data.check_out_latitude)) > 0.00001
			):
				addr = reverse_geocode(data.check_out_latitude, data.check_out_longitude)
				if addr:
					frappe.db.set_value(
						"Engineer Visit", name, "check_out_address", addr, update_modified=False
					)
					data["check_out_address"] = addr
					changed = True
			if changed:
				frappe.db.commit()
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Engineer Visit address backfill")
	return data


@frappe.whitelist()
def save_doc(doctype, doc):
	_ensure_allowed(doctype)
	data = frappe.parse_json(doc) if isinstance(doc, str) else doc
	data = frappe._dict(data)
	data.doctype = doctype
	if doctype == "Swift Service Request" and data.get("status"):
		data.status = _normalize_status(data.status)

	if data.name and frappe.db.exists(doctype, data.name):
		existing = frappe.get_doc(doctype, data.name)
		existing.update(data)
		_normalize_service_request_doc(existing)
		remapped = _remap_cancelled_links(existing)
		try:
			existing.save(ignore_permissions=True)
		except frappe.CancelledLinkError:
			# Last resort: keep existing cancelled links so detail page remains usable
			existing.flags.ignore_links = True
			existing.save(ignore_permissions=True)
		frappe.db.commit()
		out = existing.as_dict()
		if remapped:
			out["_remapped_links"] = remapped
		return out

	new_doc = frappe.get_doc(data)
	_remap_cancelled_links(new_doc)
	# Never create new docs pointing at cancelled parents when an amendment exists
	if new_doc.get("service_request"):
		new_doc.service_request = _resolve_active_link(
			"Swift Service Request", new_doc.service_request
		)
	try:
		new_doc.insert(ignore_permissions=True)
	except frappe.CancelledLinkError as e:
		frappe.throw(
			str(e)
			+ ". Open the amended Service Request (or Amend the cancelled one) and link that instead."
		)
	frappe.db.commit()
	return new_doc.as_dict()


@frappe.whitelist()
def set_status(doctype, name, status_field="status", status=None):
	_ensure_allowed(doctype)
	if not status:
		frappe.throw("Status is required")
	doc = frappe.get_doc(doctype, name)
	if not hasattr(doc, status_field):
		frappe.throw(f"Field {status_field} not found")
	setattr(doc, status_field, status)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def get_settings():
	if not frappe.db.exists("DocType", "SwiftService Settings"):
		return {
			"brand_name": "SwiftService",
			"brand_logo": "",
			"favicon": "",
			"google_maps_api_key": "",
			"has_google_maps_api_key": 0,
			"default_sla_hours": 24,
			"default_priority": "Medium",
			"auto_create_issue": 1,
			"notify_on_assignment": 1,
			"notify_on_resolution": 1,
		}
	doc = frappe.get_single("SwiftService Settings")
	out = doc.as_dict()
	# Never expose secret key value to client.
	out["google_maps_api_key"] = ""
	out["has_google_maps_api_key"] = (
		1 if doc.get_password("google_maps_api_key", raise_exception=False) else 0
	)
	return out


@frappe.whitelist()
def save_settings(doc):
	data = frappe.parse_json(doc) if isinstance(doc, str) else doc
	settings = frappe.get_single("SwiftService Settings")
	allowed = {
		"brand_name",
		"brand_logo",
		"favicon",
		"google_maps_api_key",
		"default_sla_hours",
		"default_priority",
		"auto_create_issue",
		"notify_on_assignment",
		"notify_on_resolution",
		"default_service_warehouse",
		"default_income_account",
		"default_cost_center",
		"auto_submit_stock_entry",
		"auto_submit_sales_invoice",
	}
	for key, value in data.items():
		if key in allowed:
			if key == "google_maps_api_key":
				# Empty/masked input means "keep current key".
				if not value or str(value).strip() in {"*****", "******", "********"}:
					continue
			settings.set(key, value)
	settings.save(ignore_permissions=True)
	frappe.db.commit()
	out = settings.as_dict()
	out["google_maps_api_key"] = ""
	out["has_google_maps_api_key"] = (
		1 if settings.get_password("google_maps_api_key", raise_exception=False) else 0
	)
	return out


@frappe.whitelist()
def get_user_profile():
	user = frappe.session.user
	if user in ("Guest", "Administrator") or not user:
		# Still return Administrator profile when logged in as Administrator
		pass
	if user == "Guest":
		frappe.throw("Not logged in", frappe.PermissionError)
	info = frappe.db.get_value(
		"User",
		user,
		["name", "full_name", "first_name", "last_name", "email", "user_image", "phone", "mobile_no"],
		as_dict=True,
	)
	return info or {}


@frappe.whitelist()
def save_user_profile(doc):
	data = frappe.parse_json(doc) if isinstance(doc, str) else doc
	user = frappe.session.user
	if user == "Guest":
		frappe.throw("Not logged in", frappe.PermissionError)
	user_doc = frappe.get_doc("User", user)
	for key in ("full_name", "first_name", "last_name", "user_image", "phone", "mobile_no"):
		if key in data:
			user_doc.set(key, data.get(key))
	user_doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {
		"name": user_doc.name,
		"full_name": user_doc.full_name,
		"first_name": user_doc.first_name,
		"last_name": user_doc.last_name,
		"email": user_doc.email,
		"user_image": user_doc.user_image,
		"phone": user_doc.phone,
		"mobile_no": user_doc.mobile_no,
	}


@frappe.whitelist()
def get_report_data(report_name):
	"""In-app report data without Desk."""
	if report_name == "open_tickets":
		return frappe.get_all(
			"Swift Service Request",
			filters={"status": ["not in", ["Completed", "Closed"]]},
			fields=["name", "subject", "customer", "status", "priority", "assigned_engineer", "modified"],
			order_by="modified desc",
			limit_page_length=100,
		)
	if report_name == "pending_visits":
		return frappe.get_all(
			"Engineer Visit",
			filters={"status": ["in", ["Planned", "Confirmed", "In Progress"]]},
			fields=["name", "service_request", "engineer", "visit_date", "status", "modified"],
			order_by="visit_date asc",
			limit_page_length=100,
		)
	if report_name == "spare_pending":
		return frappe.get_all(
			"Spare Request",
			filters={"status": ["in", ["Draft", "Requested", "Approved"]]},
			fields=["name", "service_request", "item_code", "qty", "stock_status", "status", "modified"],
			order_by="modified desc",
			limit_page_length=100,
		)
	if report_name == "sla_breach":
		return frappe.db.sql(
			"""
			SELECT name, subject, customer, status, priority, sla_due_datetime
			FROM `tabSwift Service Request`
			WHERE sla_due_datetime IS NOT NULL
			  AND sla_due_datetime < %(now)s
			  AND status NOT IN ('Completed', 'Closed')
			ORDER BY sla_due_datetime ASC
			LIMIT 100
			""",
			{"now": now_datetime()},
			as_dict=True,
		)
	if report_name == "amc_active":
		return frappe.get_all(
			"AMC Contract",
			filters={"status": "Active"},
			fields=["name", "customer", "installed_base", "start_date", "end_date", "remaining_visits", "status"],
			order_by="end_date asc",
			limit_page_length=100,
		)
	frappe.throw(f"Unknown report: {report_name}")


@frappe.whitelist()
def get_dispatch_board(date=None):
	date = date or nowdate()
	visits = frappe.get_all(
		"Engineer Visit",
		filters={"visit_date": ["between", [date, date]]},
		fields=["name", "service_request", "engineer", "visit_date", "status", "check_in_time"],
		order_by="engineer asc, visit_date asc",
	)
	# also include planned without date match nearby
	open_visits = frappe.get_all(
		"Engineer Visit",
		filters={"status": ["in", ["Planned", "Confirmed", "In Progress"]], "visit_date": ["is", "not set"]},
		fields=["name", "service_request", "engineer", "visit_date", "status", "check_in_time"],
		limit_page_length=50,
	)
	by_engineer = {}
	for v in visits + open_visits:
		eng = v.engineer or "Unassigned"
		by_engineer.setdefault(eng, []).append(v)
	return {"date": date, "columns": by_engineer}


@frappe.whitelist()
def get_dashboard_data(scope="organization"):
	"""Home KPIs. scope=organization (all) | my_stats (current user)."""
	user = frappe.session.user
	my = cint(scope == "my_stats")

	def sr_filter(extra=None):
		f = dict(extra or {})
		if my:
			f["assigned_engineer"] = user
		return f

	def visit_filter(extra=None):
		f = dict(extra or {})
		if my:
			f["engineer"] = user
		return f

	def assignment_filter(extra=None):
		f = dict(extra or {})
		if my:
			f["primary_engineer"] = user
		return f

	open_requests = frappe.db.count(
		"Swift Service Request",
		sr_filter({"status": ["in", ["Draft", "Open", "Under Validation"]]}),
	)
	in_progress = frappe.db.count(
		"Swift Service Request",
		sr_filter(
			{
				"status": [
					"in",
					[
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
						"Spare Required",
						"Factory Repair",
						"Replacement Required",
						"In Progress",
					],
				],
			}
		),
	)
	pending_visits = frappe.db.count(
		"Engineer Visit",
		visit_filter(
			{
				"status": [
					"in",
					[
						"Draft",
						"Scheduled",
						"Planned",
						"Confirmed",
						"Travel Started",
						"Travel",
						"Reached Site",
						"GPS Check-In",
						"Inspection",
						"Diagnosis",
						"Repair",
						"Testing",
						"In Progress",
					],
				],
			}
		),
	)
	pending_assignments = 0
	accepted_assignments = 0
	if frappe.db.exists("DocType", "Engineer Assignment"):
		pending_assignments = frappe.db.count(
			"Engineer Assignment",
			assignment_filter(
				{"status": ["in", ["Draft", "Pending Assignment", "Assigned"]], "docstatus": ["<", 2]}
			),
		)
		accepted_assignments = frappe.db.count(
			"Engineer Assignment",
			assignment_filter({"status": "Engineer Accepted", "docstatus": 1}),
		)
	active_amc = (
		frappe.db.count("AMC Contract", {"status": "Active"})
		if frappe.db.exists("DocType", "AMC Contract") and not my
		else (
			frappe.db.count("AMC Contract", {"status": "Active", "owner": user})
			if frappe.db.exists("DocType", "AMC Contract") and my
			else 0
		)
	)
	completed_month = frappe.db.count(
		"Swift Service Request",
		sr_filter(
			{
				"modified": ["like", f"{nowdate()[:7]}%"],
				"status": ["in", ["Completed", "Closed", "Resolved"]],
			}
		),
	)
	critical = frappe.db.count(
		"Swift Service Request",
		sr_filter(
			{
				"priority": ["in", ["High", "Urgent", "Critical"]],
				"status": ["not in", ["Completed", "Closed"]],
			}
		),
	)
	pending_spare = frappe.db.count(
		"Spare Request",
		{"status": ["in", ["Draft", "Requested", "Approved", "Waiting"]], **({"owner": user} if my else {})},
	)

	if my:
		sla_breach = frappe.db.sql(
			"""
			SELECT COUNT(*) FROM `tabSwift Service Request`
			WHERE sla_due_datetime IS NOT NULL AND sla_due_datetime < %s
			AND status NOT IN ('Completed', 'Closed')
			AND assigned_engineer = %s
			""",
			(now_datetime(), user),
		)[0][0]
		status_rows = frappe.db.sql(
			"""
			SELECT status, COUNT(*) as count
			FROM `tabSwift Service Request`
			WHERE assigned_engineer = %s
			GROUP BY status
			ORDER BY count DESC
			""",
			(user,),
			as_dict=True,
		)
		recent_requests = frappe.get_all(
			"Swift Service Request",
			filters={"assigned_engineer": user},
			fields=["name", "subject", "customer", "status", "priority"],
			order_by="modified desc",
			limit=10,
		)
	else:
		sla_breach = frappe.db.sql(
			"""
			SELECT COUNT(*) FROM `tabSwift Service Request`
			WHERE sla_due_datetime IS NOT NULL AND sla_due_datetime < %s
			AND status NOT IN ('Completed', 'Closed')
			""",
			(now_datetime(),),
		)[0][0]
		status_rows = frappe.db.sql(
			"""
			SELECT status, COUNT(*) as count
			FROM `tabSwift Service Request`
			GROUP BY status
			ORDER BY count DESC
			""",
			as_dict=True,
		)
		recent_requests = frappe.get_all(
			"Swift Service Request",
			fields=["name", "subject", "customer", "status", "priority"],
			order_by="modified desc",
			limit=10,
		)

	return {
		"scope": "my_stats" if my else "organization",
		"open_requests": open_requests,
		"in_progress": in_progress,
		"pending_visits": pending_visits,
		"pending_assignments": pending_assignments,
		"accepted_assignments": accepted_assignments,
		"active_amc": active_amc,
		"completed_month": completed_month,
		"critical_tickets": critical,
		"pending_spare": pending_spare,
		"sla_breach": sla_breach,
		"status_breakdown": status_rows,
		"recent_requests": recent_requests,
	}


@frappe.whitelist()
def get_notifications(limit=40):
	"""Unread + recent Notification Log for the current user (Helpdesk-style feed)."""
	limit = cint(limit) or 40
	rows = frappe.get_all(
		"Notification Log",
		filters={"for_user": frappe.session.user},
		fields=[
			"name",
			"subject",
			"email_content",
			"document_type",
			"document_name",
			"from_user",
			"type",
			"read",
			"creation",
		],
		order_by="creation desc",
		limit_page_length=limit,
	)
	out = []
	for r in rows:
		out.append(
			{
				"name": r.name,
				"subject": r.subject or "",
				"message": frappe.utils.strip_html(r.email_content or "")[:240] if r.email_content else "",
				"document_type": r.document_type,
				"document_name": r.document_name,
				"from_user": r.from_user,
				"type": r.type,
				"read": cint(r.read),
				"creation": r.creation,
			}
		)
	unread = frappe.db.count(
		"Notification Log",
		{"for_user": frappe.session.user, "read": 0},
	)
	return {"notifications": out, "unread": unread}


@frappe.whitelist()
def mark_notification_read(name=None):
	if name:
		frappe.db.set_value(
			"Notification Log",
			{"name": name, "for_user": frappe.session.user},
			"read",
			1,
			update_modified=False,
		)
	return get_notifications()


@frappe.whitelist()
def mark_all_notifications_read():
	names = frappe.get_all(
		"Notification Log",
		filters={"for_user": frappe.session.user, "read": 0},
		pluck="name",
	)
	if names:
		frappe.db.set_value(
			"Notification Log",
			{"name": ["in", names]},
			"read",
			1,
			update_modified=False,
		)
	return get_notifications()


@frappe.whitelist()
def create_service_request(
	customer=None,
	serial_no=None,
	subject=None,
	priority="Medium",
	complaint_type="Warranty",
	territory=None,
	**kwargs,
):
	if not subject:
		frappe.throw("Subject is required.")

	issue_name = None
	try:
		issue = frappe.new_doc("Issue")
		issue.subject = subject
		if customer and frappe.db.exists("Customer", customer):
			issue.customer = customer
		issue.priority = priority or "Medium"
		issue.status = "Open"
		if frappe.db.exists("Issue Type", "Warranty"):
			issue.issue_type = "Warranty"
		issue.insert(ignore_permissions=True)
		issue_name = issue.name
	except Exception:
		frappe.log_error(frappe.get_traceback(), "SwiftService create Issue skipped")

	installed_base = None
	if serial_no:
		installed_base = frappe.db.get_value("Installed Base", {"serial_no": serial_no}, "name")

	if not territory and customer and frappe.db.exists("Customer", customer):
		territory = frappe.db.get_value("Customer", customer, "territory")

	request = frappe.new_doc("Swift Service Request")
	request.customer = customer if customer and frappe.db.exists("Customer", customer) else None
	request.territory = territory if territory and frappe.db.exists("Territory", territory) else None
	request.serial_no = serial_no if serial_no and frappe.db.exists("Serial No", serial_no) else None
	request.installed_base = installed_base
	if issue_name:
		request.source_issue = issue_name
	request.subject = subject
	request.complaint_type = complaint_type or "Warranty"
	request.priority = priority or "Medium"
	request.status = "Open"
	request.sla_due_datetime = now_datetime()
	request.insert(ignore_permissions=True)

	if serial_no and not request.serial_no:
		request.add_comment("Info", f"Serial Number: {serial_no}")
	if customer and not request.customer:
		request.add_comment("Info", f"Customer (text): {customer}")

	frappe.db.commit()
	return {"name": request.name, "issue": issue_name}



@frappe.whitelist()
def assign_engineer(service_request, engineer, visit_date=None, secondary_engineer=None):
	"""Create Engineer Assignment, sync SSR, and plan Engineer Visit."""
	sr = frappe.get_doc("Swift Service Request", service_request)
	assignment = frappe.get_doc(
		{
			"doctype": "Engineer Assignment",
			"service_request": service_request,
			"primary_engineer": engineer,
			"secondary_engineer": secondary_engineer,
			"planned_visit": visit_date or nowdate(),
			"assignment_date": now_datetime(),
			"assigned_by": frappe.session.user,
			"status": "Assigned",
			"assignment_mode": "Manual",
			"priority": sr.priority or "Medium",
			"source_type": "Service Request",
		}
	)
	assignment.insert(ignore_permissions=True)
	assignment.submit()

	sr.reload()
	# Ensure denormalized SSR fields even if controller sync raced
	sr.assigned_engineer = engineer
	sr.assigned_by = frappe.session.user
	sr.assignment_date = now_datetime()
	if visit_date:
		sr.planned_date = visit_date
	if sr.status not in ("Assigned", "Accepted"):
		sr.status = "Assigned"
	if assignment.engineer_profile:
		sr.engineer_profile = assignment.engineer_profile
	sr.flags.ignore_validate_update_after_submit = True
	sr.save(ignore_permissions=True)

	frappe.db.commit()
	return {
		"service_request": sr.name,
		"assignment": assignment.name,
		"visit": assignment.engineer_visit,
		"status": sr.status,
	}


@frappe.whitelist()
def accept_assignment(assignment, engineer=None):
	doc = frappe.get_doc("Engineer Assignment", assignment)
	user = engineer or frappe.session.user
	if doc.primary_engineer and user != doc.primary_engineer and "System Manager" not in frappe.get_roles():
		# Allow secondary / listed engineers
		listed = {r.engineer for r in (doc.assigned_engineers or [])}
		if user not in listed and "Service Manager" not in frappe.get_roles() and "Service Coordinator" not in frappe.get_roles():
			frappe.throw("Only the assigned engineer can accept this assignment")

	for row in doc.assigned_engineers or []:
		if row.engineer == user or (not engineer and row.role == "Primary"):
			row.status = "Accepted"
			row.acceptance_time = now_datetime()
	doc.status = "Engineer Accepted"
	doc.append(
		"assignment_timeline",
		{
			"activity": "Engineer Accepted",
			"user": frappe.session.user,
			"time": now_datetime(),
			"remarks": user,
		},
	)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def reject_assignment(assignment, reason=None, engineer=None):
	doc = frappe.get_doc("Engineer Assignment", assignment)
	user = engineer or frappe.session.user
	for row in doc.assigned_engineers or []:
		if row.engineer == user or (row.role == "Primary" and not engineer):
			row.status = "Rejected"
			row.rejection_reason = reason
	doc.status = "Pending Assignment"
	doc.primary_engineer = None
	doc.append(
		"assignment_timeline",
		{
			"activity": "Engineer Rejected — returned to coordinator queue",
			"user": frappe.session.user,
			"time": now_datetime(),
			"remarks": reason or "",
		},
	)
	doc.save(ignore_permissions=True)
	# Bounce SSR back toward Open/Under Validation for reassignment
	if doc.service_request and frappe.db.exists("Swift Service Request", doc.service_request):
		sr = frappe.get_doc("Swift Service Request", doc.service_request)
		if sr.docstatus == 1 and sr.status in ("Assigned", "Accepted"):
			sr.status = "Under Validation"
			sr.assigned_engineer = None
			sr.flags.ignore_validate_update_after_submit = True
			sr.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def advance_assignment_status(assignment, status=None):
	doc = frappe.get_doc("Engineer Assignment", assignment)
	from swiftservice.swiftservice.doctype.engineer_assignment.engineer_assignment import (
		ALLOWED_TRANSITIONS,
	)

	if status:
		allowed = ALLOWED_TRANSITIONS.get(doc.status) or set()
		if status != doc.status and status not in allowed and "System Manager" not in frappe.get_roles():
			frappe.throw(f"Cannot move assignment from {doc.status} to {status}")
		doc.status = status
	else:
		order = [
			"Draft",
			"Pending Assignment",
			"Assigned",
			"Engineer Accepted",
			"Travel Started",
			"Reached Customer",
			"Visit Completed",
			"Assignment Closed",
		]
		if doc.status in order:
			idx = order.index(doc.status)
			if idx < len(order) - 1:
				doc.status = order[idx + 1]
	if doc.status == "Travel Started" and not doc.travel_start:
		doc.travel_start = now_datetime()
	if doc.status == "Reached Customer" and not doc.arrival_time:
		doc.arrival_time = now_datetime()
	if doc.status == "Visit Completed" and not doc.completion_time:
		doc.completion_time = now_datetime()
		doc.visit_status = "Completed"
	doc.append(
		"assignment_timeline",
		{
			"activity": f"Status → {doc.status}",
			"user": frappe.session.user,
			"time": now_datetime(),
			"remarks": "",
		},
	)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def suggest_engineers(service_request, limit=5):
	"""Rank Active Engineer Profiles for a Service Request (Phase-1 heuristic)."""
	sr = frappe.get_doc("Swift Service Request", service_request)
	profiles = frappe.get_all(
		"Engineer Profile",
		filters={"status": "Active"},
		fields=[
			"name",
			"engineer",
			"full_name",
			"region",
			"city",
			"skills",
			"certifications",
			"product_expertise",
			"workload",
			"max_open_jobs",
			"current_location",
		],
		limit_page_length=100,
	)
	territory = (sr.territory or "").lower()
	item = (sr.item_code or sr.item_name or "").lower()
	required_cert = ""

	scored = []
	for p in profiles:
		score = 0
		reasons = []
		region = (p.region or "").lower()
		city = (p.city or "").lower()
		if territory and territory in region:
			score += 40
			reasons.append("Same region")
		elif territory and territory in city:
			score += 30
			reasons.append("Same city")
		expertise = (p.product_expertise or "").lower()
		skills = (p.skills or "").lower()
		if item and (item in expertise or item in skills):
			score += 25
			reasons.append("Product expertise")
		certs = (p.certifications or "").lower()
		if required_cert and required_cert in certs:
			score += 20
			reasons.append("Certification")
		max_jobs = cint(p.max_open_jobs) or 5
		workload = cint(p.workload) or 0
		if workload < max_jobs:
			score += max(0, 15 - workload)
			reasons.append("Available")
		else:
			score -= 50
			reasons.append("At capacity")
		# Prefer lower workload
		score += max(0, 10 - workload)
		scored.append(
			{
				"engineer": p.engineer,
				"engineer_profile": p.name,
				"full_name": p.full_name or p.engineer,
				"score": score,
				"workload": workload,
				"max_open_jobs": max_jobs,
				"reasons": reasons,
				"region": p.region,
				"city": p.city,
			}
		)
	scored.sort(key=lambda x: (-x["score"], x["workload"]))
	return scored[: cint(limit) or 5]


@frappe.whitelist()
def advance_service_status(service_request, status=None):
	doc = frappe.get_doc("Swift Service Request", service_request)
	# normalize legacy status values first
	if doc.status in STATUS_ALIASES:
		doc.status = STATUS_ALIASES[doc.status]
	if status:
		status = STATUS_ALIASES.get(status, status)
		if status not in SERVICE_REQUEST_STATUSES:
			frappe.throw(f"Invalid status: {status}")
		allowed = STATUS_TRANSITIONS.get(doc.status) or []
		if status != doc.status and allowed and status not in allowed:
			if "System Manager" not in frappe.get_roles():
				frappe.throw(f"Cannot move status from {doc.status} to {status}")
		doc.status = status
	else:
		# Advance along canonical happy path (skip legacy duplicate labels)
		canonical = [
			"Draft",
			"Open",
			"Under Validation",
			"Assigned",
			"Accepted",
			"Travel Started",
			"Reached Customer",
			"Inspection",
			"Waiting Spare",
			"Repair In Progress",
			"Testing",
			"Customer Verification",
			"Completed",
			"Closed",
		]
		cur = STATUS_ALIASES.get(doc.status, doc.status)
		if cur in canonical:
			idx = canonical.index(cur)
			if idx < len(canonical) - 1:
				doc.status = canonical[idx + 1]
		elif doc.status in SERVICE_REQUEST_STATUSES:
			idx = SERVICE_REQUEST_STATUSES.index(doc.status)
			if idx < len(SERVICE_REQUEST_STATUSES) - 1:
				doc.status = SERVICE_REQUEST_STATUSES[idx + 1]
	if doc.status == "Closed":
		from swiftservice.swiftservice.doctype.service_closure.service_closure import (
			assert_can_close_service_request,
		)

		assert_can_close_service_request(doc.name)
		doc.closed_by = frappe.session.user
		doc.closed_on = now_datetime()
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def update_diagnosis(service_request, diagnosis_result, resolution_summary=None):
	doc = frappe.get_doc("Swift Service Request", service_request)
	doc.diagnosis_result = diagnosis_result
	doc.resolution_summary = resolution_summary
	status_map = {
		"Issue Fixed": "Completed",
		"Spare Required": "Waiting Spare",
		"Factory Repair": "Repair In Progress",
		"Replacement Required": "Customer Verification",
		"No Fault Found": "Completed",
	}
	doc.status = status_map.get(diagnosis_result, doc.status)
	doc.save(ignore_permissions=True)

	linked = {}
	if diagnosis_result == "Spare Required":
		pass  # UI creates spare
	elif diagnosis_result == "Factory Repair":
		ro = create_repair_order(service_request=service_request, repair_type="Warranty")
		linked["repair_order"] = ro.get("name")
	elif diagnosis_result == "Replacement Required":
		rep = create_replacement_case(service_request)
		linked["replacement"] = rep["name"]

	frappe.db.commit()
	return {"name": doc.name, "status": doc.status, "linked": linked}


@frappe.whitelist()
def create_spare_request(
	service_request,
	item_code=None,
	qty=1,
	warehouse=None,
	engineer_visit=None,
	diagnosis=None,
	request_type=None,
	priority=None,
	items=None,
):
	"""Create Spare Request — supports legacy single item or multi-item JSON."""
	items = frappe.parse_json(items) if isinstance(items, str) else items
	if not item_code and not items:
		frappe.throw("item_code or items is required")
	doc = frappe.get_doc(
		{
			"doctype": "Spare Request",
			"naming_series": "SPR-.YYYY.-.#####",
			"service_request": service_request,
			"engineer_visit": engineer_visit,
			"diagnosis": diagnosis,
			"item_code": item_code,
			"qty": flt(qty) or 1,
			"warehouse": warehouse,
			"status": "Draft",
			"stock_status": "Unknown",
			"request_type": request_type or "Emergency Breakdown",
			"priority": priority or "Medium",
		}
	)
	if items:
		for it in items:
			doc.append(
				"requested_items",
				{
					"item_code": it.get("item_code"),
					"required_qty": flt(it.get("qty") or it.get("required_qty") or 1),
					"warehouse": it.get("warehouse") or warehouse,
					"warranty_claimable": cint(it.get("warranty_claimable")),
					"chargeable": cint(it.get("chargeable")),
					"remarks": it.get("remarks"),
				},
			)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "stock_status": doc.stock_status, **doc.as_dict()}


@frappe.whitelist()
def approve_spare_request(name):
	doc = frappe.get_doc("Spare Request", name)
	doc.approve()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def issue_spare(name, warehouse=None, issue_source="Service Warehouse"):
	doc = frappe.get_doc("Spare Request", name)
	doc.issue(warehouse=warehouse, issue_source=issue_source)
	frappe.db.commit()
	return {
		**doc.as_dict(),
		"material_request": doc.purchase_request,
		"stock_entry": doc.stock_entry,
	}


@frappe.whitelist()
def advance_spare_status(name, status=None):
	doc = frappe.get_doc("Spare Request", name)
	doc.advance_status(status=status)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def receive_spare(name):
	doc = frappe.get_doc("Spare Request", name)
	doc.mark_received()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def consume_spare(name, items=None):
	doc = frappe.get_doc("Spare Request", name)
	items = frappe.parse_json(items) if isinstance(items, str) else items
	doc.consume(items=items)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def return_spare(name, items=None):
	doc = frappe.get_doc("Spare Request", name)
	items = frappe.parse_json(items) if isinstance(items, str) else items
	doc.return_parts(items=items)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def create_spare_purchase_request(name):
	doc = frappe.get_doc("Spare Request", name)
	mr = doc.create_purchase_request()
	frappe.db.commit()
	return {"name": doc.name, "purchase_request": mr, **doc.as_dict()}


@frappe.whitelist()
def create_repair_order(
	service_request=None,
	engineer_visit=None,
	diagnosis=None,
	repair_type=None,
	priority=None,
):
	if not service_request and engineer_visit:
		service_request = frappe.db.get_value("Engineer Visit", engineer_visit, "service_request")
	if not service_request and diagnosis:
		service_request = frappe.db.get_value("Failure Analysis", diagnosis, "service_request")
	if not service_request:
		frappe.throw("service_request is required")
	from swiftservice.swiftservice.doctype.repair_order.repair_order import create_from_source

	doc = create_from_source(
		service_request=service_request,
		engineer_visit=engineer_visit,
		diagnosis=diagnosis,
		repair_type=repair_type,
	)
	if priority:
		doc.priority = priority
		doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def advance_repair_status(name, status=None):
	doc = frappe.get_doc("Repair Order", name)
	doc.advance_status(status=status)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def repair_mark_received(name):
	doc = frappe.get_doc("Repair Order", name)
	doc.mark_received()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def repair_start(name):
	doc = frappe.get_doc("Repair Order", name)
	doc.start_repair()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def repair_complete(name):
	doc = frappe.get_doc("Repair Order", name)
	doc.complete_repair()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def repair_pass_testing(name):
	doc = frappe.get_doc("Repair Order", name)
	doc.pass_testing()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def repair_pass_quality(name, result="Pass"):
	doc = frappe.get_doc("Repair Order", name)
	doc.pass_quality(result=result)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def repair_dispatch(name):
	doc = frappe.get_doc("Repair Order", name)
	doc.mark_dispatched()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def repair_recommend_replacement(name, ber=0):
	doc = frappe.get_doc("Repair Order", name)
	doc.recommend_replacement(ber=cint(ber))
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def create_rma_case(service_request):
	doc = frappe.get_doc(
		{
			"doctype": "RMA Case",
			"service_request": service_request,
			"repair_status": "Initiated",
		}
	).insert(ignore_permissions=True)
	sr = frappe.get_doc("Swift Service Request", service_request)
	sr.status = "Repair In Progress"
	sr.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name}


@frappe.whitelist()
def advance_rma(name, repair_status):
	doc = frappe.get_doc("RMA Case", name)
	doc.repair_status = repair_status
	if repair_status == "Received" and not doc.received_date:
		doc.received_date = nowdate()
	if repair_status == "Dispatched" and not doc.dispatch_date:
		doc.dispatch_date = nowdate()
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def create_replacement_case(service_request):
	doc = frappe.get_doc(
		{
			"doctype": "Replacement Case",
			"service_request": service_request,
			"approval_status": "Pending",
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name}


@frappe.whitelist()
def approve_replacement(name, level="technical"):
	doc = frappe.get_doc("Replacement Case", name)
	if level == "technical":
		doc.approval_status = "Technical Approved"
	elif level == "management":
		doc.approval_status = "Approved"
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def complete_replacement(name, new_serial_no=None, old_serial_no=None):
	doc = frappe.get_doc("Replacement Case", name)
	if new_serial_no:
		doc.new_serial_no = new_serial_no
	if old_serial_no:
		doc.old_serial_no = old_serial_no
	doc.approval_status = "Completed"
	doc.dispatch_date = nowdate()
	doc.warranty_transfer_date = nowdate()
	doc.save(ignore_permissions=True)

	# update installed base serial if linked via SR
	sr = frappe.get_doc("Swift Service Request", doc.service_request)
	if sr.installed_base and new_serial_no:
		ib = frappe.get_doc("Installed Base", sr.installed_base)
		ib.serial_no = new_serial_no
		ib.save(ignore_permissions=True)
	sr.status = "Completed"
	sr.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def create_pm_visit(installed_base, scheduled_date, engineer=None):
	doc = frappe.new_doc("Preventive Maintenance Visit")
	doc.installed_base = installed_base
	doc.customer = frappe.db.get_value("Installed Base", installed_base, "customer")
	doc.scheduled_date = scheduled_date
	doc.engineer = engineer
	doc.status = "Assigned" if engineer else "Planned"
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name}


@frappe.whitelist()
def set_visit_site_location(name, gps_lat=None, gps_lng=None, address=None):
	"""
	Set the customer destination pin on the linked Service Request.
	Used so engineers can navigate like Blinkit/Zomato to an exact drop pin.
	Pass lat/lng, or free-text address (forward-geocoded).
	"""
	_ensure_allowed("Engineer Visit")
	visit = frappe.get_doc("Engineer Visit", name)
	if not visit.service_request:
		frappe.throw(_("No Service Request linked to this visit"))

	from swiftservice.swiftservice.doctype.engineer_visit.engineer_visit import (
		geocode_address,
		is_valid_geo,
		reverse_geocode,
	)

	address = (address or "").strip() or None
	lat = flt(gps_lat) if gps_lat not in (None, "") else None
	lng = flt(gps_lng) if gps_lng not in (None, "") else None

	if lat is not None and lng is not None and not is_valid_geo(lat, lng):
		lat = lng = None

	if (lat is None or lng is None) and address:
		hit = geocode_address(address)
		if not hit:
			frappe.throw(
				_("Could not find that address on the map. Add a clearer full address or drop a pin.")
			)
		lat, lng = hit["lat"], hit["lng"]
		if not address or len(address) < 12:
			address = hit.get("display_name") or address

	if lat is None or lng is None or not is_valid_geo(lat, lng):
		frappe.throw(_("Provide GPS coordinates or a full site address"))

	if not address:
		address = reverse_geocode(lat, lng) or None

	sr_name = visit.service_request
	updates = {
		"geo_latitude": lat,
		"geo_longitude": lng,
	}
	if address:
		updates["customer_address"] = address

	# Direct DB update so submitted/cancelled SRs still get a navigable pin
	for field, value in updates.items():
		frappe.db.set_value(
			"Swift Service Request",
			sr_name,
			field,
			value,
			update_modified=True,
		)

	if address:
		frappe.db.set_value(
			"Engineer Visit",
			visit.name,
			"site_address",
			address,
			update_modified=True,
		)

	frappe.db.commit()
	return get_doc("Engineer Visit", visit.name)


@frappe.whitelist()
def check_in_visit(name, gps_lat=None, gps_lng=None, gps_accuracy=None, force=0):
	doc = frappe.get_doc("Engineer Visit", name)
	doc.check_in(lat=gps_lat, lng=gps_lng, accuracy=gps_accuracy, force=cint(force))
	frappe.db.commit()
	return get_doc("Engineer Visit", doc.name)


@frappe.whitelist()
def check_out_visit(name, diagnosis_notes=None, gps_lat=None, gps_lng=None):
	doc = frappe.get_doc("Engineer Visit", name)
	doc.check_out(lat=gps_lat, lng=gps_lng, diagnosis_notes=diagnosis_notes)
	frappe.db.commit()
	return get_doc("Engineer Visit", doc.name)


@frappe.whitelist()
def create_followup_visit(source_visit, visit_date=None, engineer=None, visit_type="Follow-up"):
	"""Create another Engineer Visit for same Service Request (multi-visit support)."""
	src = frappe.get_doc("Engineer Visit", source_visit)
	if not src.service_request:
		frappe.throw("Service Request is required")

	new_visit = frappe.new_doc("Engineer Visit")
	new_visit.service_request = src.service_request
	new_visit.engineer = engineer or src.engineer
	new_visit.company = src.company
	new_visit.branch = src.branch
	new_visit.visit_date = visit_date or nowdate()
	new_visit.visit_type = visit_type or "Follow-up"
	new_visit.status = "Scheduled"
	new_visit.site_address = src.site_address
	new_visit.visit_purpose = src.pending_work or src.recommendation or src.visit_purpose
	new_visit.insert(ignore_permissions=True)

	# Link as a fresh assignment-style cycle on SSR
	if frappe.db.exists("Swift Service Request", src.service_request):
		sr = frappe.get_doc("Swift Service Request", src.service_request)
		if sr.status in ("Completed", "Closed"):
			sr.status = "Assigned"
		if new_visit.engineer:
			sr.assigned_engineer = new_visit.engineer
		sr.flags.ignore_validate_update_after_submit = True
		sr.save(ignore_permissions=True)

	frappe.db.commit()
	return {"name": new_visit.name, "service_request": new_visit.service_request}


def _haversine_m(lat1, lng1, lat2, lng2):
	r = 6371000.0
	phi1, phi2 = math.radians(flt(lat1)), math.radians(flt(lat2))
	dphi = math.radians(flt(lat2) - flt(lat1))
	dlam = math.radians(flt(lng2) - flt(lng1))
	a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
	return 2 * r * math.asin(math.sqrt(a))


def _google_maps_key():
	try:
		val = frappe.db.get_single_value("SwiftService Settings", "google_maps_api_key")
		return (val or "").strip()
	except Exception:
		return ""


def _distance_eta(origin_lat, origin_lng, dest_lat, dest_lng):
	"""Distance+ETA with Google Distance Matrix, fallback to haversine."""
	dist_m = _haversine_m(origin_lat, origin_lng, dest_lat, dest_lng)
	eta_s = max(60, int((dist_m / 1000.0 / 22.0) * 3600))  # fallback city-speed estimate
	api_key = _google_maps_key()
	if not api_key:
		return {"distance_m": dist_m, "eta_sec": eta_s, "source": "haversine"}
	try:
		import requests

		res = requests.get(
			"https://maps.googleapis.com/maps/api/distancematrix/json",
			params={
				"origins": f"{origin_lat},{origin_lng}",
				"destinations": f"{dest_lat},{dest_lng}",
				"mode": "driving",
				"departure_time": "now",
				"key": api_key,
			},
			timeout=8,
		)
		if res.status_code != 200:
			return {"distance_m": dist_m, "eta_sec": eta_s, "source": "haversine"}
		payload = res.json() or {}
		rows = payload.get("rows") or []
		els = (rows[0] or {}).get("elements") if rows else []
		el = (els[0] if els else {}) or {}
		if el.get("status") != "OK":
			return {"distance_m": dist_m, "eta_sec": eta_s, "source": "haversine"}
		g_dist = flt(((el.get("distance") or {}).get("value")) or dist_m)
		g_eta = cint(((el.get("duration_in_traffic") or {}).get("value")) or ((el.get("duration") or {}).get("value")) or eta_s)
		return {"distance_m": g_dist or dist_m, "eta_sec": g_eta or eta_s, "source": "google"}
	except Exception:
		frappe.log_error(frappe.get_traceback(), "SwiftService live distance ETA")
		return {"distance_m": dist_m, "eta_sec": eta_s, "source": "haversine"}


@frappe.whitelist()
def update_live_location(name, gps_lat, gps_lng, gps_accuracy=None, speed_kmph=None, heading=None):
	"""Engineer device pushes current location; server broadcasts realtime."""
	visit = frappe.get_doc("Engineer Visit", name)
	lat, lng = flt(gps_lat), flt(gps_lng)
	if abs(lat) < 0.00001 and abs(lng) < 0.00001:
		frappe.throw(_("Invalid live GPS coordinates"))
	payload = {
		"lat": lat,
		"lng": lng,
		"accuracy": flt(gps_accuracy) if gps_accuracy not in (None, "") else None,
		"speed_kmph": flt(speed_kmph) if speed_kmph not in (None, "") else None,
		"heading": flt(heading) if heading not in (None, "") else None,
		"updated_at": str(now_datetime()),
		"user": frappe.session.user,
		"visit": visit.name,
		"service_request": visit.service_request,
	}
	cache_key = f"swift_live_visit:{visit.name}"
	frappe.cache().set_value(cache_key, payload, expires_in_sec=3600)
	frappe.publish_realtime(
		"swift_live_location",
		message=payload,
		doctype="Engineer Visit",
		docname=visit.name,
	)
	return {"ok": True, "updated_at": payload["updated_at"]}


@frappe.whitelist()
def get_live_tracking(name):
	"""Current live location + distance/ETA to customer pin."""
	visit = frappe.get_doc("Engineer Visit", name)
	cache_key = f"swift_live_visit:{visit.name}"
	live = frappe.cache().get_value(cache_key) or {}

	site = {}
	if visit.service_request:
		site = frappe.db.get_value(
			"Swift Service Request",
			visit.service_request,
			["geo_latitude", "geo_longitude", "customer_address"],
			as_dict=True,
		) or {}

	site_lat = flt(site.get("geo_latitude")) if site else 0
	site_lng = flt(site.get("geo_longitude")) if site else 0
	if abs(site_lat) < 0.00001 and abs(site_lng) < 0.00001:
		site_lat = site_lng = None

	out = {
		"visit": visit.name,
		"service_request": visit.service_request,
		"live_location": live,
		"site": {
			"lat": site_lat,
			"lng": site_lng,
			"address": (site.get("customer_address") if site else "") or visit.site_address or "",
		},
		"eta": None,
	}
	if live and site_lat is not None and site_lng is not None:
		eta = _distance_eta(live.get("lat"), live.get("lng"), site_lat, site_lng)
		out["eta"] = eta
	return out


@frappe.whitelist()
def advance_visit_status(name, status=None):
	doc = frappe.get_doc("Engineer Visit", name)
	from swiftservice.swiftservice.doctype.engineer_visit.engineer_visit import (
		ALLOWED_TRANSITIONS,
		STATUS_ALIASES,
	)

	cur = STATUS_ALIASES.get(doc.status, doc.status)
	if status:
		status = STATUS_ALIASES.get(status, status)
		allowed = ALLOWED_TRANSITIONS.get(doc.status) or ALLOWED_TRANSITIONS.get(cur) or set()
		if status != doc.status and status not in allowed and "System Manager" not in frappe.get_roles():
			frappe.throw(f"Cannot move visit from {doc.status} to {status}")
		doc.status = status
	else:
		order = [
			"Draft",
			"Scheduled",
			"Travel Started",
			"Reached Site",
			"GPS Check-In",
			"Inspection",
			"Diagnosis",
			"Repair",
			"Testing",
			"Customer Verification",
			"GPS Check-Out",
			"Completed",
		]
		canonical = STATUS_ALIASES.get(doc.status, doc.status)
		if canonical in order:
			idx = order.index(canonical)
			if idx < len(order) - 1:
				doc.status = order[idx + 1]
	doc.append(
		"visit_timeline",
		{
			"activity": f"Status → {doc.status}",
			"user": frappe.session.user,
			"time": now_datetime(),
			"remarks": "",
		},
	)
	doc.save(ignore_permissions=True)
	doc._sync_parent_docs()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def create_diagnosis(service_request=None, engineer_visit=None, force=1):
	"""Create Diagnosis / RCA (Failure Analysis) from visit or service request."""
	if engineer_visit:
		from swiftservice.swiftservice.doctype.failure_analysis.failure_analysis import create_from_visit

		doc = create_from_visit(engineer_visit, force=cint(force))
		frappe.db.commit()
		return doc.as_dict()
	if not service_request:
		frappe.throw("service_request or engineer_visit is required")
	existing = frappe.db.get_value(
		"Failure Analysis",
		{"service_request": service_request, "docstatus": ["<", 2]},
		"name",
	)
	if existing and not cint(force):
		return frappe.get_doc("Failure Analysis", existing).as_dict()
	doc = frappe.get_doc(
		{
			"doctype": "Failure Analysis",
			"naming_series": "DX-.YYYY.-.#####",
			"service_request": service_request,
			"status": "Draft",
			"source": "Manual",
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def advance_diagnosis_status(name, status=None):
	doc = frappe.get_doc("Failure Analysis", name)
	doc.advance_status(status=status)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def create_service_report(
	service_request=None,
	engineer_visit=None,
	repair_order=None,
	replacement_case=None,
	work_done=None,
	customer_signature=None,
	force=0,
):
	"""Generate Service Report snapshot from linked docs (manual blank create discouraged)."""
	if not service_request and engineer_visit:
		service_request = frappe.db.get_value("Engineer Visit", engineer_visit, "service_request")
	if not service_request and repair_order:
		service_request = frappe.db.get_value("Repair Order", repair_order, "service_request")
	if not service_request:
		frappe.throw("service_request is required")
	from swiftservice.swiftservice.doctype.service_report.service_report import generate_from_source

	doc = generate_from_source(
		service_request=service_request,
		engineer_visit=engineer_visit,
		repair_order=repair_order,
		replacement_case=replacement_case,
		work_done=work_done,
		force=cint(force),
	)
	if work_done and not doc.work_done:
		doc.work_done = work_done
		doc.save(ignore_permissions=True)
	if customer_signature:
		doc.customer_signature = customer_signature
		doc.customer_verification = 1
		doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def advance_service_report(name, status=None):
	doc = frappe.get_doc("Service Report", name)
	doc.advance_status(status=status)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def service_report_engineer_review(name):
	doc = frappe.get_doc("Service Report", name)
	doc.engineer_review()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def service_report_customer_sign(name, signature=None, refused=0, refusal_reason=None, contact_name=None):
	doc = frappe.get_doc("Service Report", name)
	doc.capture_customer_signature(
		signature=signature,
		refused=refused,
		refusal_reason=refusal_reason,
		contact_name=contact_name,
	)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def service_report_manager_verify(name, remarks=None):
	doc = frappe.get_doc("Service Report", name)
	doc.manager_verify(remarks=remarks)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def service_report_billing_ready(name):
	doc = frappe.get_doc("Service Report", name)
	doc.mark_billing_ready()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def service_report_create_revision(name):
	doc = frappe.get_doc("Service Report", name)
	rev = doc.create_revision()
	frappe.db.commit()
	return rev.as_dict()


@frappe.whitelist()
def create_feedback(
	service_request=None,
	customer=None,
	rating=None,
	feedback_text=None,
	service_report=None,
	service_billing=None,
	nps_score=None,
	force=0,
):
	"""Create / request Customer Feedback snapshot (separate from Service Request)."""
	if not service_request and service_report:
		service_request = frappe.db.get_value("Service Report", service_report, "service_request")
	if not service_request and service_billing:
		service_request = frappe.db.get_value("Service Billing", service_billing, "service_request")
	if not service_request:
		frappe.throw("service_request is required")
	from swiftservice.swiftservice.doctype.customer_feedback.customer_feedback import generate_from_source

	doc = generate_from_source(
		service_request=service_request,
		service_report=service_report,
		service_billing=service_billing,
		force=cint(force),
		request=True,
	)
	if customer and not doc.customer:
		doc.customer = customer
	if rating not in (None, ""):
		doc.csat_rating = str(cint(rating))
		doc.rating = doc.csat_rating
	if nps_score not in (None, ""):
		doc.nps_score = cint(nps_score)
	if feedback_text:
		doc.feedback_text = feedback_text
		doc.positive_feedback = feedback_text
	if rating or feedback_text or nps_score not in (None, ""):
		doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def advance_feedback(name, status=None):
	doc = frappe.get_doc("Customer Feedback", name)
	doc.advance_status(status=status)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def feedback_request(name):
	doc = frappe.get_doc("Customer Feedback", name)
	doc.request_feedback()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def feedback_submit_response(
	name,
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
	doc = frappe.get_doc("Customer Feedback", name)
	doc.submit_response(
		csat_rating=csat_rating,
		nps_score=nps_score,
		issue_resolved=issue_resolved,
		positive_feedback=positive_feedback,
		complaint_text=complaint_text,
		suggestions=suggestions,
		would_recommend_us=would_recommend_us,
		would_call_again=would_call_again,
		complaint_against_engineer=complaint_against_engineer,
		complaint_category=complaint_category,
		complaint_details=complaint_details,
		rating_details=rating_details,
	)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def feedback_review(name, remarks=None):
	doc = frappe.get_doc("Customer Feedback", name)
	doc.mark_reviewed(remarks=remarks)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def feedback_resolve_escalation(name, remarks=None):
	doc = frappe.get_doc("Customer Feedback", name)
	doc.resolve_escalation(remarks=remarks)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def feedback_close(name):
	doc = frappe.get_doc("Customer Feedback", name)
	doc.close_feedback()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def feedback_create_revision(name):
	doc = frappe.get_doc("Customer Feedback", name)
	rev = doc.create_revision()
	frappe.db.commit()
	return rev.as_dict()


@frappe.whitelist()
def create_service_closure(service_request=None, force=0, run_validation=1):
	"""System-generated Service Closure governance document."""
	if not service_request:
		frappe.throw("service_request is required")
	from swiftservice.swiftservice.doctype.service_closure.service_closure import generate_from_source

	doc = generate_from_source(
		service_request=service_request,
		force=cint(force),
		run_validation=cint(run_validation),
	)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def advance_service_closure(name, status=None):
	doc = frappe.get_doc("Service Closure", name)
	doc.advance_status(status=status)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def closure_run_validation(name):
	doc = frappe.get_doc("Service Closure", name)
	doc.populate_from_sources()
	doc.run_validation()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def closure_approve(name, remarks=None):
	doc = frappe.get_doc("Service Closure", name)
	doc.approve_closure(remarks=remarks)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def closure_execute_close(name, closure_reason=None):
	doc = frappe.get_doc("Service Closure", name)
	if closure_reason:
		doc.closure_reason = closure_reason
	doc.execute_close()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def closure_archive(name):
	doc = frappe.get_doc("Service Closure", name)
	doc.archive()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def closure_request_reopen(name, reason=None):
	doc = frappe.get_doc("Service Closure", name)
	doc.request_reopen(reason=reason)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def closure_approve_reopen(name):
	doc = frappe.get_doc("Service Closure", name)
	doc.approve_reopen()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def create_service_estimate(service_request, labour_amount=0, travel_amount=0, spare_amount=0, notes=None):
	total = flt(labour_amount) + flt(travel_amount) + flt(spare_amount)
	doc = frappe.get_doc(
		{
			"doctype": "Service Estimate",
			"service_request": service_request,
			"labour_amount": labour_amount,
			"travel_amount": travel_amount,
			"spare_amount": spare_amount,
			"total_amount": total,
			"notes": notes,
			"status": "Draft",
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def create_service_billing(
	service_request=None,
	service_report=None,
	repair_order=None,
	replacement_case=None,
	force=0,
):
	if not service_request and service_report:
		service_request = frappe.db.get_value("Service Report", service_report, "service_request")
	if not service_request and repair_order:
		service_request = frappe.db.get_value("Repair Order", repair_order, "service_request")
	if not service_request:
		frappe.throw("service_request is required")
	from swiftservice.swiftservice.doctype.service_billing.service_billing import generate_from_source

	doc = generate_from_source(
		service_request=service_request,
		service_report=service_report,
		repair_order=repair_order,
		replacement_case=replacement_case,
		force=cint(force),
	)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def advance_service_billing(name, status=None):
	doc = frappe.get_doc("Service Billing", name)
	doc.advance_status(status=status)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def billing_approve(name, method=None, remarks=None):
	doc = frappe.get_doc("Service Billing", name)
	doc.approve_billing(method=method, remarks=remarks)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def billing_generate_invoice(name):
	doc = frappe.get_doc("Service Billing", name)
	invoice = doc.generate_sales_invoice()
	frappe.db.commit()
	doc.reload()
	return {"sales_invoice": invoice, **doc.as_dict()}


@frappe.whitelist()
def billing_record_payment(name, amount=None, mode="UPI", reference=None):
	doc = frappe.get_doc("Service Billing", name)
	amt = amount if amount not in (None, "") else doc.outstanding_amount or doc.invoice_amount
	doc.record_payment(amount=amt, mode=mode, reference=reference)
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def billing_warranty_settle(name):
	doc = frappe.get_doc("Service Billing", name)
	doc.mark_warranty_settlement()
	frappe.db.commit()
	return doc.as_dict()


@frappe.whitelist()
def billing_create_credit_note(name, amount=None, reason=None):
	doc = frappe.get_doc("Service Billing", name)
	cn = doc.create_credit_note(amount=amount, reason=reason)
	frappe.db.commit()
	doc.reload()
	return {"credit_note": cn, **doc.as_dict()}


@frappe.whitelist()
def create_service_invoice(service_request, estimate_name=None, billing_name=None):
	"""Create Sales Invoice — prefers Service Billing; estimate kept for legacy."""
	if billing_name and frappe.db.exists("Service Billing", billing_name):
		doc = frappe.get_doc("Service Billing", billing_name)
		invoice = doc.generate_sales_invoice()
		frappe.db.commit()
		doc.reload()
		return {
			"name": doc.name,
			"sales_invoice": invoice or doc.sales_invoice,
			"service_request": service_request,
			"grand_total": doc.invoice_amount or doc.grand_total,
		}

	bill = frappe.db.get_value(
		"Service Billing",
		{
			"service_request": service_request,
			"docstatus": ["<", 2],
			"status": ["not in", ["Cancelled", "Closed"]],
		},
		"name",
		order_by="modified desc",
	)
	if bill and not estimate_name:
		doc = frappe.get_doc("Service Billing", bill)
		invoice = doc.generate_sales_invoice()
		frappe.db.commit()
		doc.reload()
		return {
			"name": doc.name,
			"sales_invoice": invoice or doc.sales_invoice,
			"service_request": service_request,
			"grand_total": doc.invoice_amount or doc.grand_total,
		}

	sr = frappe.get_doc("Swift Service Request", service_request)
	if not sr.customer:
		frappe.throw("Customer is required for billing")

	estimate = None
	if estimate_name:
		estimate = frappe.get_doc("Service Estimate", estimate_name)

	si = frappe.new_doc("Sales Invoice")
	si.customer = sr.customer
	si.due_date = nowdate()
	amount = estimate.total_amount if estimate else 0
	item_code = None
	for candidate in ("Service Charges", "Servicing", "Labour Charges"):
		if frappe.db.exists("Item", candidate):
			item_code = candidate
			break
	if not item_code:
		items = frappe.get_all("Item", filters={"is_sales_item": 1}, pluck="name", limit=1)
		item_code = items[0] if items else None
	if not item_code:
		frappe.throw("No sales Item found to bill. Create a service Item in ERPNext first.")

	si.append(
		"items",
		{
			"item_code": item_code,
			"qty": 1,
			"rate": amount or 0,
			"description": f"Service for {sr.name}: {sr.subject or ''}",
		},
	)
	si.insert(ignore_permissions=True)

	if estimate:
		estimate.status = "Invoiced"
		estimate.sales_invoice = si.name
		estimate.save(ignore_permissions=True)

	# Feedback / Closure modules own SSR completion — do not force Completed here
	frappe.db.commit()
	return {"sales_invoice": si.name, "service_request": sr.name, "grand_total": si.grand_total}
