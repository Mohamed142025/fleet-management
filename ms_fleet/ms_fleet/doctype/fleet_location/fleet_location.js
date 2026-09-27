// A point marked on the map fills the coordinates (the server does the same on save).
frappe.ui.form.on("Fleet Location", {
	map(frm) {
		let features = [];
		try {
			features = JSON.parse(frm.doc.map || "{}").features || [];
		} catch (e) {
			return;
		}
		const points = features.filter((f) => f.geometry?.type === "Point");
		if (!points.length) return;
		const [lng, lat] = points[points.length - 1].geometry.coordinates;
		frm.set_value({ latitude: flt(lat, 6), longitude: flt(lng, 6) });
	},
});
