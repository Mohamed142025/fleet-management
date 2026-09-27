<template>
	<main class="px-4 pt-5">
		<header class="mb-4 flex items-center justify-between">
			<div>
				<p class="text-sm muted">أهلاً</p>
				<h1 class="text-xl font-bold">{{ store.session?.full_name }}</h1>
			</div>
			<button class="btn btn-outline !w-auto !py-2" :disabled="loading" @click="load">{{ loading ? "…" : "تحديث" }}</button>
		</header>

		<div v-if="pushAvailable() && !store.push" class="card mb-4 flex items-center gap-3" style="background: var(--brand-soft)">
			<Icon name="bell" :size="26" />
			<p class="flex-1 text-sm font-semibold">فعّل الإشعارات علشان توصلك الرحلات الجديدة على طول.</p>
			<button class="btn btn-primary !w-auto !py-2" @click="turnOnPush">تفعيل</button>
		</div>

		<div class="mb-4 grid grid-cols-2 gap-2 rounded-xl p-1" style="background: var(--brand-soft)">
			<button v-for="t in tabs" :key="t.key" class="rounded-lg py-2 text-sm font-semibold"
				:style="tab === t.key ? 'background: var(--surface)' : ''" @click="tab = t.key">{{ t.label }}</button>
		</div>

		<div class="space-y-3">
			<TripCard v-for="trip in list" :key="trip.name" :trip="trip" />
			<p v-if="!list.length && !loading" class="card text-center muted">
				{{ tab === "active" ? "مفيش رحلات مسندة ليك دلوقتي." : "لسه مفيش رحلات سابقة." }}
			</p>
		</div>
	</main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue"
import Icon from "../components/Icon.vue"
import TripCard from "../components/TripCard.vue"
import { pushAvailable } from "../push"
import { loadTrips, store, turnOnPush } from "../store"

const tabs = [
	{ key: "active", label: "الحالية" },
	{ key: "history", label: "السابقة" },
]
const tab = ref("active")
const loading = ref(false)
const list = computed(() => (tab.value === "active" ? store.trips : store.history))

async function load() {
	loading.value = true
	await loadTrips(tab.value)
	loading.value = false
}
onMounted(load)
watch(tab, load)
</script>
