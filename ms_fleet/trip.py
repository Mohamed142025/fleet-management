"""The life of a fleet trip.

A requester sends the trip to the fleet team, which assigns a vehicle and its driver. The driver
accepts or declines in the driver app, starts, presses «وصلت» and «اتحركت» at every stop (with
a photo where goods are loaded or delivered, and the receiver's confirmation on deliveries) and
finishes. The trip is then priced; for an outside vehicle it is approved for payment and later
invoiced to its supplier (ms_fleet.settlement). A company vehicle's trip ends when it finishes.

Desk actions are whitelisted here. The driver app goes through ms_fleet.api.driver, which checks
that the trip is the driver's own and then calls the step functions below.
"""

import random

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, get_datetime, get_fullname, now_datetime

from ms_fleet import constants as C
from ms_fleet import maps, notify, pricing

# Filled in when the trip is priced or run; nobody types them.
EXECUTION_FIELDS = (
	"status", "vehicle", "is_company_vehicle", "driver", "driver_user", "supplier", "assigned_by",
	"assigned_on", "response_due", "timeout_alerted", "accepted_on", "decline_reason", "started_on",
	"finished_on", "odometer_start", "odometer_end", "planned_km", "actual_km", "return_km", "manual_km",
	"distance_source", "distance_flag", "waiting_minutes", "worked_days", "overtime_hours", "holiday_days",
	"is_night", "is_holiday", "expected_amount", "cancellation_compensation", "payment_approved_by",
	"payment_approved_on", "approval_note", "cancel_reason", "cancelled_on", "purchase_invoice",
	*pricing.RATE_FIELDS, *pricing.AMOUNT_FIELDS,
)
STOP_EXECUTION_FIELDS = (
	"planned_leg_km", "arrived_on", "arrived_lat", "arrived_lng", "arrived_accuracy_m",
	"distance_from_stop_m", "out_of_range", "departed_on", "waiting_minutes", "leg_km", "photo",
	"confirmed", "confirmed_via", "confirmed_by", "confirmed_on", "confirmation_code", "code_attempts",
)
REQUEST_FIELDS = ("project", "company", "cost_center", "vehicle_type", "billing_mode", "scheduled_time", "planned_days")


def settings():
	return frappe.get_cached_doc("Fleet Settings")


def is_manager(user=None):
	roles = frappe.get_roles(user)
	return C.FLEET_MANAGER in roles or "System Manager" in roles


def check_manager():
	if not is_manager():
		frappe.throw(_("الإجراء ده لإدارة الحركة بس."), frappe.PermissionError)


def get_trip(name):
	return frappe.get_doc("Fleet Trip", name, for_update=True)


def require_status(trip, *states):
	if trip.status not in states:
		frappe.throw(_("الرحلة {0} حالتها «{1}»، والإجراء ده مش متاح دلوقتي.").format(trip.name, _(trip.status)))


def save(trip):
	trip.flags.fleet_action = True
	trip.save(ignore_permissions=True)


def comment(trip, text):
	trip.add_comment("Info", text)


# Controller rules (called from FleetTrip) -------------------------------------------------


def validate(trip):
	if trip.is_new():
		trip.status = C.DRAFT
		trip.requested_by = trip.requested_by or frappe.session.user
	elif not trip.flags.fleet_action:
		_keep_execution_fields(trip)

	if trip.status in (C.DRAFT, C.PENDING):
		_validate_request(trip)


def _keep_execution_fields(trip):
	"""A form save never changes what the actions record, and after the request is sent only the
	fleet team changes it, and only until the trip starts."""
	before = trip.get_doc_before_save()
	if not before:
		return
	for field in EXECUTION_FIELDS:
		trip.set(field, before.get(field))
	old_stops = {row.name: row for row in before.stops}
	for row in trip.stops:
		old = old_stops.get(row.name)
		for field in STOP_EXECUTION_FIELDS:
			row.set(field, old.get(field) if old else None)

	changed = any(str(trip.get(f) or "") != str(before.get(f) or "") for f in REQUEST_FIELDS) or _stops_signature(
		trip
	) != _stops_signature(before)
	if not changed:
		return
	if trip.status not in (C.DRAFT, C.PENDING) and not is_manager():
		frappe.throw(_("الرحلة اتبعتت لإدارة الحركة، والتعديل عليها من عندهم بس."))
	if trip.status in (C.IN_PROGRESS, C.FINISHED, C.APPROVED, C.INVOICED, C.CANCELLED):
		frappe.throw(_("الرحلة بدأت أو خلصت، فبياناتها ما تتعدلش."))


