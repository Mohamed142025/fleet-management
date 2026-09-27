# Copyright (c) 2026, Mohamed Sayed and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ms_fleet.pricing import RATE_FIELDS


class FleetVehicleType(Document):
	def validate(self):
		negative = [self.meta.get_label(f) for f in RATE_FIELDS if flt(self.get(f)) < 0]
		if negative:
			frappe.throw(_("القيم دي ما تبقاش بالسالب: {0}").format("، ".join(negative)))
		if not flt(self.daily_hours):
			self.daily_hours = 8
		if self.service_item and frappe.db.get_value("Item", self.service_item, "is_stock_item"):
			frappe.throw(_("صنف الخدمة لازم يبقى غير مخزني."))
