<template>
	<div v-if="store.ready" class="mx-auto min-h-screen max-w-xl" :class="showNav ? 'pb-24' : ''">
		<OfflineBanner />
		<router-view />
		<BottomNav v-if="showNav" />
		<Toasts />
	</div>
	<div v-else class="flex min-h-screen items-center justify-center muted">…</div>
</template>

<script setup>
import { computed } from "vue"
import { useRoute } from "vue-router"
import { store } from "./store"
import BottomNav from "./components/BottomNav.vue"
import OfflineBanner from "./components/OfflineBanner.vue"
import Toasts from "./components/Toasts.vue"

const route = useRoute()
const showNav = computed(() => store.session && route.name && route.name !== "login")
</script>
