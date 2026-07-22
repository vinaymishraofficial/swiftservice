import frappe


SERVICE_ROLES = (
	"Service Manager",
	"Service Coordinator",
	"Field Engineer",
)


def after_migrate():
	"""Keep SwiftService launcher icons after migrate orphan cleanup; ensure service roles exist."""
	_ensure_service_roles()

	from frappe.desk.doctype.desktop_icon.desktop_icon import (
		clear_desktop_icons_cache,
		create_desktop_icons_from_installed_apps,
	)

	create_desktop_icons_from_installed_apps()
	clear_desktop_icons_cache()
	frappe.cache.delete_key("desktop_icons")


def _ensure_service_roles():
	for role in SERVICE_ROLES:
		if not frappe.db.exists("Role", role):
			doc = frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role,
					"desk_access": 1,
				}
			)
			doc.insert(ignore_permissions=True)
			frappe.db.commit()
