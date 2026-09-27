<template>
	<main class="space-y-4 px-4 pt-5">
		<h1 class="text-xl font-bold">حسابي</h1>
		<section class="card">
			<div class="text-lg font-bold">{{ store.session?.full_name }}</div>
			<div class="muted" dir="ltr">{{ store.session?.mobile }}</div>
			<div v-for="v in store.session?.vehicles || []" :key="v.name" class="mt-2 text-sm">
				<Icon name="truck" :size="16" class="inline" /> {{ v.name }} · {{ v.vehicle_type }} <span class="muted">({{ v.ownership }})</span>
			</div>
		</section>

		<section v-if="pushAvailable()" class="card flex items-center justify-between">
			<span class="font-semibold">الإشعارات</span>
			<span v-if="store.push" class="pill bg-emerald-100 text-emerald-800">شغالة</span>
			<button v-else class="btn btn-primary !w-auto !py-2" @click="turnOnPush">تفعيل</button>
		</section>

		<section class="card">
			<div class="flex items-center justify-between">
				<span class="font-semibold">كشف الحساب</span>
				<span class="text-lg font-bold" style="color: var(--brand-text)">{{ money(statement.balance) }}</span>
			</div>
			<p class="text-xs muted">الرصيد اللي ليك عند الشركة.</p>
			<ul class="mt-3 divide-y" style="border-color: var(--line)">
				<li v-for="(e, i) in statement.entries" :key="i" class="flex items-center justify-between py-2 text-sm">
					<div>
						<div class="font-semibold">{{ e.voucher_type === "Payment Entry" ? "دفعة" : "فاتورة مستحقات" }}</div>
						<div class="muted">{{ e.posting_date }} · {{ e.voucher_no }}</div>
					</div>
					<div class="font-bold" :class="e.debit ? 'text-emerald-600' : ''">{{ money(e.credit || -e.debit) }}</div>
				</li>
				<li v-if="!statement.entries.length" class="py-2 text-sm muted">لسه مفيش حركة.</li>
			</ul>
		</section>

		<button class="btn btn-outline" @click="logout">خروج</button>
	</main>
</template>

<script setup>
import { onMounted, reactive } from "vue"
import { call } from "../api"
import Icon from "../components/Icon.vue"
import { money } from "../format"
import { pushAvailable } from "../push"
import * as queue from "../queue"
import { logout, store, toast, turnOnPush } from "../store"

const statement = reactive({ balance: 0, entries: [] })
onMounted(async () => {
	try {
		Object.assign(statement, await call("statement", {}, { get: true }))
		await queue.cache("statement", statement)
	} catch (e) {
		if (e.server) toast(e.message, "error")
		Object.assign(statement, (await queue.cached("statement")) || {})
	}
})
</script>
