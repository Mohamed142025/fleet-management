<template>
	<main v-if="trip" class="space-y-4 px-4 pt-4">
		<header class="flex items-center gap-3">
			<router-link to="/" class="btn btn-outline !w-auto !px-3 !py-2" aria-label="رجوع"><Icon name="back" /></router-link>
			<div class="flex-1">
				<h1 class="text-lg font-bold leading-tight">{{ trip.project_name || trip.project }}</h1>
				<div class="text-sm muted">{{ trip.name }} · {{ trip.project }}</div>
			</div>
			<StatusPill :status="trip.status" />
		</header>

		<section class="card grid grid-cols-2 gap-3 text-sm">
			<div><div class="muted">الميعاد</div><div class="font-semibold">{{ when(trip.scheduled_time) }}</div></div>
			<div><div class="muted">العربية</div><div class="font-semibold">{{ trip.vehicle }} · {{ trip.vehicle_type }}</div></div>
			<div><div class="muted">الحساب</div><div class="font-semibold">{{ trip.billing_mode }}<span v-if="trip.billing_mode === 'باليومية'"> ({{ trip.planned_days }} يوم)</span></div></div>
			<div v-if="!trip.is_company_vehicle">
				<div class="muted">{{ trip.total_amount ? "المستحق" : "المتوقع" }}</div>
				<div class="font-bold" style="color: var(--brand-text)">{{ money(trip.total_amount || trip.expected_amount) }}</div>
			</div>
			<div v-if="trip.request_notes" class="col-span-2"><div class="muted">تفاصيل</div><div>{{ trip.request_notes }}</div></div>
		</section>

		<!-- Assigned: accept or decline -->
		<section v-if="trip.status === 'مسندة'" class="card space-y-3">
			<p class="font-semibold">الرحلة دي اتسندت ليك. تقبلها؟</p>
			<button class="btn btn-primary" :disabled="busy" @click="run(accept)">قبول الرحلة</button>
			<template v-if="declining">
				<textarea v-model.trim="reason" class="input" rows="2" placeholder="سبب الرفض"></textarea>
				<button class="btn btn-danger" :disabled="busy || !reason" @click="run(decline)">تأكيد الرفض</button>
			</template>
			<button v-else class="btn btn-outline" @click="declining = true">رفض</button>
		</section>

		<!-- Accepted: start -->
		<section v-if="trip.status === 'مقبولة'" class="card space-y-3">
			<label v-if="trip.is_company_vehicle" class="block">
				<span class="mb-1 block text-sm font-semibold">قراءة العداد دلوقتي</span>
				<input v-model.number="odometer" class="input" type="number" inputmode="numeric" dir="ltr" />
			</label>
			<button class="btn btn-primary" :disabled="busy || (trip.is_company_vehicle && !odometer)" @click="run(start)">ابدأ الرحلة</button>
		</section>

		<!-- Stops -->
		<section class="space-y-3">
			<h2 class="font-bold">النقاط</h2>
			<article v-for="stop in trip.stops" :key="stop.idx" class="card"
				:style="isCurrent(stop) ? 'border-color: var(--brand); box-shadow: 0 0 0 2px color-mix(in srgb, var(--brand) 30%, transparent)' : ''">
				<div class="flex items-start gap-3">
					<div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold"
						:class="stop.departed_on || (stop.arrived_on && isLast(stop) && finished) ? 'bg-emerald-600 text-white' : ''"
						:style="!(stop.departed_on || (stop.arrived_on && isLast(stop) && finished)) ? 'background: var(--brand-soft)' : ''">
						<Icon v-if="stop.departed_on || (stop.arrived_on && isLast(stop) && finished)" name="check" :size="18" /><template v-else>{{ stop.idx }}</template>
					</div>
					<div class="flex-1">
						<div class="font-bold">{{ stop.location }}</div>
						<div class="text-sm muted">{{ stop.purpose }}<span v-if="stop.notes"> · {{ stop.notes }}</span></div>
						<div class="mt-1 flex flex-wrap gap-x-3 text-xs muted">
							<span v-if="stop.arrived_on">وصلت {{ time(stop.arrived_on) }}</span>
							<span v-if="stop.departed_on">اتحركت {{ time(stop.departed_on) }}</span>
							<span v-if="stop.photo" class="text-emerald-600">الصورة ✓</span>
							<span v-if="stop.needs_confirmation && stop.confirmed" class="text-emerald-600">✓ الاستلام متأكد</span>
							<span v-if="stop.out_of_range && stop.arrived_on" class="text-amber-600">بعيد عن النقطة</span>
						</div>
					</div>
				</div>

				<div v-if="inProgress && isCurrent(stop)" class="mt-4 space-y-2">
					<template v-if="!stop.arrived_on">
						<a class="btn btn-soft" :href="navigateUrl(stop.latitude, stop.longitude)" target="_blank" rel="noopener"><Icon name="navigation" /> افتح الملاحة</a>
						<button class="btn btn-primary" :disabled="busy" @click="run(() => arrive(stop))"><Icon name="pin" /> وصلت</button>
					</template>
					<template v-else>
						<button v-if="stop.needs_photo && !stop.photo" class="btn btn-primary" :disabled="busy" @click="run(() => photo(stop))">
							<Icon name="camera" /> صوّر {{ stop.purpose }}
						</button>
						<div v-if="stop.needs_confirmation && !stop.confirmed" class="space-y-2 rounded-xl p-3" style="background: var(--brand-soft)">
							<p class="text-sm font-semibold">كود المستلم</p>
							<div class="flex gap-2">
								<input v-model.trim="codes[stop.idx]" class="input !w-32 text-center text-lg tracking-widest" inputmode="numeric" maxlength="4" dir="ltr" />
								<button class="btn btn-primary !w-auto" :disabled="busy || (codes[stop.idx] || '').length !== 4" @click="run(() => confirmCode(stop))">تأكيد</button>
							</div>
							<p class="text-xs muted">أو المستلم يأكد الاستلام من حسابه.</p>
						</div>
						<button v-if="!isLast(stop)" class="btn btn-primary" :disabled="busy || (stop.needs_photo && !stop.photo)" @click="run(() => depart(stop))">
							<Icon name="go" /> اتحركت
						</button>
					</template>
				</div>
			</article>
		</section>

		<!-- Finish -->
		<section v-if="inProgress && allArrived" class="card space-y-3">
			<label v-if="trip.is_company_vehicle" class="block">
				<span class="mb-1 block text-sm font-semibold">قراءة العداد في النهاية</span>
				<input v-model.number="odometer" class="input" type="number" inputmode="numeric" dir="ltr" />
			</label>
			<button class="btn btn-primary" :disabled="busy || lastNeedsPhoto || (trip.is_company_vehicle && !odometer)" @click="run(finish)"><Icon name="flag" /> إنهاء الرحلة</button>
			<p v-if="lastNeedsPhoto" class="text-sm text-amber-600">صوّر آخر نقطة الأول.</p>
		</section>

		<!-- Result -->
		<section v-if="finished && !trip.is_company_vehicle" class="card space-y-1 text-sm">
			<h2 class="mb-2 font-bold">الحساب</h2>
			<template v-if="trip.total_amount">
				<div v-for="line in breakdown" :key="line.label" class="flex justify-between"><span class="muted">{{ line.label }}</span><span>{{ money(line.value) }}</span></div>
				<div class="flex justify-between border-t pt-2 text-base font-bold" style="border-color: var(--line)"><span>المستحق</span><span style="color: var(--brand-text)">{{ money(trip.total_amount) }}</span></div>
			</template>
			<p v-else class="muted">الرحلة بتتراجع من إدارة الحركة، والمبلغ هيظهر هنا.</p>
			<p v-if="trip.actual_km || trip.manual_km" class="muted">المسافة: {{ km(trip.manual_km || trip.actual_km) }}</p>
		</section>
		<section v-if="trip.status === 'ملغاة'" class="card text-sm">
			<p class="font-semibold">اتلغت: {{ trip.cancel_reason }}</p>
			<p v-if="trip.cancellation_compensation" class="mt-1">تعويض: <b>{{ money(trip.cancellation_compensation) }}</b></p>
		</section>
	</main>
	<p v-else class="card m-4 text-center muted">…</p>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue"
