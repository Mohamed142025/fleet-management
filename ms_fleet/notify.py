"""Who hears about a trip, and how.

Desk users (fleet managers, requesters, receivers) get a Notification Log. The driver gets a
push notification through Frappe's push service (frappe.push_notification, whichever relay
push_relay_server_url points at) and a realtime event, so an open app refreshes at once. Both
go out only after the transaction commits.
"""

import frappe
from frappe.utils import get_url

from ms_fleet import constants as C


def managers():
	from frappe.utils.user import get_users_with_role

	return [
		user
		for user in get_users_with_role(C.FLEET_MANAGER)
		if frappe.db.get_value("User", user, "user_type") == "System User"
	]


def alert(users, subject, trip, message=None):
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	users = [u for u in dict.fromkeys(users or []) if u and u != frappe.session.user]
	if not users:
		return
	enqueue_create_notification(
		users,
		{
			"type": "Alert",
			"document_type": "Fleet Trip",
			"document_name": trip.name,
			"subject": subject,
			"email_content": message or subject,
			"from_user": frappe.session.user,
		},
	)


def driver(trip, title, body):
	user = trip.driver_user
	if not user:
		return
	frappe.publish_realtime("fleet_trip", {"trip": trip.name, "status": trip.status}, user=user, after_commit=True)
	push(user, title, body, f"/driver/trip/{trip.name}")


def push(user, title, body, link=None):
	if not frappe.db.get_single_value("Push Notification Settings", "enable_push_notification_relay"):
		return
	frappe.enqueue(
		"ms_fleet.notify.send_push",
		queue="short",
		enqueue_after_commit=True,
		user=user,
		title=title,
		body=body,
		link=link,
	)


def send_push(user, title, body, link=None):
	from frappe.push_notification import PushNotification

	notification = PushNotification(C.PUSH_PROJECT)
	if not notification.is_enabled():
		return
	icon = frappe.get_cached_doc("Fleet Settings").app_logo
	notification.send_notification_to_user(
		user, title, body, link=get_url(link) if link else None, icon=get_url(icon) if icon else None
	)
