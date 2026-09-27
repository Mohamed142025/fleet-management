<template>
	<main class="flex min-h-screen flex-col justify-center px-6">
		<div class="mb-8 text-center">
			<img v-if="boot.logo" :src="boot.logo" alt="" class="mx-auto mb-4 h-16 w-16 rounded-2xl object-contain" />
			<div v-else class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl text-white" style="background: var(--brand)"><Icon name="truck" :size="34" /></div>
			<h1 class="text-2xl font-bold">{{ boot.app_name || "MS Fleet" }}</h1>
			<p class="mt-1 muted">تطبيق السواقين</p>
		</div>
		<form class="card space-y-4" @submit.prevent="submit">
			<label class="block">
				<span class="mb-1 block text-sm font-semibold">رقم الموبايل</span>
				<input v-model.trim="mobile" class="input" type="tel" inputmode="tel" autocomplete="username" dir="ltr" required />
			</label>
			<label class="block">
				<span class="mb-1 block text-sm font-semibold">كلمة السر</span>
				<input v-model="password" class="input" type="password" autocomplete="current-password" dir="ltr" required />
			</label>
			<p v-if="error" class="text-sm font-semibold text-red-600">{{ error }}</p>
			<button class="btn btn-primary" :disabled="busy">{{ busy ? "…" : "دخول" }}</button>
		</form>
	</main>
</template>

<script setup>
import { ref } from "vue"
import { useRouter } from "vue-router"
import { boot } from "../boot"
import Icon from "../components/Icon.vue"
import { login } from "../store"

const router = useRouter()
const mobile = ref("")
const password = ref("")
const error = ref("")
const busy = ref(false)

async function submit() {
	busy.value = true
	error.value = ""
	try {
		await login(mobile.value, password.value)
		router.replace("/")
	} catch (e) {
		error.value = e.server ? e.message : "مفيش نت. جرّب تاني."
	} finally {
		busy.value = false
	}
}
</script>
