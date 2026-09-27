"""The driver app's API (/driver).

Drivers are website users with the Fleet Driver role and a Driver record pointing at them. Every
call here works only on the calling driver's own trips and account, and never returns the
receivers' confirmation codes. Actions queued while the phone was offline carry the time they
were pressed (client_time); it is accepted when it falls between the assignment and now.
"""

import base64

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_to_date, cint, flt, get_datetime, get_url, now_datetime

from ms_fleet import constants as C
from ms_fleet import trip as fleet_trip

TRIP_FIELDS = (
	"name", "status", "project", "vehicle_type", "billing_mode", "scheduled_time", "planned_days", "request_notes",
	"vehicle", "is_company_vehicle", "assigned_on", "response_due", "accepted_on", "started_on", "finished_on",
	"odometer_start", "odometer_end", "planned_km", "actual_km", "manual_km", "distance_source", "expected_amount",
	"total_amount", "base_amount", "return_amount", "surcharge_amount", "waiting_amount", "daily_amount",
	"overtime_amount", "cancellation_compensation", "cancel_reason", "purchase_invoice", "payment_approved_on",
)
STOP_FIELDS = (
	"name", "idx", "location", "purpose", "notes", "latitude", "longitude", "arrived_on", "departed_on",
	"out_of_range", "photo", "confirmed", "confirmed_via", "waiting_minutes", "leg_km",
)
EARNING_STATES = (C.FINISHED, C.APPROVED, C.INVOICED, C.CANCELLED)


def current_driver():
	if frappe.session.user == "Guest":
		frappe.throw(_("سجّل الدخول الأول."), frappe.AuthenticationError)
	driver = frappe.db.get_value(
		"Driver", {"user": frappe.session.user}, ["name", "full_name", "status", "transporter", "cell_number"], as_dict=True
	)
	if not driver or driver.status != "Active":
		frappe.throw(_("الحساب ده مش مربوط بسواق نشط."), frappe.PermissionError)
	return driver


def own_trip(name):
	driver = current_driver()
	trip = fleet_trip.get_trip(name)
	if trip.driver != driver.name:
		frappe.throw(_("الرحلة دي مش ليك."), frappe.PermissionError)
	return trip


def event_time(client_time, trip):
	"""When the driver pressed the button: the phone's time for a queued action, if believable."""
	now = now_datetime()
	if not client_time:
		return now
	try:
		moment = get_datetime(client_time)
	except Exception:
		return now
	moment = moment.replace(tzinfo=None, microsecond=0)
	earliest = get_datetime(trip.assigned_on) if trip.assigned_on else add_to_date(now, days=-2)
	return moment if earliest <= moment <= add_to_date(now, minutes=2) else now


def trip_data(trip):
	data = {field: trip.get(field) for field in TRIP_FIELDS}
	data["project_name"] = frappe.get_cached_value("Project", trip.project, "project_name")
	data["stops"] = [{field: row.get(field) for field in STOP_FIELDS} for row in trip.stops]
	for stop in data["stops"]:
		stop["needs_photo"] = stop["purpose"] in C.PHOTO_PURPOSES
		stop["needs_confirmation"] = stop["purpose"] in C.CONFIRM_PURPOSES
	return data


# Session -------------------------------------------------------------------------------


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=10 * 60)
def login(mobile, password):
	"""Drivers sign in with their mobile number."""
	mobile = (mobile or "").strip().replace(" ", "")
	user = frappe.db.get_value("User", {"mobile_no": mobile, "enabled": 1}, "name")
	if not user or not frappe.db.exists("Driver", {"user": user, "status": "Active"}):
		frappe.throw(_("رقم الموبايل أو كلمة السر غلط."), frappe.AuthenticationError)
	frappe.local.login_manager.authenticate(user=user, pwd=password)
	frappe.local.login_manager.post_login()
	return session()


@frappe.whitelist(methods=["POST"])
def logout():
	frappe.local.login_manager.logout()
	return True


