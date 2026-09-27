const LOCALE = "ar-EG-u-nu-latn"

export function localNow() {
	// The phone's wall-clock time, as the server stores times.
	const d = new Date()
	const pad = (n) => String(n).padStart(2, "0")
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

export function parse(value) {
	return value ? new Date(String(value).replace(" ", "T")) : null
}

export function when(value) {
	const d = parse(value)
	if (!d) return ""
	return new Intl.DateTimeFormat(LOCALE, { weekday: "short", day: "numeric", month: "numeric", hour: "numeric", minute: "2-digit" }).format(d)
}

export function time(value) {
	const d = parse(value)
	return d ? new Intl.DateTimeFormat(LOCALE, { hour: "numeric", minute: "2-digit" }).format(d) : ""
}

export function money(value) {
	const n = Number(value || 0)
	return new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 2 }).format(n) + " ج.م"
}

export function km(value) {
	return value ? `${new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1 }).format(value)} كم` : ""
}

export const STATUS_STYLE = {
	"مسندة": "bg-blue-100 text-blue-800",
	"مقبولة": "bg-cyan-100 text-cyan-800",
	"جارية": "bg-violet-100 text-violet-800",
	"منتهية": "bg-amber-100 text-amber-800",
	"معتمدة للصرف": "bg-emerald-100 text-emerald-800",
	"مفوترة": "bg-gray-200 text-gray-700",
	"مرفوضة من السواق": "bg-red-100 text-red-700",
	"ملغاة": "bg-red-100 text-red-700",
}
