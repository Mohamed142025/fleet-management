# Copyright (c) 2026, Mohamed Sayed and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from ms_fleet import constants as C


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = get_rows(filters)
	outside = [r for r in rows if not r.is_company_vehicle]
	summary = [
		{"label": _("الرحلات"), "value": len(rows), "datatype": "Int"},
		{"label": _("الكيلومترات"), "value": flt(sum(flt(r.km) for r in rows), 1), "datatype": "Float"},
		{"label": _("مستحقات العربيات الخارجية"), "value": flt(sum(flt(r.total_amount) for r in outside), 2), "datatype": "Currency", "indicator": "Green"},
	]
	return columns(), rows, None, None, summary


def columns():
	return [
		{"fieldname": "name", "label": _("الرحلة"), "fieldtype": "Link", "options": "Fleet Trip", "width": 130},
		{"fieldname": "scheduled_time", "label": _("الميعاد"), "fieldtype": "Datetime", "width": 150},
		{"fieldname": "status", "label": _("الحالة"), "fieldtype": "Data", "width": 120},
		{"fieldname": "project", "label": _("المشروع"), "fieldtype": "Link", "options": "Project", "width": 110},
		{"fieldname": "vehicle_type", "label": _("النوع"), "fieldtype": "Link", "options": "Fleet Vehicle Type", "width": 110},
		{"fieldname": "billing_mode", "label": _("الحساب"), "fieldtype": "Data", "width": 80},
		{"fieldname": "driver_name", "label": _("السواق"), "fieldtype": "Data", "width": 140},
		{"fieldname": "vehicle", "label": _("العربية"), "fieldtype": "Link", "options": "Vehicle", "width": 100},
		{"fieldname": "supplier", "label": _("المورد"), "fieldtype": "Link", "options": "Supplier", "width": 130},
		{"fieldname": "is_company_vehicle", "label": _("عربية شركة"), "fieldtype": "Check", "width": 80},
		{"fieldname": "km", "label": _("كم"), "fieldtype": "Float", "precision": 1, "width": 80},
		{"fieldname": "waiting_minutes", "label": _("انتظار (دقيقة)"), "fieldtype": "Int", "width": 90},
		{"fieldname": "total_amount", "label": _("المستحق"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "purchase_invoice", "label": _("الفاتورة"), "fieldtype": "Link", "options": "Purchase Invoice", "width": 140},
	]


def get_rows(filters):
	conditions = {"company": filters.company}
	for field in ("project", "supplier", "driver", "vehicle_type", "status"):
		if filters.get(field):
			conditions[field] = filters.get(field)
	if filters.from_date and filters.to_date:
		conditions["scheduled_time"] = ["between", [f"{filters.from_date} 00:00:00", f"{filters.to_date} 23:59:59"]]
	rows = frappe.get_list(
		"Fleet Trip",
		filters=conditions,
		fields=[
			"name", "scheduled_time", "status", "project", "vehicle_type", "billing_mode", "driver_name", "vehicle", "supplier",
			"is_company_vehicle", "actual_km", "manual_km", "distance_source", "waiting_minutes", "total_amount", "purchase_invoice",
		],
		order_by="scheduled_time desc",
	)
	for row in rows:
		row.km = row.manual_km if row.distance_source == C.DISTANCE_MANUAL else row.actual_km
	return rows
