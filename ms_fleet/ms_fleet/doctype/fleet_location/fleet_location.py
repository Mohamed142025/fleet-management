# Copyright (c) 2026, Mohamed Sayed and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class FleetLocation(Document):
	def validate(self):
		self.set_coordinates_from_map()
		if not (-90 <= flt(self.latitude) <= 90 and -180 <= flt(self.longitude) <= 180):
			frappe.throw(_("الإحداثيات مش صحيحة."))
		if not (flt(self.latitude) or flt(self.longitude)):
			frappe.throw(_("حدد المكان على الخريطة، أو اكتب خط العرض والطول."))

	def set_coordinates_from_map(self):
		"""The last point marked on the map gives the coordinates."""
		if not self.map or not self.has_value_changed("map"):
			return
		try:
			features = json.loads(self.map).get("features") or []
		except (TypeError, ValueError):
			return
		points = [f["geometry"]["coordinates"] for f in features if (f.get("geometry") or {}).get("type") == "Point"]
		if points:
			self.longitude, self.latitude = flt(points[-1][0], 6), flt(points[-1][1], 6)