@frappe.whitelist()
def session():
	driver = current_driver()
	vehicles = frappe.get_all(
		"Vehicle",
		filters={"custom_fleet_driver": driver.name},
		fields=["name", "custom_fleet_vehicle_type as vehicle_type", "custom_fleet_ownership as ownership", "make", "model"],
	)
	return {
		"user": frappe.session.user,
		"driver": driver.name,
		"full_name": driver.full_name,
		"mobile": driver.cell_number,
		"vehicles": vehicles,
		"csrf_token": frappe.sessions.get_csrf_token(),
	}


# Trips ---------------------------------------------------------------------------------


@frappe.whitelist()
def trips(scope="active"):
	driver = current_driver()
	states = list(C.ACTIVE_STATES) if scope == "active" else [C.FINISHED, C.APPROVED, C.INVOICED, C.CANCELLED, C.DECLINED]
	names = frappe.get_all(
		"Fleet Trip",
		filters={"driver": driver.name, "status": ["in", states]},
		pluck="name",
		order_by="scheduled_time asc" if scope == "active" else "modified desc",
		limit=50,
	)
	return [trip_data(frappe.get_doc("Fleet Trip", name)) for name in names]


@frappe.whitelist()
def trip(name):
	driver = current_driver()
	doc = frappe.get_doc("Fleet Trip", name)
	if doc.driver != driver.name:
		frappe.throw(_("الرحلة دي مش ليك."), frappe.PermissionError)
	return trip_data(doc)


@frappe.whitelist(methods=["POST"])
def accept(name, client_time=None):
	doc = own_trip(name)
	fleet_trip.accept(doc)
	return trip_data(doc)


@frappe.whitelist(methods=["POST"])
def decline(name, reason, client_time=None):
	doc = own_trip(name)
	fleet_trip.decline(doc, reason)
	return trip_data(doc)


@frappe.whitelist(methods=["POST"])
def start(name, odometer=None, lat=None, lng=None, accuracy=None, client_time=None):
	doc = own_trip(name)
	fleet_trip.start(doc, event_time(client_time, doc), odometer)
	return trip_data(doc)


@frappe.whitelist(methods=["POST"])
def arrive(name, stop, lat=None, lng=None, accuracy=None, client_time=None):
	doc = own_trip(name)
	fleet_trip.arrive(doc, stop, event_time(client_time, doc), flt(lat) or None, flt(lng) or None, accuracy)
	return trip_data(doc)


@frappe.whitelist(methods=["POST"])
def photo(name, stop, data, filename=None, client_time=None):
	"""data: the picture as base64 (optionally a data: URL)."""
	doc = own_trip(name)
	if "," in (data or "")[:100]:
		data = data.split(",", 1)[1]
	try:
		content = base64.b64decode(data)
	except Exception:
		frappe.throw(_("الصورة مش سليمة."))
	if len(content) > 8 * 1024 * 1024:
		frappe.throw(_("الصورة كبيرة، صوّرها تاني."))
	fleet_trip.attach_photo(doc, stop, filename, content)
	return trip_data(doc)


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=20, seconds=10 * 60)
def confirm_code(name, stop, code, client_time=None):
	doc = own_trip(name)
	error = fleet_trip.confirm_by_code(doc, stop, code, event_time(client_time, doc))
	data = trip_data(doc)
	data["code_error"] = error
	return data


@frappe.whitelist(methods=["POST"])
def depart(name, stop, lat=None, lng=None, accuracy=None, client_time=None):
	doc = own_trip(name)
	fleet_trip.depart(doc, stop, event_time(client_time, doc))
	return trip_data(doc)


@frappe.whitelist(methods=["POST"])
def finish(name, odometer=None, lat=None, lng=None, accuracy=None, client_time=None):
	doc = own_trip(name)
	fleet_trip.finish(doc, event_time(client_time, doc), odometer)
	return trip_data(doc)


# Money ---------------------------------------------------------------------------------


