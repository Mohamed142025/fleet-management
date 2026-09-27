// The driver's app account: created (or given a new password) from the Driver form by the fleet
// team. The password is shown once.
frappe.ui.form.on("Driver", {
	refresh(frm) {
		if (frm.is_new() || !frappe.user.has_role(["Fleet Manager", "System Manager"])) return;
		const label = frm.doc.user ? __("كلمة سر جديدة للتطبيق") : __("حساب تطبيق السواق");
		frm.add_custom_button(label, () => {
			frappe.prompt(
				[{ fieldname: "mobile", fieldtype: "Data", label: __("رقم الموبايل"), default: frm.doc.cell_number, reqd: 1 }],
				({ mobile }) =>
					frappe.xcall("ms_fleet.accounts.create_driver_login", { driver: frm.doc.name, mobile }).then((r) => {
						frm.reload_doc();
						frappe.msgprint({
							title: __("حساب تطبيق السواق"),
							indicator: "green",
							message: `<p>${__("اديها للسواق. كلمة السر مش هتظهر تاني.")}</p>
								<p>${__("الرابط")}: <b dir="ltr">${frappe.utils.escape_html(r.url)}</b></p>
								<p>${__("الموبايل")}: <b dir="ltr">${frappe.utils.escape_html(r.mobile)}</b></p>
								<p>${__("كلمة السر")}: <b dir="ltr">${frappe.utils.escape_html(r.password)}</b></p>`,
						});
					}),
				label,
				__("تنفيذ")
			);
		});
	},
});
