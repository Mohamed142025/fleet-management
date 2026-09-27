frappe.query_reports["Fleet Trip Register"] = {
	filters: [
		{ fieldname: "company", label: __("الشركة"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "from_date", label: __("من"), fieldtype: "Date", default: frappe.datetime.month_start() },
		{ fieldname: "to_date", label: __("إلى"), fieldtype: "Date", default: frappe.datetime.month_end() },
		{ fieldname: "project", label: __("المشروع"), fieldtype: "Link", options: "Project" },
		{ fieldname: "supplier", label: __("المورد"), fieldtype: "Link", options: "Supplier" },
		{ fieldname: "driver", label: __("السواق"), fieldtype: "Link", options: "Driver" },
		{ fieldname: "vehicle_type", label: __("النوع"), fieldtype: "Link", options: "Fleet Vehicle Type" },
		{ fieldname: "status", label: __("الحالة"), fieldtype: "Select",
			options: ["", "مسودة", "بانتظار الاعتماد", "مسندة", "مقبولة", "جارية", "منتهية", "معتمدة للصرف", "مفوترة", "مرفوضة من السواق", "ملغاة"].join("\n") },
	],
};
