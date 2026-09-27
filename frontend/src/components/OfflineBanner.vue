<template>
	<div v-if="!store.online || store.pending" class="sticky top-0 z-30 px-4 py-2 text-center text-sm font-semibold"
		:class="store.failed ? 'bg-red-600 text-white' : !store.online ? 'bg-amber-500 text-black' : 'bg-sky-600 text-white'">
		<template v-if="store.failed">
			خطوة ما اتقبلتش: {{ store.failed.error }}
			<button class="mr-2 underline" @click="discardFailed">تجاهلها</button>
		</template>
		<template v-else-if="!store.online">
			مفيش نت — خطواتك بتتسجل على الموبايل<span v-if="store.pending"> ({{ store.pending }})</span> وهتتبعت أول ما النت يرجع
		</template>
		<template v-else>بنبعت الخطوات المتسجلة ({{ store.pending }})…</template>
	</div>
</template>

<script setup>
import { discardFailed, store } from "../store"
</script>
