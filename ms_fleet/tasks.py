"""Scheduled checks: drivers who have not answered an assignment, and licences and insurance
about to expire."""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime, nowdate

from ms_fleet import constants as C
from ms_fleet import notify

EXPIRY_NOTICE_DAYS = 30


def check_response_timeouts():
	"""Every few minutes: an assigned trip past its answer time goes back to the fleet team once."""
	for name in frappe.get_all(
		"Fleet Trip",
		filters={"status": C.ASSIGNED, "response_due": ["<", now_datetime()], "timeout_alerted": 0},
		pluck="name",
	):
		trip = frappe.get_doc("Fleet Trip", name)
		frappe.db.set_value("Fleet Trip", name, "timeout_alerted", 1, update_modified=False)
		notify.alert(
			notify.managers(),
			_("{0} ما ردّش على الرحلة {1} في المهلة. كلّمه أو أسندها لسواق تاني.").format(trip.driver_name, trip.name),
			trip,
		)


def expiry_alerts():
	"""Daily: driving licences and vehicle insurance ending within 30 days (or already ended)."""
	until = add_days(nowdate(), EXPIRY_NOTICE_DAYS)
	lines = []
	for driver in frappe.get_all(
		"Driver",
		filters=[["status", "=", "Active"], ["expiry_date", "is", "set"], ["expiry_date", "<=", until]],
		fields=["full_name", "expiry_date"],
	):
		lines.append(_("رخصة السواق {0} تنتهي {1}").format(driver.full_name, driver.expiry_date))
	for vehicle in frappe.get_all(
		"Vehicle",
		filters=[["end_date", "is", "set"], ["end_date", "<=", until], ["custom_fleet_ownership", "is", "set"]],
		fields=["name", "end_date"],
	):
		lines.append(_("تأمين العربية {0} ينتهي {1}").format(vehicle.name, vehicle.end_date))
	if not lines:
		return
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	enqueue_create_notification(
		notify.managers(),
		{
			"type": "Alert",
			"subject": _("تنبيه انتهاء: {0} بند").format(len(lines)),
			"email_content": "<br>".join(frappe.utils.escape_html(line) for line in lines),
		},
	)
