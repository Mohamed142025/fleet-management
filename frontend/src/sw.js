// The driver app's service worker (served by ms_fleet.api.driver.service_worker, scope /driver).
// It keeps the app and its last page for use without a connection, and shows push notifications
// from Frappe's push service (Firebase), as the HRMS app does. The Firebase web config comes in
// the ?config= of the worker's URL.
import { cleanupOutdatedCaches, precacheAndRoute } from "workbox-precaching"
import { NavigationRoute, registerRoute } from "workbox-routing"
import { clientsClaim } from "workbox-core"
import { initializeApp } from "firebase/app"
import { getMessaging, onBackgroundMessage } from "firebase/messaging/sw"

self.skipWaiting()
clientsClaim()
precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

// Every /driver/... address is the same single-page app, so one copy of the page (the latest one
// fetched) opens any of them without a connection.
const PAGES = "ms-fleet-pages"
const SHELL = "/driver"

function fetchWithin(request, ms) {
	return Promise.race([fetch(request), new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), ms))])
}

registerRoute(
	new NavigationRoute(
		async ({ request }) => {
			const cache = await caches.open(PAGES)
			try {
				const response = await fetchWithin(request, 6000)
				if (response.ok) await cache.put(SHELL, response.clone())
				return response
			} catch (e) {
				return (await cache.match(SHELL)) || Response.error()
			}
		},
		{ allowlist: [/^\/driver(\/|$)/] }
	)
)

self.addEventListener("install", (event) => {
	event.waitUntil(
		caches
			.open(PAGES)
			.then((cache) => cache.add(SHELL))
			.catch(() => {})
	)
})

const config = new URL(self.location).searchParams.get("config")
if (config) {
	try {
		const messaging = getMessaging(initializeApp(JSON.parse(config)))
		onBackgroundMessage(messaging, (payload) => {
			const data = payload.data || {}
			self.registration.showNotification(data.title || "", {
				body: data.body || "",
				icon: data.notification_icon || "/assets/ms_fleet/driver-icons/icon-192.png",
				badge: "/assets/ms_fleet/driver-icons/icon-192.png",
				dir: "rtl",
				lang: "ar",
				data: { url: data.click_action || "/driver" },
			})
		})
	} catch (e) {
		// A wrong config leaves the app working, without notifications.
	}
}

self.addEventListener("notificationclick", (event) => {
	event.notification.close()
	const url = event.notification.data?.url || "/driver"
	event.waitUntil(
		self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
			for (const client of windows) {
				if (client.url.includes("/driver") && "focus" in client) {
					client.navigate(url)
					return client.focus()
				}
			}
			return self.clients.openWindow(url)
		})
	)
})
