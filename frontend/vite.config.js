import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import { VitePWA } from "vite-plugin-pwa"
import path from "path"

// Built into ms_fleet/public/driver and served from /assets/ms_fleet/driver/. The page itself is
// ms_fleet/www/driver.html (a copy of the built index.html, filled in by www/driver.py). The
// service worker is served by ms_fleet.api.driver.service_worker so it may control /driver.
export default defineConfig({
	base: "/assets/ms_fleet/driver/",
	plugins: [
		vue(),
		VitePWA({
			strategies: "injectManifest",
			srcDir: "src",
			filename: "sw.js",
			injectRegister: null,
			manifest: false,
			// The worker is served from /api/method/..., so the precached files need absolute URLs.
			injectManifest: { globPatterns: ["**/*.{js,css,png,svg,woff2}"], modifyURLPrefix: { "": "/assets/ms_fleet/driver/" } },
		}),
	],
	resolve: { alias: { "@": path.resolve(__dirname, "src") } },
	build: {
		outDir: "../ms_fleet/public/driver",
		emptyOutDir: true,
		target: "es2018",
		chunkSizeWarningLimit: 700,
	},
})
