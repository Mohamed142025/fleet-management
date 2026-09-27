frappe.query_reports["Fleet Vehicle Cost"] = {
	filters: [
		{ fieldname: "company", label: __("الشركة"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "from_date", label: __("من"), fieldtype: "Date", reqd: 1, default: frappe.datetime.month_start() },
		{ fieldname: "to_date", label: __("إلى"), fieldtype: "Date", reqd: 1, default: frappe.datetime.month_end() },
		{ fieldname: "vehicle", label: __("العربية"), fieldtype: "Link", options: "Vehicle" },
	],
};
