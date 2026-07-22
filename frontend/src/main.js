import "./index.css";

import { createApp } from "vue";
import { createPinia } from "pinia";
import {
	FrappeUI,
	Button,
	TextInput,
	Badge,
	Avatar,
	Dropdown,
	Tooltip,
	setConfig,
	frappeRequest,
	FeatherIcon,
} from "frappe-ui";

import App from "./App.vue";
import router from "./router";
import { sessionStore } from "./stores/session";

setConfig("resourceFetcher", frappeRequest);

const app = createApp(App);
const pinia = createPinia();

app.use(FrappeUI, { socketio: false });
app.use(pinia);
app.use(router);

app.component("Button", Button);
app.component("TextInput", TextInput);
app.component("Badge", Badge);
app.component("Avatar", Avatar);
app.component("Dropdown", Dropdown);
app.component("Tooltip", Tooltip);
app.component("FeatherIcon", FeatherIcon);

app.config.errorHandler = (err, instance, info) => {
	console.error("SwiftService render error:", err, info);
};

// Visible in DevTools so we know which bundle is loaded
console.info("[SwiftService] build 2026-07-22-0955 (no FrappeUIProvider/ToastViewport)");

async function boot() {
	if (window.__SS_MOUNTED__) {
		console.warn("[SwiftService] skip duplicate mount");
		return;
	}
	window.__SS_MOUNTED__ = true;
	try {
		const session = sessionStore();
		await session.fetchUser();
		app.mount("#app");
		if (session.isLoggedIn) {
			import("frappe-ui")
				.then(({ call }) => call("swiftservice.api.ensure_demo_masters"))
				.catch(() => {});
		}
	} catch (err) {
		console.error("SwiftService boot error:", err);
		window.__SS_MOUNTED__ = false;
		const el = document.getElementById("app");
		if (el && !el.querySelector(".ss-shell")) {
			el.innerHTML = `<div style="padding:2rem;font-family:system-ui">SwiftService failed to start.<pre>${String(err?.message || err)}</pre></div>`;
		}
	}
}

boot();