def _stops_signature(trip):
	return [(row.location, row.purpose, row.receiver or "") for row in trip.stops]


def _validate_request(trip):
	if not trip.stops:
		frappe.throw(_("حدد نقاط الرحلة."))
	if trip.billing_mode == C.BY_KM and len(trip.stops) < 2:
		frappe.throw(_("الرحلة بالكيلو محتاجة نقطتين على الأقل: البداية والوصول."))
	for row in trip.stops:
		if not (flt(row.latitude) or flt(row.longitude)):
			frappe.throw(_("المكان «{0}» في السطر {1} ملوش إحداثيات.").format(row.location, row.idx))
		if row.purpose in C.CONFIRM_PURPOSES and not row.receiver:
			row.receiver = trip.requested_by
	if trip.billing_mode == C.BY_DAY and cint(trip.planned_days) < 1:
		trip.planned_days = 1


# Request -------------------------------------------------------------------------------


@frappe.whitelist()
def submit_request(name):
	trip = get_trip(name)
	if trip.owner != frappe.session.user and not is_manager():
		frappe.throw(_("يبعت الطلب اللي عمله أو إدارة الحركة."), frappe.PermissionError)
	require_status(trip, C.DRAFT)
	_validate_request(trip)
	_plan_distance(trip)
	trip.status = C.PENDING
	save(trip)
	_share_with_receivers(trip)
	notify.alert(
		notify.managers(),
		_("طلب رحلة {0} من {1} لمشروع {2}، بانتظار الإسناد.").format(trip.name, get_fullname(trip.requested_by), trip.project),
		trip,
	)
	return trip.status


def _plan_distance(trip):
	route = maps.route_km([(row.latitude, row.longitude) for row in trip.stops])
	if not route:
		trip.planned_km = 0
		return
	trip.planned_km, legs = route
	for row, km in zip(trip.stops, [0, *legs]):
		row.planned_leg_km = km
	first, last = trip.stops[0], trip.stops[-1]
	back = maps.route_km([(last.latitude, last.longitude), (first.latitude, first.longitude)])
	trip.return_km = back[0] if back else 0


def _share_with_receivers(trip):
	from frappe.share import add_docshare

	for user in {row.receiver for row in trip.stops if row.receiver}:
		if not frappe.has_permission("Fleet Trip", "read", doc=trip, user=user):
			add_docshare("Fleet Trip", trip.name, user, read=1, flags={"ignore_share_permission": True})


# Assignment ----------------------------------------------------------------------------


