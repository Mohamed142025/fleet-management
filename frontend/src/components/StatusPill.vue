<template>
	<span class="pill" :class="STATUS_STYLE[status] || 'bg-gray-100 text-gray-700'">{{ status }}</span>
</template>

<script setup>
import { STATUS_STYLE } from "../format"

defineProps({ status: String })
</script>
