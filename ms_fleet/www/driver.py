"""The driver app page (/driver). The page itself is the built Vue app (driver.html); this fills in
the session's CSRF token and the boot data it starts from."""

import frappe

no_cache = 1


def get_context(context):
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()  # nosemgrep: the token has to be saved for the page's first request
	context.csrf_token = csrf_token
	context.boot = get_boot()
	return context


def get_boot():
	settings = frappe.get_cached_doc("Fleet Settings")
	return {
		"site_name": frappe.local.site,
		"socketio_port": frappe.conf.get("socketio_port") or 9000,
		"push_relay_server_url": frappe.conf.get("push_relay_server_url") or "",
		"push_enabled": bool(frappe.db.get_single_value("Push Notification Settings", "enable_push_notification_relay")),
		"app_name": settings.app_name or "MS Fleet",
		"theme_color": settings.theme_color or "#0E3B2E",
		"logo": settings.app_logo or "",
		"logged_in": frappe.session.user != "Guest",
	}
