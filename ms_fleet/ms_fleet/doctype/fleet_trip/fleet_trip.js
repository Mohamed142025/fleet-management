// Fleet Trip: the requester sends it, the fleet team assigns it and reviews it, receivers confirm
// deliveries. The driver works through the driver app. The server enforces the same rules.
(() => {
	const API = "ms_fleet.trip.";
	const S = {
		DRAFT: "مسودة",
		PENDING: "بانتظار الاعتماد",
		ASSIGNED: "مسندة",
		ACCEPTED: "مقبولة",
		IN_PROGRESS: "جارية",
		FINISHED: "منتهية",
		APPROVED: "معتمدة للصرف",
		INVOICED: "مفوترة",
		DECLINED: "مرفوضة من السواق",
		CANCELLED: "ملغاة",
	};
	const DELIVERY = "تنزيل";
	const is_manager = () => frappe.user.has_role(["Fleet Manager", "System Manager"]);

	frappe.ui.form.on("Fleet Trip", {
		setup(frm) {
			frm.set_query("vehicle_type", () => ({ filters: { disabled: 0 } }));
			frm.set_query("receiver", "stops", () => ({ filters: { enabled: 1, user_type: "System User" } }));
		},

		refresh(frm) {
			if (frm.is_new()) return;
			const status = frm.doc.status;
			const editable = status === S.DRAFT || status === S.PENDING || (is_manager() && [S.ASSIGNED, S.ACCEPTED, S.DECLINED].includes(status));
			frm.set_df_property("stops", "read_only", editable ? 0 : 1);
			for (const field of ["project", "company", "cost_center", "vehicle_type", "billing_mode", "scheduled_time", "planned_days"]) {
				frm.set_df_property(field, "read_only", editable ? 0 : 1);
			}

			if (status === S.DRAFT && (frm.doc.owner === frappe.session.user || is_manager())) {
				frm.page.set_primary_action(__("إرسال لإدارة الحركة"), () => call(frm, "submit_request", {}, __("اتبعت الطلب.")));
			}
			if (is_manager() && [S.PENDING, S.DECLINED, S.ASSIGNED, S.ACCEPTED].includes(status)) {
				const label = frm.doc.driver ? __("إسناد لسواق تاني") : __("إسناد");
				if (status === S.PENDING || status === S.DECLINED) frm.page.set_primary_action(label, () => assign(frm));
				else frm.add_custom_button(label, () => assign(frm));
			}
			if (status === S.FINISHED && !frm.doc.is_company_vehicle) {
				if (is_manager() && frm.doc.billing_mode === "بالكيلو") {
					frm.add_custom_button(__("مسافة يدوية"), () => manual_distance(frm), __("المراجعة"));
				}
				if (is_manager()) frm.add_custom_button(__("إعادة الحساب"), () => call(frm, "recalculate", {}, __("اتحسبت.")), __("المراجعة"));
				frm.page.set_primary_action(__("اعتماد للصرف"), () => approve(frm));
			}
			receipt_buttons(frm);
			const can_cancel =
				![S.INVOICED, S.CANCELLED, S.APPROVED].includes(status) &&
				(is_manager() || (frm.doc.owner === frappe.session.user && [S.DRAFT, S.PENDING].includes(status)));
			if (can_cancel) frm.add_custom_button(__("إلغاء الرحلة"), () => cancel(frm));
			show_issues(frm);
		},
	});

	frappe.ui.form.on("Fleet Trip Stop", {
		location(frm, cdt, cdn) {
			const row = locals[cdt][cdn];
			if (row.purpose === DELIVERY && !row.receiver) frappe.model.set_value(cdt, cdn, "receiver", frm.doc.requested_by || frappe.session.user);
		},
	});

	function call(frm, method, args, done) {
		return frappe
			.xcall(API + method, { name: frm.doc.name, ...args })
			.then(() => {
				frm.reload_doc();
				if (done) frappe.show_alert({ message: done, indicator: "green" });
			})
			.catch(() => {});
	}

	function assign(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("إسناد الرحلة"),
			fields: [
				{
					fieldname: "vehicle",
					fieldtype: "Link",
					options: "Vehicle",
					label: __("العربية"),
					reqd: 1,
					get_query: () => ({ filters: { custom_fleet_vehicle_type: frm.doc.vehicle_type } }),
					onchange() {
						const vehicle = dialog.get_value("vehicle");
						if (!vehicle) return;
						frappe.db.get_value("Vehicle", vehicle, ["custom_fleet_driver", "custom_fleet_ownership"]).then(({ message }) => {
							if (message?.custom_fleet_driver) dialog.set_value("driver", message.custom_fleet_driver);
							dialog.set_df_property("vehicle", "description", message?.custom_fleet_ownership ? __("الملكية: {0}", [message.custom_fleet_ownership]) : "");
						});
					},
				},
				{ fieldname: "driver", fieldtype: "Link", options: "Driver", label: __("السواق"), get_query: () => ({ filters: { status: "Active" } }) },
			],
			primary_action_label: __("إسناد وإبلاغ السواق"),
			primary_action(values) {
				dialog.hide();
				call(frm, "assign", values, __("اتسندت، والسواق وصله إشعار."));
			},
		});
		dialog.show();
	}

	function manual_distance(frm) {
		frappe.prompt(
			[
				{ fieldname: "km", fieldtype: "Float", label: __("المسافة (كم)"), reqd: 1, default: frm.doc.manual_km || frm.doc.planned_km },
				{ fieldname: "return_km", fieldtype: "Float", label: __("مسافة الرجوع (كم)"), default: frm.doc.return_km,
					description: __("بتتحسب لو تسعيرة النوع فيها رجوع فاضي.") },
				{ fieldname: "reason", fieldtype: "Small Text", label: __("السبب"), reqd: 1 },
			],
			(values) => call(frm, "set_manual_distance", values, __("اتحسب المستحق.")),
			__("مسافة يدوية"),
			__("حفظ")
		);
	}

	function approve(frm) {
		frappe.xcall(API + "review_info", { name: frm.doc.name }).then(({ issues, total }) => {
			const list = issues.length
				? `<ul class="text-danger">${issues.map((i) => `<li>${frappe.utils.escape_html(i)}</li>`).join("")}</ul>`
				: `<p class="text-success">${__("مفيش ملاحظات على الرحلة.")}</p>`;
			const dialog = new frappe.ui.Dialog({
				title: __("اعتماد للصرف"),
				fields: [
					{ fieldtype: "HTML", fieldname: "summary", options: `<p>${__("المستحق")}: <b>${format_currency(total)}</b></p>${list}` },
					{ fieldname: "note", fieldtype: "Small Text", label: __("ملاحظة الاعتماد"), reqd: issues.length ? 1 : 0 },
				],
				primary_action_label: __("اعتماد"),
				primary_action({ note }) {
					dialog.hide();
					call(frm, "approve_payment", { note }, __("اتعتمدت للصرف."));
				},
			});
			dialog.show();
		});
	}

	function cancel(frm) {
		const after_accept = [S.ACCEPTED, S.IN_PROGRESS, S.FINISHED].includes(frm.doc.status) && !frm.doc.is_company_vehicle;
		const fields = [{ fieldname: "reason", fieldtype: "Small Text", label: __("سبب الإلغاء"), reqd: 1 }];
		if (after_accept && is_manager()) {
			fields.push({ fieldname: "compensation", fieldtype: "Currency", label: __("تعويض السواق"), default: 0,
				description: __("السواق كان قبل الرحلة. التعويض بيتصرف في فاتورة المستحقات.") });
		}
		frappe.prompt(fields, (values) => call(frm, "cancel", values, __("اتلغت.")), __("إلغاء الرحلة"), __("إلغاء الرحلة"));
	}

	function receipt_buttons(frm) {
		if (![S.IN_PROGRESS, S.FINISHED].includes(frm.doc.status)) return;
		for (const row of frm.doc.stops || []) {
			const mine = row.receiver === frappe.session.user || is_manager();
			if (row.purpose === DELIVERY && row.arrived_on && !row.confirmed && mine) {
				frm.add_custom_button(__("تأكيد الاستلام: {0}", [row.location]), () =>
					frappe.confirm(__("استلمت في «{0}»؟", [row.location]), () =>
						call(frm, "confirm_receipt", { stop: row.name }, __("اتأكد الاستلام.")))
				);
			}
		}
	}

	function show_issues(frm) {
		if (frm.doc.status !== S.FINISHED || frm.doc.is_company_vehicle || !is_manager()) return;
		frappe.xcall(API + "review_info", { name: frm.doc.name }).then(({ issues }) => {
			if (issues.length) frm.dashboard.set_headline(`<span class="text-danger">${issues.map(frappe.utils.escape_html).join(" · ")}</span>`);
		});
	}
})();