@frappe.whitelist()
def assign(name, vehicle, driver=None):
	check_manager()
	trip = get_trip(name)
	require_status(trip, *C.ASSIGNABLE_STATES)
	vehicle = frappe.db.get_value(
		"Vehicle",
		vehicle,
		["name", "custom_fleet_vehicle_type", "custom_fleet_ownership", "custom_fleet_owner_supplier", "custom_fleet_driver"],
		as_dict=True,
	)
	if not vehicle:
		frappe.throw(_("العربية غير موجودة."))
	if vehicle.custom_fleet_vehicle_type != trip.vehicle_type:
		frappe.throw(_("العربية {0} نوعها «{1}» والرحلة محتاجة «{2}».").format(
			vehicle.name, vehicle.custom_fleet_vehicle_type or "-", trip.vehicle_type))

	driver = frappe.db.get_value(
		"Driver", driver or vehicle.custom_fleet_driver, ["name", "full_name", "status", "user", "transporter"], as_dict=True
	)
	if not driver:
		frappe.throw(_("حدد السواق، أو اربط سواق بالعربية."))
	if driver.status != "Active":
		frappe.throw(_("السواق {0} مش نشط.").format(driver.full_name))
	if not driver.user:
		frappe.throw(_("السواق {0} ملوش حساب على تطبيق السواقين. اعمله حساب من شاشة السواق.").format(driver.full_name))

	company_vehicle = vehicle.custom_fleet_ownership == C.COMPANY_OWNED
	supplier = None if company_vehicle else (driver.transporter or vehicle.custom_fleet_owner_supplier)
	if not company_vehicle and not supplier:
		frappe.throw(_("السواق {0} مش مربوط بمورد (Transporter)، فمستحقاته ما تتصرفش.").format(driver.full_name))

	previous_driver = trip.driver_user if trip.driver != driver.name else None
	rates = pricing.get_rates(trip.vehicle_type, driver.name)
	if not company_vehicle:
		key = "daily_rate" if trip.billing_mode == C.BY_DAY else "rate_per_km"
		if not flt(rates[key]) and not flt(rates["minimum_fare"]):
			frappe.throw(_("حدد تسعيرة نوع العربية «{0}» الأول.").format(trip.vehicle_type))

	trip.update(rates)
	trip.update(
		{
			"vehicle": vehicle.name,
			"is_company_vehicle": 1 if company_vehicle else 0,
			"driver": driver.name,
			"driver_name": driver.full_name,
			"driver_user": driver.user,
			"supplier": supplier,
			"assigned_by": frappe.session.user,
			"assigned_on": now_datetime(),
			"response_due": add_to_date(now_datetime(), minutes=cint(settings().response_timeout_minutes) or 30),
			"timeout_alerted": 0,
			"accepted_on": None,
			"decline_reason": None,
			"status": C.ASSIGNED,
		}
	)
	for row in trip.stops:
		if row.purpose in C.CONFIRM_PURPOSES and not row.confirmation_code:
			row.confirmation_code = f"{random.SystemRandom().randint(0, 9999):04d}"
			row.code_attempts = 0
	trip.expected_amount = 0 if company_vehicle else pricing.expected_amount(trip, settings())
	save(trip)

	comment(trip, _("أُسندت إلى {0} على العربية {1}.").format(driver.full_name, vehicle.name))
	if previous_driver:
		frappe.publish_realtime("fleet_trip", {"trip": trip.name}, user=previous_driver, after_commit=True)
		notify.push(previous_driver, _("اتلغى إسناد رحلة"), _("الرحلة {0} اتسندت لسواق تاني.").format(trip.name))
	first, last = trip.stops[0], trip.stops[-1]
	amount = "" if company_vehicle else _(" · المتوقع {0}").format(frappe.format_value(trip.expected_amount, {"fieldtype": "Currency"}))
	notify.driver(
		trip,
		_("رحلة جديدة 🚚"),
		_("{0} ← {1} · {2}{3}").format(first.location, last.location, frappe.format_value(trip.scheduled_time, {"fieldtype": "Datetime"}), amount),
	)
	for row in trip.stops:
		if row.receiver and row.confirmation_code:
			notify.alert(
				[row.receiver],
				_("كود استلام رحلة {0} عند «{1}»: {2}. اديه للسواق بعد ما يسلّم، أو أكّد الاستلام من الرحلة.").format(
					trip.name, row.location, row.confirmation_code),
				trip,
			)
	return trip.status


# The driver's steps (called by ms_fleet.api.driver) ---------------------------------------


def accept(trip):
	require_status(trip, C.ASSIGNED)
	trip.status, trip.accepted_on = C.ACCEPTED, now_datetime()
	save(trip)
	notify.alert([trip.requested_by, trip.assigned_by], _("{0} قبل الرحلة {1}.").format(trip.driver_name, trip.name), trip)


def decline(trip, reason):
	require_status(trip, C.ASSIGNED)
	if not (reason or "").strip():
		frappe.throw(_("اكتب سبب الرفض."))
	trip.status, trip.decline_reason = C.DECLINED, reason.strip()
	save(trip)
	comment(trip, _("{0} رفض الرحلة: {1}").format(trip.driver_name, trip.decline_reason))
	notify.alert(
		notify.managers(), _("{0} رفض الرحلة {1}: {2}. أسندها لسواق تاني.").format(trip.driver_name, trip.name, trip.decline_reason), trip
	)


def start(trip, at, odometer=None):
	require_status(trip, C.ACCEPTED)
	if trip.is_company_vehicle:
		if not cint(odometer):
			frappe.throw(_("اكتب قراءة العداد في البداية."))
		trip.odometer_start = cint(odometer)
	trip.status, trip.started_on = C.IN_PROGRESS, at
	save(trip)


def _stop(trip, index):
	index = cint(index)
	if index < 1 or index > len(trip.stops):
		frappe.throw(_("النقطة مش موجودة."))
	return trip.stops[index - 1]


