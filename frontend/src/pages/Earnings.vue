<template>
	<main class="px-4 pt-5">
		<h1 class="mb-4 text-xl font-bold">مستحقاتي</h1>
		<div class="mb-4 grid grid-cols-3 gap-2">
			<div v-for="c in cards" :key="c.label" class="card !p-3 text-center">
				<div class="text-xs muted">{{ c.label }}</div>
				<div class="mt-1 text-base font-bold" :style="c.brand ? 'color: var(--brand-text)' : ''">{{ money(c.value) }}</div>
			</div>
		</div>
		<div class="space-y-2">
			<router-link v-for="t in data.trips" :key="t.name" :to="`/trip/${t.name}`" class="card flex items-center justify-between !py-3">
				<div>
					<div class="font-semibold">{{ t.name }} · {{ t.project }}</div>
					<div class="text-sm muted">{{ when(t.finished_on || t.cancelled_on) }}</div>
				</div>
				<div class="text-left">
					<div class="font-bold">{{ money(t.total_amount) }}</div>
					<span class="pill" :class="t.paid ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-700'">
						{{ t.paid ? "اتصرف" : t.status === "منتهية" ? "قيد المراجعة" : t.status === "ملغاة" ? "تعويض" : "معتمد" }}
					</span>
				</div>
			</router-link>
			<p v-if="!data.trips.length" class="card text-center muted">لسه مفيش مستحقات.</p>
		</div>
	</main>
</template>

<script setup>
import { computed, onMounted, reactive } from "vue"
import { call } from "../api"
import { money, when } from "../format"
import * as queue from "../queue"
import { toast } from "../store"

const data = reactive({ summary: {}, trips: [] })
const cards = computed(() => [
	{ label: "قيد المراجعة", value: data.summary.pending_review },
	{ label: "معتمد", value: data.summary.approved, brand: true },
	{ label: "اتصرف", value: data.summary.paid },
])

onMounted(async () => {
	try {
		Object.assign(data, await call("earnings", {}, { get: true }))
		await queue.cache("earnings", data)
	} catch (e) {
		if (e.server) toast(e.message, "error")
		Object.assign(data, (await queue.cached("earnings")) || {})
	}
})
</script>
