// Fleet Trip list: status colours, and the purchase invoices for approved trips.
frappe.listview_settings["Fleet Trip"] = {
	add_fields: ["status", "is_company_vehicle"],
	get_indicator(doc) {
		const colors = {
			"مسودة": "gray",
			"بانتظار الاعتماد": "orange",
			"مسندة": "blue",
			"مقبولة": "cyan",
			"جارية": "purple",
			"منتهية": "yellow",
			"معتمدة للصرف": "green",
			"مفوترة": "darkgrey",
			"مرفوضة من السواق": "red",
			"ملغاة": "red",
		};
		return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},
	onload(list) {
		if (!frappe.model.can_create("Purchase Invoice")) return;
		list.page.add_inner_button(__("فواتير المستحقات"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("فواتير مستحقات العربيات الخارجية"),
				fields: [
					{ fieldname: "company", fieldtype: "Link", options: "Company", label: __("الشركة"), reqd: 1,
						default: frappe.defaults.get_user_default("Company") },
					{ fieldname: "to_date", fieldtype: "Date", label: __("لحد تاريخ"), reqd: 1, default: frappe.datetime.get_today() },
					{ fieldname: "from_date", fieldtype: "Date", label: __("من تاريخ") },
					{ fieldname: "supplier", fieldtype: "Link", options: "Supplier", label: __("مورد معيّن") },
				],
				primary_action_label: __("إنشاء الفواتير"),
				primary_action(values) {
					dialog.hide();
					frappe.xcall("ms_fleet.settlement.make_invoices", values).then((names) => {
						list.refresh();
						frappe.msgprint({
							title: __("اتعملت فواتير مسودة"),
							indicator: "green",
							message: names.map((n) => frappe.utils.get_form_link("Purchase Invoice", n, true)).join("<br>"),
						});
					});
				},
			});
			dialog.show();
		});
	},
};
