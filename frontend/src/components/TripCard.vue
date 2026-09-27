<template>
	<router-link :to="`/trip/${trip.name}`" class="card block">
		<div class="flex items-center justify-between gap-2">
			<StatusPill :status="trip.status" />
			<span class="text-sm muted">{{ when(trip.scheduled_time) }}</span>
		</div>
		<div class="mt-3 text-lg font-bold leading-snug">
			{{ first }} <span class="muted">←</span> {{ last }}
		</div>
		<div class="mt-1 flex flex-wrap gap-x-3 text-sm muted">
			<span>{{ trip.project_name || trip.project }}</span>
			<span>{{ trip.vehicle_type }}</span>
			<span v-if="trip.stops.length > 2">{{ trip.stops.length }} نقاط</span>
		</div>
		<div v-if="amount" class="mt-3 text-base font-bold" style="color: var(--brand-text)">{{ amount }}</div>
	</router-link>
</template>

<script setup>
import { computed } from "vue"
import { money, when } from "../format"
import StatusPill from "./StatusPill.vue"

const props = defineProps({ trip: Object })
const first = computed(() => props.trip.stops[0]?.location)
const last = computed(() => props.trip.stops[props.trip.stops.length - 1]?.location)
const amount = computed(() => {
	if (props.trip.is_company_vehicle) return ""
	if (props.trip.total_amount) return money(props.trip.total_amount)
	return props.trip.expected_amount ? `المتوقع ${money(props.trip.expected_amount)}` : ""
})
</script>