def arrive(trip, index, at, lat=None, lng=None, accuracy=None):
	require_status(trip, C.IN_PROGRESS)
	stop = _stop(trip, index)
	if stop.arrived_on:
		return
	for earlier in trip.stops[: stop.idx - 1]:
		if not earlier.departed_on:
			frappe.throw(_("دوس «اتحركت» في «{0}» الأول.").format(earlier.location))
	if get_datetime(at) < get_datetime(trip.started_on):
		at = trip.started_on
	stop.arrived_on = at
	if lat or lng:
		stop.arrived_lat, stop.arrived_lng, stop.arrived_accuracy_m = flt(lat), flt(lng), flt(accuracy)
		stop.distance_from_stop_m = flt(maps.haversine_m(lat, lng, stop.latitude, stop.longitude), 0)
		stop.out_of_range = 1 if stop.distance_from_stop_m > (cint(settings().geofence_radius_m) or 300) else 0
	else:
		stop.out_of_range = 1
	save(trip)
	if stop.receiver and stop.purpose in C.CONFIRM_PURPOSES:
		notify.alert([stop.receiver], _("السواق {0} وصل «{1}» (رحلة {2}).").format(trip.driver_name, stop.location, trip.name), trip)


def attach_photo(trip, index, filename, content):
	require_status(trip, C.IN_PROGRESS)
	stop = _stop(trip, index)
	if not stop.arrived_on:
		frappe.throw(_("دوس «وصلت» الأول."))
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename or f"{trip.name}-{stop.idx}.jpg",
			"attached_to_doctype": "Fleet Trip",
			"attached_to_name": trip.name,
			"is_private": 1,
			"content": content,
		}
	).insert(ignore_permissions=True)
	stop.photo = file.file_url
	save(trip)
	return file.file_url


def confirm_by_code(trip, index, code, at):
	"""Returns an error message for a wrong code instead of raising, so the count of attempts is
	saved and the code cannot be guessed."""
	require_status(trip, C.IN_PROGRESS, C.FINISHED)
	stop = _stop(trip, index)
	if stop.purpose not in C.CONFIRM_PURPOSES or stop.confirmed:
		return None
	if not stop.arrived_on:
		frappe.throw(_("دوس «وصلت» الأول."))
	if cint(stop.code_attempts) >= C.MAX_CODE_ATTEMPTS:
		return _("المحاولات خلصت. المستلم يأكد من حسابه، أو كلّم إدارة الحركة.")
	if (code or "").strip() != stop.confirmation_code:
		stop.code_attempts = cint(stop.code_attempts) + 1
		save(trip)
		left = C.MAX_CODE_ATTEMPTS - stop.code_attempts
		return _("الكود غلط. فاضل {0} محاولات.").format(left) if left else _("الكود غلط، والمحاولات خلصت.")
	stop.update({"confirmed": 1, "confirmed_via": C.VIA_CODE, "confirmed_by": stop.receiver, "confirmed_on": at})
	save(trip)
	return None


def depart(trip, index, at):
	require_status(trip, C.IN_PROGRESS)
	stop = _stop(trip, index)
	if stop.departed_on:
		return
	if not stop.arrived_on:
		frappe.throw(_("دوس «وصلت» الأول."))
	if stop.purpose in C.PHOTO_PURPOSES and not stop.photo:
		frappe.throw(_("صوّر {0} في «{1}» قبل ما تتحرك.").format(_(stop.purpose), stop.location))
	stop.departed_on = max(get_datetime(at), get_datetime(stop.arrived_on))
	save(trip)