@frappe.whitelist()
def earnings():
	driver = current_driver()
	rows = frappe.get_all(
		"Fleet Trip",
		filters={"driver": driver.name, "status": ["in", EARNING_STATES], "is_company_vehicle": 0},
		fields=["name", "status", "project", "finished_on", "cancelled_on", "total_amount", "purchase_invoice"],
		order_by="modified desc",
		limit=100,
	)
	rows = [r for r in rows if r.status != C.CANCELLED or flt(r.total_amount)]
	invoices = {r.purchase_invoice for r in rows if r.purchase_invoice}
	paid = {
		i.name: i
		for i in frappe.get_all(
			"Purchase Invoice", filters={"name": ["in", list(invoices)]}, fields=["name", "docstatus", "outstanding_amount", "grand_total"]
		)
	} if invoices else {}
	for row in rows:
		invoice = paid.get(row.purchase_invoice)
		row.paid = bool(invoice and invoice.docstatus == 1 and not flt(invoice.outstanding_amount))
	summary = {
		"pending_review": sum(flt(r.total_amount) for r in rows if r.status == C.FINISHED),
		"approved": sum(flt(r.total_amount) for r in rows if r.status in (C.APPROVED, C.INVOICED, C.CANCELLED) and not r.paid),
		"paid": sum(flt(r.total_amount) for r in rows if r.paid),
	}
	return {"summary": summary, "trips": rows}


@frappe.whitelist()
def statement():
	"""The supplier account: invoices, payments and the balance the company owes."""
	driver = current_driver()
	if not driver.transporter:
		return {"entries": [], "balance": 0}
	gle = frappe.qb.DocType("GL Entry")
	entries = (
		frappe.qb.from_(gle)
		.select(gle.posting_date, gle.voucher_type, gle.voucher_no, gle.debit, gle.credit)
		.where((gle.party_type == "Supplier") & (gle.party == driver.transporter) & (gle.is_cancelled == 0))
		.orderby(gle.posting_date, order=frappe.qb.desc)
		.orderby(gle.creation, order=frappe.qb.desc)
		.limit(100)
		.run(as_dict=True)
	)
	balance = (
		frappe.qb.from_(gle)
		.select(frappe.query_builder.functions.Sum(gle.credit - gle.debit))
		.where((gle.party_type == "Supplier") & (gle.party == driver.transporter) & (gle.is_cancelled == 0))
		.run()[0][0]
	)
	return {"entries": entries, "balance": flt(balance)}


# The page and its service worker ------------------------------------------------------------


@frappe.whitelist(allow_guest=True, methods=["GET"])
def service_worker(config=None):
	"""The app's service worker, served so that it may control /driver (it lives under /assets)."""
	from werkzeug.wrappers import Response

	path = frappe.get_app_path("ms_fleet", "public", "driver", "sw.js")
	with open(path, encoding="utf-8") as f:
		body = f.read()
	response = Response(body, mimetype="application/javascript")
	response.headers["Service-Worker-Allowed"] = "/driver"
	response.headers["Cache-Control"] = "no-cache"
	return response


@frappe.whitelist(allow_guest=True, methods=["GET"])
def manifest():
	from werkzeug.wrappers import Response
	import json

	settings = frappe.get_cached_doc("Fleet Settings")
	icon = settings.app_logo or "/assets/ms_fleet/driver-icons/icon-512.png"
	body = {
		"name": settings.app_name or "MS Fleet",
		"short_name": settings.app_name or "MS Fleet",
		"start_url": "/driver",
		"scope": "/driver",
		"display": "standalone",
		"dir": "rtl",
		"lang": "ar",
		"theme_color": settings.theme_color or "#0E3B2E",
		"background_color": "#ffffff",
		"icons": [
			{"src": get_url(icon), "sizes": "512x512", "type": "image/png", "purpose": "any"},
			{"src": get_url("/assets/ms_fleet/driver-icons/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
			{"src": get_url("/assets/ms_fleet/driver-icons/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
		],
	}
	return Response(json.dumps(body, ensure_ascii=False), mimetype="application/manifest+json")
