// Push notifications through Frappe's push service: the same protocol as Frappe's
// FrappePushNotification client. The Firebase web config comes from the relay that
// push_relay_server_url points at, and the device token is registered with
// frappe.push_notification.subscribe under the project "ms_fleet".
import { boot } from "./boot"

const PROJECT = "ms_fleet"
const TOKEN_KEY = `firebase_token_${PROJECT}`
const CONFIG_KEY = `firebase_config_${PROJECT}`

export const pushAvailable = () => Boolean(boot.push_enabled && boot.push_relay_server_url && "Notification" in window)

export async function webConfig() {
	const saved = localStorage.getItem(CONFIG_KEY)
	if (saved) return JSON.parse(saved)
	const response = await fetch(`${boot.push_relay_server_url}/api/method/notification_relay.api.get_config?project_name=${PROJECT}`)
	const data = await response.json()
	if (!data.config) throw new Error("push relay not configured")
	localStorage.setItem(CONFIG_KEY, JSON.stringify(data))
	return data
}

export async function registerServiceWorker() {
	if (!("serviceWorker" in navigator)) return null
	let url = "/api/method/ms_fleet.api.driver.service_worker"
	if (pushAvailable()) {
		try {
			const { config } = await webConfig()
			url += "?config=" + encodeURIComponent(JSON.stringify(config))
		} catch (e) {
			/* notifications stay off; the app still works offline */
		}
	}
	try {
		return await navigator.serviceWorker.register(url, { scope: "/driver" })
	} catch (e) {
		return null
	}
}

export async function enablePush(registration, onMessage) {
	if (!pushAvailable() || !registration) return false
	const permission = await Notification.requestPermission()
	if (permission !== "granted") return false
	const [{ initializeApp }, messaging] = await Promise.all([import("firebase/app"), import("firebase/messaging")])
	if (!(await messaging.isSupported())) return false
	const { config, vapid_public_key } = await webConfig()
	const app = initializeApp(config)
	const client = messaging.getMessaging(app)
	const token = await messaging.getToken(client, { vapidKey: vapid_public_key, serviceWorkerRegistration: registration })
	const old = localStorage.getItem(TOKEN_KEY)
	if (token && token !== old) {
		if (old) await fetch(`/api/method/frappe.push_notification.unsubscribe?fcm_token=${old}&project_name=${PROJECT}`).catch(() => {})
		const response = await fetch(`/api/method/frappe.push_notification.subscribe?fcm_token=${token}&project_name=${PROJECT}`)
		if (!response.ok) return false
		localStorage.setItem(TOKEN_KEY, token)
	}
	messaging.onMessage(client, (payload) => onMessage?.(payload.data || {}))
	return true
}

export const pushEnabled = () => pushAvailable() && Notification.permission === "granted" && Boolean(localStorage.getItem(TOKEN_KEY))
