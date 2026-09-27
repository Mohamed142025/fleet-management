"""Paying outside vehicles: the trips approved for payment (and cancelled trips with a
compensation) become one draft Purchase Invoice per supplier, a line per trip carrying its
project and cost center, so the transport cost lands on the project. The accountant reviews and
submits the invoice (the supplier's tax withholding category applies as usual) and pays it with
a Payment Entry. Cancelling or deleting the invoice puts its trips back.
"""

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate, nowdate

from ms_fleet import constants as C


def payable_trips(company, to_date, supplier=None, from_date=None):
	trip = frappe.qb.DocType("Fleet Trip")
	when = frappe.query_builder.functions.Coalesce(trip.payment_approved_on, trip.cancelled_on)
	query = (
		frappe.qb.from_(trip)
		.select(trip.name)
		.where(
			(trip.company == company)
			& (trip.is_company_vehicle == 0)
			& (trip.supplier.isnotnull())
			& (trip.purchase_invoice.isnull() | (trip.purchase_invoice == ""))
			& (
				(trip.status == C.APPROVED)
				| ((trip.status == C.CANCELLED) & (trip.cancellation_compensation > 0))
			)
			& (when <= get_datetime(f"{getdate(to_date)} 23:59:59"))
		)
		.orderby(trip.supplier)
		.orderby(when)
	)
	if supplier:
		query = query.where(trip.supplier == supplier)
	if from_date:
		query = query.where(when >= get_datetime(getdate(from_date)))
	return query.run(pluck=True)


@frappe.whitelist()
def make_invoices(company, to_date, supplier=None, from_date=None):
	if not frappe.has_permission("Purchase Invoice", "create"):
		frappe.throw(_("محتاج صلاحية إنشاء فاتورة مشتريات."), frappe.PermissionError)
	by_supplier = {}
	for name in payable_trips(company, to_date, supplier, from_date):
		trip = frappe.get_doc("Fleet Trip", name, for_update=True)
		by_supplier.setdefault(trip.supplier, []).append(trip)
	if not by_supplier:
		frappe.throw(_("مفيش رحلات معتمدة للصرف في الفترة دي."))

	invoices = []
	for supplier_name, trips in by_supplier.items():
		invoice = frappe.new_doc("Purchase Invoice")
		invoice.update({"supplier": supplier_name, "company": company, "posting_date": nowdate(), "set_posting_time": 1})
		for trip in trips:
			item = frappe.get_cached_value("Fleet Vehicle Type", trip.vehicle_type, "service_item")
			if not item:
				frappe.throw(_("حدد صنف الخدمة لنوع العربية «{0}» الأول.").format(trip.vehicle_type))
			invoice.append(
				"items",
				{
					"item_code": item,
					"qty": 1,
					"rate": flt(trip.total_amount),
					"description": describe(trip),
					"project": trip.project,
					"cost_center": trip.cost_center,
					"custom_fleet_trip": trip.name,
				},
			)
		invoice.set_missing_values()
		invoice.insert()
		for trip in trips:
			trip.purchase_invoice = invoice.name
			if trip.status == C.APPROVED:
				trip.status = C.INVOICED
			trip.flags.fleet_action = True
			trip.save(ignore_permissions=True)
		invoices.append(invoice.name)
	return invoices


def describe(trip):
	route = " ← ".join(row.location for row in trip.stops)
	lines = [_("رحلة {0} · {1} · {2}").format(trip.name, trip.driver_name or "", trip.vehicle or ""), route]
	if trip.status == C.CANCELLED:
		lines.append(_("تعويض إلغاء: {0}").format(trip.cancel_reason or ""))
	elif trip.billing_mode == C.BY_DAY:
		lines.append(_("{0} يوم، إضافي {1} ساعة").format(trip.worked_days, trip.overtime_hours))
	else:
		km = trip.manual_km if trip.distance_source == C.DISTANCE_MANUAL else trip.actual_km
		lines.append(_("{0} كم، رجوع {1} كم، انتظار {2} دقيقة").format(flt(km, 2), flt(trip.return_km, 2), trip.waiting_minutes or 0))
	return "<br>".join(frappe.utils.escape_html(line) for line in lines)


def release_trips(doc, method=None):
	"""Purchase Invoice on_cancel / on_trash: its trips can be invoiced again."""
	for name in frappe.get_all("Fleet Trip", filters={"purchase_invoice": doc.name}, pluck="name"):
		trip = frappe.get_doc("Fleet Trip", name)
		trip.purchase_invoice = None
		if trip.status == C.INVOICED:
			trip.status = C.APPROVED
		trip.flags.fleet_action = True
		trip.save(ignore_permissions=True)
