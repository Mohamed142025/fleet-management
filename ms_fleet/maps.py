"""Road distances from the maps provider set in Fleet Settings, and straight-line distances for
checking that a driver pressed «وصلت» near the stop.

Without a provider and key, route_km returns None and the trip waits for a distance entered by
the fleet manager.
"""

import math

import frappe
import requests
from frappe.utils import flt

GOOGLE_URL = "https://maps.googleapis.com/maps/api/directions/json"
ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
TIMEOUT = 20


def haversine_m(lat1, lng1, lat2, lng2):
	radius = 6371000
	p1, p2 = math.radians(flt(lat1)), math.radians(flt(lat2))
	dp, dl = p2 - p1, math.radians(flt(lng2) - flt(lng1))
	a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
	return 2 * radius * math.asin(math.sqrt(a))


def is_configured():
	settings = frappe.get_cached_doc("Fleet Settings")
	return bool(settings.maps_provider and settings.get_password("maps_api_key", raise_exception=False))


def route_km(points):
	"""(total km, [km of each leg]) along the road through the points in order, or None."""
	points = [(flt(lat), flt(lng)) for lat, lng in points if lat or lng]
	if len(points) < 2 or not is_configured():
		return None
	settings = frappe.get_cached_doc("Fleet Settings")
	key = settings.get_password("maps_api_key")
	try:
		if settings.maps_provider == "Google Maps":
			legs = _google(points, key)
		else:
			legs = _openrouteservice(points, key)
	except Exception:
		frappe.log_error(title="Fleet: route distance failed")
		return None
	legs = [flt(meters / 1000, 2) for meters in legs]
	return flt(sum(legs), 2), legs


def _google(points, key):
	params = {
		"origin": "{},{}".format(*points[0]),
		"destination": "{},{}".format(*points[-1]),
		"mode": "driving",
		"key": key,
	}
	if len(points) > 2:
		params["waypoints"] = "|".join("{},{}".format(*p) for p in points[1:-1])
	response = requests.get(GOOGLE_URL, params=params, timeout=TIMEOUT)
	response.raise_for_status()
	data = response.json()
	if data.get("status") != "OK":
		raise ValueError(f"Google Directions: {data.get('status')} {data.get('error_message', '')}")
	return [leg["distance"]["value"] for leg in data["routes"][0]["legs"]]


def _openrouteservice(points, key):
	response = requests.post(
		ORS_URL,
		json={"coordinates": [[lng, lat] for lat, lng in points]},
		headers={"Authorization": key, "Content-Type": "application/json"},
		timeout=TIMEOUT,
	)
	response.raise_for_status()
	return [segment["distance"] for segment in response.json()["routes"][0]["segments"]]
