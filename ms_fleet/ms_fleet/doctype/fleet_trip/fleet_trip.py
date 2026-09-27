# Copyright (c) 2026, Mohamed Sayed and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from ms_fleet import constants as C
from ms_fleet import trip as fleet_trip


class FleetTrip(Document):
	def validate(self):
		fleet_trip.validate(self)

	def on_trash(self):
		if self.status not in (C.DRAFT, C.PENDING):
			frappe.throw(_("الرحلة اتسندت، فتتلغي بس ومش بتتمسح."))
