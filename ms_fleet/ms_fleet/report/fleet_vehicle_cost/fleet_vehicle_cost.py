# Copyright (c) 2026, Mohamed Sayed and contributors
# For license information, please see license.txt

"""Company vehicles: kilometres driven on trips, fuel and service costs from Vehicle Log (HRMS), the
cost of a kilometre, and the outside rate for the same vehicle type to compare with. Depreciation
is not included."""

import frappe
from frappe import _
from frappe.utils import flt

from ms_fleet import constants as C


def execute(filters=None):
	filters = frappe._dict(filters or {})
	vehicle_filters = {"custom_fleet_ownership": C.COMPANY_OWNED}
	if filters.vehicle:
		vehicle_filters["name"] = filters.vehicle
	if filters.company:
		vehicle_filters["company"] = ["in", [filters.company, None, ""]]
	vehicles = frappe.get_all("Vehicle", filters=vehicle_filters, fields=["name", "custom_fleet_vehicle_type as vehicle_type"])
	span = [f"{filters.from_date} 00:00:00", f"{filters.to_date} 23:59:59"]
	rows = []
	for vehicle in vehicles:
		km = sum(
			flt(k)
			for k in frappe.get_all(
				"Fleet Trip",
				filters={"vehicle": vehicle.name, "is_company_vehicle": 1, "status": C.FINISHED, "finished_on": ["between", span]},
				pluck="actual_km",
			)
		)
		logs = frappe.get_all(
			"Vehicle Log",
			filters={"license_plate": vehicle.name, "docstatus": 1, "date": ["between", [filters.from_date, filters.to_date]]},
			fields=["name", "fuel_qty", "price"],
		)
		fuel = sum(flt(log.fuel_qty) * flt(log.price) for log in logs)
		service = (
			sum(flt(v) for v in frappe.get_all("Vehicle Service", filters={"parent": ["in", [log.name for log in logs]]}, pluck="expense_amount"))
			if logs
			else 0
		)
		outside_rate = flt(frappe.db.get_value("Fleet Vehicle Type", vehicle.vehicle_type, "rate_per_km")) if vehicle.vehicle_type else 0
		per_km = (fuel + service) / km if km else 0
		rows.append(
			{
				"vehicle": vehicle.name,
				"vehicle_type": vehicle.vehicle_type,
				"km": km,
				"fuel": fuel,
				"service": service,
				"cost": fuel + service,
				"cost_per_km": per_km,
				"outside_rate": outside_rate,
				"saving_per_km": outside_rate - per_km if km else 0,
			}
		)
	return columns(), rows


def columns():
	return [
		{"fieldname": "vehicle", "label": _("العربية"), "fieldtype": "Link", "options": "Vehicle", "width": 120},
		{"fieldname": "vehicle_type", "label": _("النوع"), "fieldtype": "Link", "options": "Fleet Vehicle Type", "width": 120},
		{"fieldname": "km", "label": _("كم في الرحلات"), "fieldtype": "Float", "precision": 1, "width": 110},
		{"fieldname": "fuel", "label": _("البنزين"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "service", "label": _("الصيانة"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "cost", "label": _("التكلفة"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "cost_per_km", "label": _("تكلفة الكيلو"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "outside_rate", "label": _("سعر الكيلو الخارجي"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "saving_per_km", "label": _("التوفير في الكيلو"), "fieldtype": "Currency", "width": 130},
	]
