# Copyright (c) 2026, Mohamed Sayed and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from ms_fleet import constants as C

# What an outside vehicle has earned: finished (under review), approved, invoiced, or cancelled
# with a compensation.
EARNED = (C.FINISHED, C.APPROVED, C.INVOICED, C.CANCELLED)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions = {"company": filters.company, "status": ["in", EARNED]}
	if filters.project:
		conditions["project"] = filters.project
	if filters.from_date and filters.to_date:
		conditions["scheduled_time"] = ["between", [f"{filters.from_date} 00:00:00", f"{filters.to_date} 23:59:59"]]
	trips = frappe.get_list(
		"Fleet Trip",
		filters=conditions,
		fields=["project", "status", "is_company_vehicle", "actual_km", "manual_km", "distance_source", "total_amount"],
	)
	by_project = {}
	for trip in trips:
		row = by_project.setdefault(trip.project, frappe._dict(project=trip.project, trips=0, outside_amount=0, under_review=0, outside_km=0, company_km=0))
		km = flt(trip.manual_km if trip.distance_source == C.DISTANCE_MANUAL else trip.actual_km)
		if trip.status == C.CANCELLED and not flt(trip.total_amount):
			continue
		row.trips += 1
		if trip.is_company_vehicle:
			row.company_km += km
			continue
		row.outside_km += km
		if trip.status == C.FINISHED:
			row.under_review += flt(trip.total_amount)
		else:
			row.outside_amount += flt(trip.total_amount)
	names = dict(frappe.get_all("Project", filters={"name": ["in", list(by_project)]}, fields=["name", "project_name"], as_list=True)) if by_project else {}
	rows = sorted(by_project.values(), key=lambda r: -(r.outside_amount + r.under_review))
	for row in rows:
		row.project_name = names.get(row.project)
	chart = {
		"data": {"labels": [r.project for r in rows[:15]], "datasets": [{"name": _("المستحقات"), "values": [flt(r.outside_amount + r.under_review, 2) for r in rows[:15]]}]},
		"type": "bar",
	}
	return columns(), rows, None, chart


def columns():
	return [
		{"fieldname": "project", "label": _("المشروع"), "fieldtype": "Link", "options": "Project", "width": 120},
		{"fieldname": "project_name", "label": _("اسم المشروع"), "fieldtype": "Data", "width": 200},
		{"fieldname": "trips", "label": _("الرحلات"), "fieldtype": "Int", "width": 90},
		{"fieldname": "outside_amount", "label": _("مستحقات معتمدة"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "under_review", "label": _("قيد المراجعة"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "outside_km", "label": _("كم خارجي"), "fieldtype": "Float", "precision": 1, "width": 100},
		{"fieldname": "company_km", "label": _("كم عربيات الشركة"), "fieldtype": "Float", "precision": 1, "width": 130},
	]
