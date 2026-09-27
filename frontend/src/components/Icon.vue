<template>
	<svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
		stroke-linejoin="round" aria-hidden="true" class="shrink-0">
		<path v-for="(d, i) in paths[name] || []" :key="i" :d="d" />
	</svg>
</template>

<script setup>
// A few line icons (drawn inline, so they look the same on every phone).
defineProps({ name: String, size: { type: [Number, String], default: 20 } })
const paths = {
	truck: ["M3 6h11v10H3z", "M14 10h4l3 3v3h-7", "M7 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4z", "M17 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"],
	wallet: ["M3 7h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z", "M3 7l12-4 2 4", "M17 13h.01"],
	user: ["M20 21a8 8 0 0 0-16 0", "M12 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"],
	pin: ["M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z", "M12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z"],
	navigation: ["M3 11l18-8-8 18-2-8z"],
	camera: ["M4 8h3l2-3h6l2 3h3v11H4z", "M12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"],
	flag: ["M5 21V4", "M5 4h11l-2 4 2 4H5"],
	bell: ["M18 16H6l1.5-2V10a4.5 4.5 0 0 1 9 0v4z", "M10 19a2 2 0 0 0 4 0"],
	check: ["M5 12l5 5 9-10"],
	back: ["M9 18l6-6-6-6"],
	go: ["M5 12h14", "M13 6l6 6-6 6"],
}
</script>
