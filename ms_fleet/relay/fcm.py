"""Sending through Firebase Cloud Messaging (HTTP v1) with the service account kept as a private
file in Fleet Settings. google-auth comes with Frappe."""

import json

import frappe
import requests
from frappe import _

SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
ACCESS_TOKEN_KEY = "ms_fleet_fcm_access_token"
SENT, UNREGISTERED, FAILED = "sent", "unregistered", "failed"


def load_service_account(file_url=None):
	file_url = file_url or frappe.get_cached_doc("Fleet Settings").firebase_service_account
	if not file_url:
		frappe.throw(_("ملف حساب الخدمة بتاع Firebase مش مرفوع في Fleet Settings."))
	content = frappe.get_doc("File", {"file_url": file_url}).get_content()
	if isinstance(content, bytes):
		content = content.decode()
	try:
		return json.loads(content)
	except ValueError:
		frappe.throw(_("ملف حساب الخدمة لازم يبقى JSON."))


def access_token():
	token = frappe.cache.get_value(ACCESS_TOKEN_KEY)
	if token:
		return token
	from google.auth.transport.requests import Request
	from google.oauth2 import service_account

	credentials = service_account.Credentials.from_service_account_info(load_service_account(), scopes=[SCOPE])
	credentials.refresh(Request())
	# Google's tokens last an hour; take a fresh one a little before.
	frappe.cache.set_value(ACCESS_TOKEN_KEY, credentials.token, expires_in_sec=50 * 60)
	return credentials.token


def send(token, data):
	"""A data message, as Frappe's push client expects (title, body, click_action, ...)."""
	project_id = load_service_account()["project_id"]
	response = requests.post(
		f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
		json={
			"message": {
				"token": token,
				"data": {key: str(value) for key, value in data.items() if value is not None},
				"webpush": {"headers": {"Urgency": "high", "TTL": "86400"}},
			}
		},
		headers={"Authorization": f"Bearer {access_token()}"},
		timeout=15,
	)
	if response.ok:
		return SENT
	text = response.text or ""
	if response.status_code == 404 or "UNREGISTERED" in text or (
		response.status_code == 400 and "registration token" in text.lower()
	):
		return UNREGISTERED
	if response.status_code == 401:
		frappe.cache.delete_value(ACCESS_TOKEN_KEY)
	frappe.log_error(title="Fleet push: FCM send failed", message=text[:2000])
	return FAILED
