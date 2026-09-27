<template>
	<div class="pointer-events-none fixed inset-x-0 top-14 z-40 mx-auto flex max-w-xl flex-col gap-2 px-4" aria-live="polite">
		<div v-for="t in store.toasts" :key="t.id" class="rounded-xl px-4 py-3 text-sm font-semibold shadow-lg"
			:class="t.kind === 'error' ? 'bg-red-600 text-white' : t.kind === 'warn' ? 'bg-amber-400 text-black' : 'bg-gray-900 text-white'">
			{{ t.message }}
		</div>
	</div>
</template>

<script setup>
import { store } from "../store"
</script>
