"""Install and migrate: the fleet roles, the fields ms_fleet adds to Vehicle, Driver and Purchase
Invoice Item, and the starting settings and vehicle types (first run only)."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from ms_fleet import constants as C

MODULE = "MS Fleet"
ROLES = {
	C.FLEET_MANAGER: 1,  # desk access
	C.FLEET_REQUESTER: 1,
	C.FLEET_DRIVER: 0,
	C.RELAY_CLIENT: 0,
}
VEHICLE_TYPES = ("ملاكي / تاكسي", "نقل خفيف", "نقل تقيل")


def after_install():
	after_migrate()


def after_migrate():
	make_roles()
	make_custom_fields()
	first_run()


def make_roles():
	for role, desk_access in ROLES.items():
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": desk_access}).insert(ignore_permissions=True)


def make_custom_fields():
	create_custom_fields(
		{
			"Vehicle": [
				{"fieldname": "custom_fleet_section", "label": "إدارة الحركة", "fieldtype": "Section Break",
					"insert_after": "company", "module": MODULE},
				{"fieldname": "custom_fleet_vehicle_type", "label": "نوع العربية", "fieldtype": "Link",
					"options": "Fleet Vehicle Type", "insert_after": "custom_fleet_section", "in_standard_filter": 1, "module": MODULE},
				{"fieldname": "custom_fleet_ownership", "label": "الملكية", "fieldtype": "Select", "options": f"\n{C.COMPANY_OWNED}\n{C.EXTERNAL}",
					"insert_after": "custom_fleet_vehicle_type", "in_standard_filter": 1, "module": MODULE},
				{"fieldname": "custom_fleet_column", "fieldtype": "Column Break", "insert_after": "custom_fleet_ownership", "module": MODULE},
				{"fieldname": "custom_fleet_driver", "label": "السواق", "fieldtype": "Link", "options": "Driver",
					"insert_after": "custom_fleet_column", "module": MODULE},
				{"fieldname": "custom_fleet_owner_supplier", "label": "المورد المالك", "fieldtype": "Link", "options": "Supplier",
					"insert_after": "custom_fleet_driver", "depends_on": f"eval:doc.custom_fleet_ownership=='{C.EXTERNAL}'",
					"description": "صاحب العربية اللي بتتصرفله المستحقات (لو السواق نفسه، هو نفس الـ Transporter على السواق).",
					"module": MODULE},
			],
			"Driver": [
				{"fieldname": "custom_fleet_rates_section", "label": "أسعار خاصة بالسواق", "fieldtype": "Section Break",
					"insert_after": "user", "collapsible": 1,
					"description": "لو متفق مع السواق على سعر مختلف عن تسعيرة النوع. صفر = سعر النوع.", "module": MODULE},
				{"fieldname": "custom_fleet_rates", "label": "الأسعار الخاصة", "fieldtype": "Table", "options": "Fleet Driver Rate",
					"insert_after": "custom_fleet_rates_section", "module": MODULE},
			],
			"Purchase Invoice Item": [
				{"fieldname": "custom_fleet_trip", "label": "رحلة", "fieldtype": "Link", "options": "Fleet Trip",
					"insert_after": "project", "read_only": 1, "no_copy": 1, "module": MODULE},
			],
		},
		update=True,
	)


def first_run():
	if not frappe.db.exists("Singles", {"doctype": "Fleet Settings"}):
		settings = frappe.get_single("Fleet Settings")
		settings.update(
			{
				"night_start": "22:00:00",
				"night_end": "06:00:00",
				"response_timeout_minutes": 30,
				"distance_tolerance_percent": 20,
				"geofence_radius_m": 300,
				"payment_approver_role": C.FLEET_MANAGER,
				"app_name": "MS Fleet",
				"theme_color": "#0E3B2E",
			}
		)
		settings.save(ignore_permissions=True)
		for name in VEHICLE_TYPES:
			if not frappe.db.exists("Fleet Vehicle Type", name):
				frappe.get_doc({"doctype": "Fleet Vehicle Type", "vehicle_type_name": name, "free_waiting_minutes": 15, "daily_hours": 8}).insert(
					ignore_permissions=True
				)
