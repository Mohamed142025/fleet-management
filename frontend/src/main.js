import { createApp } from "vue"
import App from "./App.vue"
import { router } from "./router"
import { boot } from "./boot"
import "./style.css"

// The company's colour from Fleet Settings.
if (boot.theme_color) document.documentElement.style.setProperty("--brand", boot.theme_color)

createApp(App).use(router).mount("#app")
