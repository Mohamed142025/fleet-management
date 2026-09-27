"""Trip pricing from the vehicle type's rate card, with a driver's own rates taking precedence.

By the kilometre: the larger of distance x rate and the minimum fare, plus the empty return (a
share of the way back from the last stop to the first), then the night or holiday surcharge on
that (the higher of the two when both apply), then waiting beyond the free minutes at each stop.

By the day: every calendar day worked at the day rate, hours beyond the working day at the
overtime rate, and the holiday surcharge on the days that are holidays.

The rates are copied onto the trip when it is assigned, so a later change of the rate card does
not reach trips already given to a driver.
"""

from datetime import datetime, time, timedelta

import frappe
from frappe.utils import cint, flt, get_datetime, get_time, getdate

from ms_fleet import constants as C

RATE_FIELDS = (
	"rate_per_km",
	"minimum_fare",
	"empty_return_percent",
	"free_waiting_minutes",
	"waiting_rate_per_hour",
	"night_surcharge_percent",
	"holiday_surcharge_percent",
	"daily_rate",
	"daily_hours",
	"overtime_rate_per_hour",
)
# The rates a driver can have agreed on; zero on the driver means the vehicle type's rate.
DRIVER_RATE_FIELDS = ("rate_per_km", "minimum_fare", "waiting_rate_per_hour", "daily_rate", "overtime_rate_per_hour")
AMOUNT_FIELDS = (
	"base_amount",
	"return_amount",
	"surcharge_amount",
	"waiting_amount",
	"daily_amount",
	"overtime_amount",
	"total_amount",
)


def get_rates(vehicle_type, driver=None):
	vehicle_type = frappe.get_cached_doc("Fleet Vehicle Type", vehicle_type)
	rates = {field: vehicle_type.get(field) for field in RATE_FIELDS}
	if driver:
		own = frappe.get_all(
			"Fleet Driver Rate",
			filters={"parent": driver, "parenttype": "Driver", "vehicle_type": vehicle_type.name},
			fields=list(DRIVER_RATE_FIELDS),
			limit=1,
		)
		for field in DRIVER_RATE_FIELDS:
			if own and flt(own[0].get(field)):
				rates[field] = own[0].get(field)
	return rates


def is_night(moment, night_start, night_end):
	moment, start, end = get_time(moment), get_time(night_start or "22:00:00"), get_time(night_end or "06:00:00")
	if start == end:
		return False
	if start < end:
		return start <= moment < end
	return moment >= start or moment < end


def holiday_dates(holiday_list, from_date, to_date):
	if not holiday_list:
		return set()
	return {
		getdate(d)
		for d in frappe.get_all(
			"Holiday",
			filters={"parent": holiday_list, "holiday_date": ["between", [getdate(from_date), getdate(to_date)]]},
			pluck="holiday_date",
		)
	}


def stop_waiting(stops, free_minutes, finished_on=None):
	"""Minutes spent at each stop, and the minutes beyond the free allowance over the trip. The
	last stop runs until the trip is finished when the driver did not press «اتحركت» there."""
	extra = 0
	for i, stop in enumerate(stops):
		left = stop.get("departed_on") or (finished_on if i == len(stops) - 1 else None)
		if not stop.get("arrived_on") or not left:
			continue
		minutes = max(0, (get_datetime(left) - get_datetime(stop.arrived_on)).total_seconds() / 60)
		stop.waiting_minutes = cint(round(minutes))
		extra += max(0, minutes - cint(free_minutes))
	return cint(round(extra))


def daily_breakdown(started_on, finished_on, daily_hours, holidays):
	"""Calendar days touched by the work, overtime hours beyond the working day on each, and how
	many of those days are holidays."""
	cursor, end = get_datetime(started_on), get_datetime(finished_on)
	days = holiday_days = 0
	overtime = 0.0
	while cursor < end:
		next_midnight = datetime.combine(cursor.date() + timedelta(days=1), time.min)
		segment_end = min(end, next_midnight)
		hours = (segment_end - cursor).total_seconds() / 3600
		days += 1
		overtime += max(0.0, hours - flt(daily_hours))
		if cursor.date() in holidays:
			holiday_days += 1
		cursor = segment_end
	return days, flt(overtime, 2), holiday_days