def finish(trip, at, odometer=None):
	require_status(trip, C.IN_PROGRESS)
	for stop in trip.stops:
		if not stop.arrived_on:
			frappe.throw(_("لسه ما وصلتش «{0}».").format(stop.location))
		if stop.purpose in C.PHOTO_PURPOSES and not stop.photo:
			frappe.throw(_("صوّر {0} في «{1}» الأول.").format(_(stop.purpose), stop.location))
	if trip.is_company_vehicle:
		if cint(odometer) < cint(trip.odometer_start):
			frappe.throw(_("قراءة عداد النهاية أقل من البداية ({0}).").format(trip.odometer_start))
		trip.odometer_end = cint(odometer)
	trip.finished_on = max(get_datetime(at), get_datetime(trip.stops[-1].arrived_on))
	if not trip.stops[-1].departed_on:
		trip.stops[-1].departed_on = trip.finished_on
	trip.status = C.FINISHED

	if trip.is_company_vehicle:
		trip.actual_km = cint(trip.odometer_end) - cint(trip.odometer_start)
		pricing.stop_waiting(trip.stops, 0, trip.finished_on)
		save(trip)
		frappe.db.set_value("Vehicle", trip.vehicle, "last_odometer", trip.odometer_end, update_modified=False)
		notify.alert(notify.managers(), _("رحلة {0} بعربية الشركة {1} انتهت.").format(trip.name, trip.vehicle), trip)
		return

	measure_distance(trip)
	priced = pricing.apply(trip, settings())
	save(trip)
	message = (
		_("رحلة {0} ({1}) انتهت، بانتظار المراجعة والاعتماد للصرف.").format(trip.name, trip.driver_name)
		if priced
		else _("رحلة {0} ({1}) انتهت، ومحتاجة مسافة يدوية قبل الحساب.").format(trip.name, trip.driver_name)
	)
	notify.alert(notify.managers(), message, trip)


def measure_distance(trip):
	"""The road distance through the points where the driver arrived (the stop itself when there
	was no GPS), and back to the start when the rate card pays the empty return."""
	if trip.billing_mode != C.BY_KM:
		return
	points = [(s.arrived_lat or s.latitude, s.arrived_lng or s.longitude) for s in trip.stops]
	route = maps.route_km(points)
	if not route:
		trip.distance_source = None
		return
	trip.actual_km, legs = route
	for stop, km in zip(trip.stops, [0, *legs]):
		stop.leg_km = km
	trip.return_km = 0
	if flt(trip.empty_return_percent):
		back = maps.route_km([points[-1], points[0]])
		trip.return_km = back[0] if back else 0
	trip.distance_source = C.DISTANCE_MAP
	tolerance = flt(settings().distance_tolerance_percent) or 20
	trip.distance_flag = (
		1 if flt(trip.planned_km) and abs(trip.actual_km - trip.planned_km) / trip.planned_km * 100 > tolerance else 0
	)


# Review, receipt and payment ---------------------------------------------------------------


@frappe.whitelist()
def confirm_receipt(name, stop):
	trip = get_trip(name)
	require_status(trip, C.IN_PROGRESS, C.FINISHED)
	row = next((r for r in trip.stops if r.name == stop), None)
	if not row or row.purpose not in C.CONFIRM_PURPOSES:
		frappe.throw(_("النقطة مش نقطة تسليم."))
	if row.receiver != frappe.session.user and not is_manager():
		frappe.throw(_("يأكد الاستلام المستلم المحدد للنقطة بس."), frappe.PermissionError)
	if not row.arrived_on:
		frappe.throw(_("السواق لسه ما وصلش «{0}».").format(row.location))
	if not row.confirmed:
		row.update({"confirmed": 1, "confirmed_via": C.VIA_ACCOUNT, "confirmed_by": frappe.session.user, "confirmed_on": now_datetime()})
		save(trip)
	return True


@frappe.whitelist()
def set_manual_distance(name, km, reason, return_km=0):
	check_manager()
	trip = get_trip(name)
	require_status(trip, C.FINISHED)
	if trip.billing_mode != C.BY_KM or trip.is_company_vehicle:
		frappe.throw(_("المسافة اليدوية لرحلات الكيلو بالعربيات الخارجية بس."))
	if flt(km) <= 0 or not (reason or "").strip():
		frappe.throw(_("اكتب المسافة والسبب."))
	trip.manual_km, trip.return_km, trip.distance_source = flt(km, 2), flt(return_km, 2), C.DISTANCE_MANUAL
	pricing.apply(trip, settings())
	save(trip)
	comment(trip, _("مسافة يدوية {0} كم (رجوع {1} كم): {2}").format(trip.manual_km, trip.return_km, reason.strip()))
	return trip.total_amount


@frappe.whitelist()
def recalculate(name):
	check_manager()
	trip = get_trip(name)
	require_status(trip, C.FINISHED)
	if trip.is_company_vehicle:
		return 0
	if trip.distance_source != C.DISTANCE_MANUAL:
		measure_distance(trip)
	pricing.apply(trip, settings())
	save(trip)
	return trip.total_amount


