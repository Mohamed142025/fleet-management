// The app's state: the signed-in driver, the trips, and the steps waiting for the network.
import { reactive } from "vue"
import { call } from "./api"
import { boot } from "./boot"
import { localNow } from "./format"
import * as queue from "./queue"
import { enablePush, pushEnabled, registerServiceWorker } from "./push"
import { connectSocket } from "./socket"

export const store = reactive({
	ready: false,
	session: null,
	online: navigator.onLine,
	pending: 0,
	failed: null,
	trips: [],
	history: [],
	current: null,
	toasts: [],
	registration: null,
	push: false,
})

export function toast(message, kind = "info") {
	if (store.toasts.some((t) => t.message === message)) return
	const id = `${Date.now()}${Math.random()}`
	store.toasts.push({ id, message, kind })
	setTimeout(() => (store.toasts = store.toasts.filter((t) => t.id !== id)), kind === "error" ? 6500 : 3500)
}

let initialised = null
export function init() {
	return (initialised ||= (async () => {
		window.addEventListener("online", () => {
			store.online = true
			flush()
		})
		window.addEventListener("offline", () => (store.online = false))
		await refreshQueueState()
		if (boot.logged_in) await loadSession()
		store.ready = true
		if (store.session) afterLogin()
	})())
}

async function loadSession() {
	try {
		store.session = await call("session", {}, { get: true })
		window.csrf_token = store.session.csrf_token
		await queue.cache("session", store.session)
	} catch (e) {
		store.session = e.server ? null : (await queue.cached("session")) || null
	}
}

export async function login(mobile, password) {
	const session = await call("login", { mobile, password })
	store.session = session
	window.csrf_token = session.csrf_token
	await queue.cache("session", session)
	afterLogin()
}

export async function logout() {
	try {
		await call("logout")
	} catch (e) {
		/* signed out locally anyway */
	}
	await queue.cache("session", null)
	store.session = null
	window.location.href = "/driver/login"
}

let started = false
function afterLogin() {
	if (started) return
	started = true
	registerServiceWorker().then((registration) => {
		store.registration = registration
		store.push = pushEnabled()
		if (store.push) enablePush(registration, onPush).catch(() => {})
	})
	try {
		connectSocket(() => refreshAll())
	} catch (e) {
		/* realtime is a convenience; pull-to-refresh still works */
	}
	setInterval(() => store.pending && navigator.onLine && flush(), 20000)
	flush()
}

function onPush(data) {
	toast([data.title, data.body].filter(Boolean).join(" — "))
	refreshAll()
}

export async function turnOnPush() {
	let ok = false
	try {
		ok = await enablePush(store.registration, onPush)
	} catch (e) {
		ok = false
	}
	store.push = ok
	toast(ok ? "الإشعارات اتفعلت ✅" : "مقدرناش نفعّل الإشعارات. اسمح بيها من إعدادات المتصفح.", ok ? "info" : "error")
	return ok
}

export async function loadTrips(scope = "active") {
	const key = `trips:${scope}`
	let rows
	try {
		rows = await call("trips", { scope }, { get: true })
		await queue.cache(key, rows)
	} catch (e) {
		if (e.server) toast(e.message, "error")
		rows = (await queue.cached(key)) || []
	}
	if (scope === "active") store.trips = rows
	else store.history = rows
}

export async function loadTrip(name) {
	const saved = await queue.cached(`trip:${name}`)
	if (store.current?.name !== name) store.current = saved || null
	if (store.pending && saved) return store.current // the phone's copy has the steps not sent yet
	try {
		await remember(await call("trip", { name }, { get: true }))
	} catch (e) {
		if (e.server) toast(e.message, "error")
	}
	return store.current
}

async function remember(trip) {
	await queue.cache(`trip:${trip.name}`, trip)
	if (!store.current || store.current.name === trip.name) store.current = trip
}

function refreshAll() {
	loadTrips("active")
	if (store.current) loadTrip(store.current.name)
}

// A driver's step goes straight to the server when online. Without a connection (or while
// earlier steps are still waiting) it is queued with the time it was pressed and shown on the
// phone at once.
export async function act(method, args, optimistic) {
	args = { ...args, client_time: localNow() }
	if (navigator.onLine && !store.pending) {
		try {
			const trip = await call(method, args)
			await remember(trip)
			if (trip.code_error) toast(trip.code_error, "error")
			return trip
		} catch (e) {
			if (e.server) {
				toast(e.message, "error")
				throw e
			}
		}
	}
	await queue.enqueue(method, args)
	await refreshQueueState()
	if (optimistic && store.current) {
		optimistic(store.current)
		await queue.cache(`trip:${store.current.name}`, store.current)
	}
	// The banner keeps count; say it once, for the first step kept on the phone.
	if (store.pending === 1) toast("اتسجلت على الموبايل، وهتتبعت أول ما النت يرجع", "warn")
	return store.current
}

let flushing = false
export async function flush() {
	if (flushing || !navigator.onLine) return
	flushing = true
	try {
		const items = await queue.pending()
		if (!items.length) return
		try {
			const session = await call("session", {}, { get: true })
			window.csrf_token = session.csrf_token
		} catch (e) {
			if (e.server) toast("سجّل الدخول تاني علشان الخطوات المتسجلة تتبعت.", "error")
			return
		}
		for (const item of items) {
			if (item.error) break
			try {
				const trip = await call(item.method, item.args)
				await queue.drop(item.id)
				if (trip?.name) await queue.cache(`trip:${trip.name}`, trip)
				if (trip?.code_error) toast(trip.code_error, "error")
			} catch (e) {
				if (!e.server) break
				await queue.markFailed(item.id, e.message)
				toast(`خطوة متسجلة ما اتقبلتش: ${e.message}`, "error")
				break
			}
		}
		await refreshQueueState()
		if (!store.pending) refreshAll()
	} finally {
		flushing = false
	}
}

async function refreshQueueState() {
	const items = await queue.pending()
	store.pending = items.length
	store.failed = items.find((i) => i.error) || null
}

export async function discardFailed() {
	if (!store.failed) return
	await queue.drop(store.failed.id)
	await refreshQueueState()
	flush()
}
