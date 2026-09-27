# Copyright (c) 2026, Mohamed Sayed and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document


class FleetSettings(Document):
	def validate(self):
		if self.night_start and self.night_start == self.night_end:
			frappe.throw(_("بداية الليل ونهايته ما ينفعش يبقوا نفس الساعة."))
		if self.firebase_web_config:
			try:
				config = json.loads(self.firebase_web_config)
			except ValueError:
				frappe.throw(_("إعدادات Firebase للويب لازم تبقى JSON."))
			missing = [k for k in ("apiKey", "projectId", "messagingSenderId", "appId") if not config.get(k)]
			if missing:
				frappe.throw(_("ناقص من إعدادات Firebase: {0}").format(", ".join(missing)))
		if self.firebase_service_account:
			self.validate_service_account()
		if self.relay_enabled and not (self.firebase_web_config and self.firebase_vapid_key and self.firebase_service_account):
			frappe.throw(_("السيرفر الوسيط محتاج إعدادات Firebase للويب، ومفتاح VAPID، وملف حساب الخدمة."))

	def validate_service_account(self):
		from ms_fleet.relay.fcm import load_service_account

		file = frappe.db.get_value("File", {"file_url": self.firebase_service_account}, ["is_private"], as_dict=True)
		if file and not file.is_private:
			frappe.throw(_("ملف حساب الخدمة سري: ارفعه كملف خاص (Private)."))
		info = load_service_account(self.firebase_service_account)
		if not info.get("private_key") or not info.get("project_id"):
			frappe.throw(_("ملف حساب الخدمة مش صحيح (مفيهوش private_key أو project_id)."))

	def on_update(self):
		frappe.cache.delete_value("ms_fleet_fcm_access_token")
