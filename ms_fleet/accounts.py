"""Driver accounts for the driver app: a website user (no desk) with the Fleet Driver role, signed
in with the mobile number. The fleet team creates it from the Driver form and hands the password
to the driver; it is shown once."""

import secrets

import frappe
from frappe import _

from ms_fleet import constants as C
from ms_fleet.trip import check_manager


@frappe.whitelist()
def create_driver_login(driver, mobile=None):
	check_manager()
	driver = frappe.get_doc("Driver", driver)
	mobile = (mobile or driver.cell_number or "").strip().replace(" ", "")
	if not mobile:
		frappe.throw(_("اكتب رقم موبايل السواق."))
	other = frappe.db.get_value("User", {"mobile_no": mobile, "name": ["!=", driver.user or ""]})
	if other:
		frappe.throw(_("رقم الموبايل ده مستخدم لحساب تاني: {0}").format(other))

	if driver.user and frappe.db.exists("User", driver.user):
		user = frappe.get_doc("User", driver.user)
	else:
		user = frappe.new_doc("User")
		user.update(
			{
				"email": f"driver-{frappe.scrub(driver.name).replace('_', '-')}@drivers.invalid",
				"first_name": driver.full_name,
				"user_type": "Website User",
				"send_welcome_email": 0,
			}
		)
		user.flags.no_welcome_mail = True
	password = secrets.token_urlsafe(9)
	user.mobile_no = mobile
	user.enabled = 1
	user.new_password = password
	if C.FLEET_DRIVER not in [r.role for r in user.roles]:
		user.append("roles", {"role": C.FLEET_DRIVER})
	user.save(ignore_permissions=True)

	if driver.user != user.name or driver.cell_number != mobile:
		driver.user, driver.cell_number = user.name, mobile
		driver.save(ignore_permissions=True)
	return {"mobile": mobile, "password": password, "url": frappe.utils.get_url("/driver")}