import { useRoute } from "vue-router"
import Icon from "../components/Icon.vue"
import StatusPill from "../components/StatusPill.vue"
import { takePhoto } from "../camera"
import { km, localNow, money, time, when } from "../format"
import { navigateUrl, position } from "../geo"
import { act, loadTrip, store, toast } from "../store"

const route = useRoute()
const trip = computed(() => (store.current?.name === route.params.name ? store.current : null))
const busy = ref(false)
const declining = ref(false)
const reason = ref("")
const odometer = ref(null)
const codes = reactive({})

watch(() => route.params.name, (name) => name && loadTrip(name), { immediate: true })

const inProgress = computed(() => trip.value?.status === "جارية")
const finished = computed(() => ["منتهية", "معتمدة للصرف", "مفوترة"].includes(trip.value?.status))
const allArrived = computed(() => trip.value?.stops.every((s) => s.arrived_on))
const isLast = (stop) => stop.idx === trip.value.stops.length
const current = computed(() => trip.value?.stops.find((s) => !s.departed_on && !(isLast(s) && s.arrived_on && finished.value)))
const isCurrent = (stop) => current.value?.idx === stop.idx
const lastNeedsPhoto = computed(() => {
	const last = trip.value?.stops[trip.value.stops.length - 1]
	return last?.needs_photo && !last.photo
})
const breakdown = computed(() =>
	[
		["أساس المسافة", trip.value.base_amount],
		["الرجوع الفاضي", trip.value.return_amount],
		["اليوميات", trip.value.daily_amount],
		["الإضافي", trip.value.overtime_amount],
		["ليلي / إجازة", trip.value.surcharge_amount],
		["الانتظار", trip.value.waiting_amount],
	]
		.filter(([, v]) => v)
		.map(([label, value]) => ({ label, value }))
)

