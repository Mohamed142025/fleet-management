export default {
	content: ["./index.html", "./src/**/*.{vue,js}"],
	theme: {
		extend: {
			colors: { brand: "var(--brand)", "brand-soft": "var(--brand-soft)" },
			fontFamily: { sans: ["system-ui", "Segoe UI", "Tahoma", "Arial", "sans-serif"] },
		},
	},
}
