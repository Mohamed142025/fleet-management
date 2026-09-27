<template>
	<nav
		class="fixed inset-x-0 bottom-0 z-20 mx-auto flex max-w-xl justify-around border-t px-2 pb-[max(env(safe-area-inset-bottom),0.5rem)] pt-2"
		style="background: var(--surface); border-color: var(--line)"
	>
		<router-link v-for="item in items" :key="item.to" :to="item.to" class="flex flex-1 flex-col items-center gap-1 rounded-xl py-1 text-xs"
			:class="active(item) ? 'font-bold' : 'muted'" :style="active(item) ? 'color: var(--brand-text)' : ''">
			<Icon :name="item.icon" :size="22" />
			<span>{{ item.label }}</span>
		</router-link>
	</nav>
</template>

<script setup>
import { useRoute } from "vue-router"
import Icon from "./Icon.vue"

const route = useRoute()
const items = [
	{ to: "/", label: "رحلاتي", icon: "truck", names: ["trips", "trip"] },
	{ to: "/earnings", label: "مستحقاتي", icon: "wallet", names: ["earnings"] },
	{ to: "/account", label: "حسابي", icon: "user", names: ["account"] },
]
const active = (item) => item.names.includes(route.name)
</script>
