import frappe
from frappe import _
from frappe.utils import cint, get_system_timezone

no_cache = 1


def get_context():
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/swiftservice"
		raise frappe.Redirect

	context = frappe._dict()
	context.boot = get_boot()
	context.asset_version = frappe.utils.cint(frappe.utils.now_datetime().timestamp())
	return context


def get_boot():
	user = frappe.session.user
	user_info = {}
	if user and user != "Guest":
		user_info = frappe.db.get_value(
			"User",
			user,
			["name", "full_name", "user_image", "email"],
			as_dict=True,
		) or {}

	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"default_route": "/swiftservice",
			"site_name": frappe.local.site,
			"csrf_token": frappe.sessions.get_csrf_token(),
			"setup_complete": cint(frappe.get_system_settings("setup_complete")),
			"sysdefaults": frappe.defaults.get_defaults(),
			"timezone": {
				"system": get_system_timezone(),
				"user": frappe.db.get_value("User", user, "time_zone") or get_system_timezone(),
			},
			"user": user_info,
		}
	)


@frappe.whitelist()
def check_app_permission():
	return frappe.session.user != "Guest"
