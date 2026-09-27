"""A push relay that speaks the protocol of Frappe's central relay (notification_relay.api.*).

Frappe's push service (frappe.push_notification on the server, the FrappePushNotification client
in the browser) talks to whatever push_relay_server_url points at. Frappe's own relay only knows
Frappe's apps (hrms, raven ...), so this site can be the relay instead, sending through the
company's Firebase project for every project name (ms_fleet, hrms ...). hooks.py maps the
notification_relay.api.* method names to the functions here.

A site registers once: it asks for credentials, the relay calls the site's
frappe.push_notification.auth_webhook to check the token it sent, then issues an API key for a
relay-only user. Every later call comes with that key.
"""

import json

import frappe
import requests
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime
from werkzeug.wrappers import Response

from ms_fleet import constants as C
from ms_fleet.relay import fcm

WEBHOOK_PREFIX = "/api/method/frappe.push_notification.auth_webhook"
NO_TOPICS = {"success": False, "message": "Topics are not supported by this relay"}


def _check_enabled():
	if not frappe.db.get_single_value("Fleet Settings", "relay_enabled"):
		frappe.throw(_("Push relay is not enabled on this site."))


def _client_site(site_name):
	"""The registered site behind the API key of this call."""
	_check_enabled()
	site = frappe.db.get_value("Fleet Push Site", {"user": frappe.session.user}, "site_name")
	if not site or (site_name and site_name != site):
		frappe.throw(_("Not a registered site."), frappe.PermissionError)
	return site


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_config(project_name=None):
	"""The browser reads this directly, without Frappe's {"message": ...} wrapper."""
	settings = frappe.get_cached_doc("Fleet Settings")
	if settings.relay_enabled and settings.firebase_web_config:
		body, status = {"config": json.loads(settings.firebase_web_config), "vapid_public_key": settings.firebase_vapid_key}, 200
	else:
		body, status = {"exc_type": "ValidationError", "message": "Push relay is not enabled on this site."}, 417
	response = Response(json.dumps(body), status=status, mimetype="application/json")
	response.headers["Access-Control-Allow-Origin"] = "*"
	return response


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60 * 60)
def get_credential(endpoint, protocol, port=None, token=None, webhook_route=None, project_name=None, site_name=None):
	_check_enabled()
	if protocol not in ("http", "https") or not (webhook_route or "").startswith(WEBHOOK_PREFIX) or not token:
		return {"success": False, "message": "Invalid registration request"}
	base = f"{protocol}://{endpoint}" + (f":{port}" if port else "")
	try:
		answer = requests.get(base + webhook_route, timeout=15)
	except Exception:
		return {"success": False, "message": "Site unreachable"}
	if answer.status_code != 200 or answer.text.strip() != token:
		return {"success": False, "message": "Site verification failed"}

	site_name = site_name or endpoint
	user = _relay_user(site_name)
	api_key, api_secret = frappe.generate_hash(length=15), frappe.generate_hash(length=15)
	user.api_key, user.api_secret = api_key, api_secret
	user.save(ignore_permissions=True)

	site = frappe.get_doc("Fleet Push Site", site_name) if frappe.db.exists("Fleet Push Site", site_name) else frappe.new_doc("Fleet Push Site")
	site.update({"site_name": site_name, "endpoint": endpoint, "protocol": protocol, "port": port, "user": user.name, "registered_on": now_datetime()})
	site.save(ignore_permissions=True)
	return {"success": True, "credentials": {"api_key": api_key, "api_secret": api_secret}}


def _relay_user(site_name):
	existing = frappe.db.get_value("Fleet Push Site", site_name, "user")
	if existing and frappe.db.exists("User", existing):
		return frappe.get_doc("User", existing)
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": f"push-relay-{frappe.generate_hash(length=8)}@relay.invalid",
			"first_name": f"Push Relay {site_name}"[:140],
			"user_type": "Website User",
			"send_welcome_email": 0,
			"roles": [{"role": C.RELAY_CLIENT}],
		}
	)
	user.flags.no_welcome_mail = True
	return user.insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def add_token(project_name, user_id, fcm_token, site_name=None):
	site = _client_site(site_name)
	if not fcm_token:
		return {"success": False, "message": "Token missing"}
	existing = frappe.db.get_value("Fleet Push Token", {"site_name": site, "project_name": project_name, "token": fcm_token})
	if existing:
		frappe.db.set_value("Fleet Push Token", existing, "user_id", user_id)
	else:
		frappe.get_doc(
			{"doctype": "Fleet Push Token", "site_name": site, "project_name": project_name, "user_id": user_id, "token": fcm_token}
		).insert(ignore_permissions=True)
	return {"success": True, "message": "Token added"}


@frappe.whitelist(methods=["POST"])
def remove_token(project_name, user_id, fcm_token, site_name=None):
	site = _client_site(site_name)
	frappe.db.delete("Fleet Push Token", {"site_name": site, "project_name": project_name, "user_id": user_id, "token": fcm_token})
	return {"success": True, "message": "Token removed"}


@frappe.whitelist(methods=["POST"])
def send_to_user(project_name, user_id, title, body, data=None, site_name=None):
	site = _client_site(site_name)
	tokens = frappe.get_all(
		"Fleet Push Token", filters={"site_name": site, "project_name": project_name, "user_id": user_id}, fields=["name", "token"]
	)
	if not tokens:
		return {"success": False, "message": "No device registered for this user"}
	payload = {"title": title, "body": body}
	payload.update(json.loads(data) if isinstance(data, str) and data else data or {})
	sent = 0
	for row in tokens:
		result = fcm.send(row.token, payload)
		if result == fcm.SENT:
			sent += 1
			frappe.db.set_value("Fleet Push Token", row.name, "last_sent", now_datetime(), update_modified=False)
		elif result == fcm.UNREGISTERED:
			frappe.delete_doc("Fleet Push Token", row.name, ignore_permissions=True, delete_permanently=True)
	return {"success": sent > 0, "message": f"{sent} of {len(tokens)} sent"}


@frappe.whitelist(methods=["POST"])
def topics_not_supported(**kwargs):
	_client_site(kwargs.get("site_name"))
	return NO_TOPICS