def _surcharge_percent(trip, moment, settings):
	trip.is_night = 1 if is_night(moment, settings.night_start, settings.night_end) else 0
	trip.is_holiday = 1 if getdate(moment) in holiday_dates(settings.holiday_list, moment, moment) else 0
	percents = [0]
	if trip.is_night:
		percents.append(flt(trip.night_surcharge_percent))
	if trip.is_holiday:
		percents.append(flt(trip.holiday_surcharge_percent))
	return max(percents)


def _by_km(trip, km, return_km, moment, waiting_minutes, settings):
	base = max(flt(km) * flt(trip.rate_per_km), flt(trip.minimum_fare))
	back = flt(return_km) * flt(trip.rate_per_km) * flt(trip.empty_return_percent) / 100
	surcharge = (base + back) * _surcharge_percent(trip, moment, settings) / 100
	waiting = flt(waiting_minutes) / 60 * flt(trip.waiting_rate_per_hour)
	return {
		"base_amount": flt(base, 2),
		"return_amount": flt(back, 2),
		"surcharge_amount": flt(surcharge, 2),
		"waiting_amount": flt(waiting, 2),
		"daily_amount": 0,
		"overtime_amount": 0,
		"total_amount": flt(base + back + surcharge + waiting, 2),
	}


def expected_amount(trip, settings):
	"""What the driver sees when the trip is offered: the planned distance, no waiting."""
	if trip.billing_mode == C.BY_DAY:
		days = max(1, cint(trip.planned_days))
		surcharge = _surcharge_percent(trip, trip.scheduled_time, settings)
		return flt(days * flt(trip.daily_rate) * (1 + surcharge / 100), 2)
	if not trip.planned_km:
		return flt(trip.minimum_fare, 2)
	planned_return = trip.return_km if flt(trip.empty_return_percent) else 0
	return _by_km(trip, trip.planned_km, planned_return, trip.scheduled_time, 0, settings)["total_amount"]


def apply(trip, settings):
	"""Price a finished trip in place. Returns False when the distance is still unknown."""
	for field in AMOUNT_FIELDS:
		trip.set(field, 0)
	trip.waiting_minutes = stop_waiting(trip.stops, trip.free_waiting_minutes, trip.finished_on)

	if trip.billing_mode == C.BY_DAY:
		holidays = holiday_dates(settings.holiday_list, trip.started_on, trip.finished_on)
		days, overtime, holiday_days = daily_breakdown(trip.started_on, trip.finished_on, trip.daily_hours, holidays)
		trip.worked_days, trip.overtime_hours, trip.holiday_days = days, overtime, holiday_days
		trip.is_holiday = 1 if holiday_days else 0
		trip.is_night = 0
		daily = days * flt(trip.daily_rate)
		extra = overtime * flt(trip.overtime_rate_per_hour)
		surcharge = holiday_days * flt(trip.daily_rate) * flt(trip.holiday_surcharge_percent) / 100
		trip.update(
			{
				"daily_amount": flt(daily, 2),
				"overtime_amount": flt(extra, 2),
				"surcharge_amount": flt(surcharge, 2),
				"total_amount": flt(daily + extra + surcharge, 2),
			}
		)
		return True

	km = trip.manual_km if trip.distance_source == C.DISTANCE_MANUAL else trip.actual_km
	if trip.distance_source not in (C.DISTANCE_MAP, C.DISTANCE_MANUAL):
		return False
	trip.update(_by_km(trip, km, trip.return_km, trip.started_on, trip.waiting_minutes, settings))
	return True