async function run(step) {
	if (busy.value) return
	busy.value = true
	try {
		await step()
	} catch (e) {
		/* the message is already shown */
	} finally {
		busy.value = false
	}
}

const name = () => trip.value.name
const stopOf = (t, idx) => t.stops.find((s) => s.idx === idx)

const accept = () => act("accept", { name: name() }, (t) => (t.status = "مقبولة"))
const decline = () => act("decline", { name: name(), reason: reason.value }, (t) => (t.status = "مرفوضة من السواق"))
const start = () =>
	act("start", { name: name(), odometer: odometer.value }, (t) => {
		t.status = "جارية"
		t.started_on = localNow()
	}).then(() => (odometer.value = null))

async function arrive(stop) {
	const where = await position()
	if (!where) toast("مقدرناش نحدد موقعك. هنسجل الوصول، وفعّل الموقع (GPS) للنقاط الجاية.", "warn")
	await act("arrive", { name: name(), stop: stop.idx, ...(where || {}) }, (t) => (stopOf(t, stop.idx).arrived_on = localNow()))
}

async function photo(stop) {
	const data = await takePhoto()
	if (!data) return
	await act("photo", { name: name(), stop: stop.idx, data, filename: `${name()}-${stop.idx}.jpg` }, (t) => (stopOf(t, stop.idx).photo = "pending"))
}

async function confirmCode(stop) {
	await act("confirm_code", { name: name(), stop: stop.idx, code: codes[stop.idx] }, (t) => (stopOf(t, stop.idx).confirmed = 1))
	codes[stop.idx] = ""
}

const depart = (stop) => act("depart", { name: name(), stop: stop.idx }, (t) => (stopOf(t, stop.idx).departed_on = localNow()))

async function finish() {
	const where = await position(8000)
	await act("finish", { name: name(), odometer: odometer.value, ...(where || {}) }, (t) => {
		t.status = "منتهية"
		t.finished_on = localNow()
	})
}
</script>