def open_issues(trip):
	issues = []
	if trip.billing_mode == C.BY_KM and trip.distance_source not in (C.DISTANCE_MAP, C.DISTANCE_MANUAL):
		issues.append(_("المسافة لسه مش محسوبة"))
	unconfirmed = [r.location for r in trip.stops if r.purpose in C.CONFIRM_PURPOSES and not r.confirmed]
	if unconfirmed:
		issues.append(_("الاستلام مش متأكد في: {0}").format("، ".join(unconfirmed)))
	far = [r.location for r in trip.stops if r.out_of_range]
	if far:
		issues.append(_("«وصلت» اتسجل بعيد عن النقطة أو من غير GPS في: {0}").format("، ".join(far)))
	if trip.distance_flag:
		issues.append(_("المسافة الفعلية بعيدة عن المخططة ({0} مقابل {1} كم)").format(trip.actual_km, trip.planned_km))
	return issues


@frappe.whitelist()
def approve_payment(name, note=None):
	role = settings().payment_approver_role or C.FLEET_MANAGER
	if role not in frappe.get_roles() and "System Manager" not in frappe.get_roles():
		frappe.throw(_("الاعتماد للصرف لدور {0}.").format(_(role)), frappe.PermissionError)
	trip = get_trip(name)
	require_status(trip, C.FINISHED)
	if trip.is_company_vehicle:
		frappe.throw(_("رحلات عربيات الشركة ملهاش صرف."))
	if trip.billing_mode == C.BY_KM and trip.distance_source not in (C.DISTANCE_MAP, C.DISTANCE_MANUAL):
		frappe.throw(_("حدد المسافة يدوي الأول."))
	issues = [i for i in open_issues(trip) if i != _("المسافة لسه مش محسوبة")]
	note = (note or "").strip()
	if issues and not note:
		frappe.throw(_("قبل الاعتماد اكتب ملاحظة على: {0}").format("؛ ".join(issues)), title=_("محتاج ملاحظة"))
	for row in trip.stops:
		if row.purpose in C.CONFIRM_PURPOSES and not row.confirmed:
			row.update({"confirmed": 1, "confirmed_via": C.VIA_OVERRIDE, "confirmed_by": frappe.session.user, "confirmed_on": now_datetime()})
	pricing.apply(trip, settings())
	trip.update({"status": C.APPROVED, "payment_approved_by": frappe.session.user, "payment_approved_on": now_datetime(), "approval_note": note or None})
	save(trip)
	notify.driver(trip, _("اتعتمد مستحقك ✅"), _("رحلة {0}: {1}").format(
		trip.name, frappe.format_value(trip.total_amount, {"fieldtype": "Currency"})))
	return trip.status


@frappe.whitelist()
def cancel(name, reason, compensation=0):
	trip = get_trip(name)
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("اكتب سبب الإلغاء."))
	own_request = trip.owner == frappe.session.user and trip.status in (C.DRAFT, C.PENDING)
	if not own_request:
		check_manager()
	if trip.status in (C.INVOICED, C.CANCELLED, C.APPROVED):
		frappe.throw(_("الرحلة {0} ما تتلغيش وهي «{1}».").format(trip.name, _(trip.status)))
	compensation = flt(compensation)
	if compensation:
		if trip.status not in (C.ACCEPTED, C.IN_PROGRESS, C.FINISHED) or trip.is_company_vehicle:
			frappe.throw(_("التعويض بيبقى بعد ما السواق الخارجي يقبل الرحلة بس."))
		if compensation < 0:
			frappe.throw(_("التعويض ما يبقاش بالسالب."))
	was_with_driver = trip.status in C.ACTIVE_STATES or trip.status == C.FINISHED
	for field in pricing.AMOUNT_FIELDS:
		trip.set(field, 0)
	trip.update({"status": C.CANCELLED, "cancel_reason": reason, "cancelled_on": now_datetime(),
		"cancellation_compensation": compensation, "total_amount": compensation})
	save(trip)
	comment(trip, _("اتلغت: {0}{1}").format(reason, _(" · تعويض {0}").format(compensation) if compensation else ""))
	if was_with_driver:
		notify.driver(trip, _("اتلغت رحلة"), _("الرحلة {0} اتلغت: {1}").format(trip.name, reason))
	return trip.status


@frappe.whitelist()
def review_info(name):
	"""What the approval dialog shows before approving for payment."""
	trip = frappe.get_doc("Fleet Trip", name)
	trip.check_permission("read")
	return {"issues": open_issues(trip), "total": trip.total_amount}
