import { createRouter, createWebHistory } from "vue-router"
import { init, store } from "./store"

const routes = [
	{ path: "/", name: "trips", component: () => import("./pages/Trips.vue") },
	{ path: "/trip/:name", name: "trip", component: () => import("./pages/Trip.vue") },
	{ path: "/earnings", name: "earnings", component: () => import("./pages/Earnings.vue") },
	{ path: "/account", name: "account", component: () => import("./pages/Account.vue") },
	{ path: "/login", name: "login", component: () => import("./pages/Login.vue") },
	{ path: "/:pathMatch(.*)*", redirect: "/" },
]

export const router = createRouter({ history: createWebHistory("/driver"), routes })

router.beforeEach(async (to) => {
	await init()
	if (!store.session && to.name !== "login") return { name: "login" }
	if (store.session && to.name === "login") return { name: "trips" }
})
