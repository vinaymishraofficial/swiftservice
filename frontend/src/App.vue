<template>
	<div class="h-full isolate">
		<template v-if="session.isLoggedIn">
			<component :is="layoutComponent">
				<router-view />
			</component>
		</template>
		<div
			v-else
			class="flex h-full items-center justify-center bg-surface-gray-1"
		>
			<div
				class="rounded-xl border border-outline-gray-2 bg-surface-modal p-8 text-center shadow-sm"
			>
				<img :src="logoUrl" class="mx-auto mb-4 h-12 w-12 rounded-lg" alt="" />
				<h1 class="text-xl font-semibold text-ink-gray-9">SwiftService</h1>
				<p class="mt-2 text-sm text-ink-gray-6">Please login to continue</p>
				<a
					href="/login?redirect-to=/swiftservice"
					class="mt-4 inline-flex rounded-lg bg-ink-gray-9 px-4 py-2 text-sm text-white"
				>
					Login
				</a>
			</div>
		</div>
		<!-- FrappeUIProvider/ToastViewport (reka-ui) crashes Vue mount with
		     nextSibling null on this Vue/frappe-ui combo — keep Dialogs only. -->
		<Dialogs v-if="extrasReady" />
	</div>
</template>

<script setup>
import { computed, defineAsyncComponent, onMounted, ref } from "vue";
import { Dialogs } from "frappe-ui";
import DesktopLayout from "@/components/DesktopLayout.vue";
import { sessionStore } from "@/stores/session";
import { initializeTheme } from "@/composables/theme";
import { useSettings } from "@/stores/settings";
import { isMobileView } from "@/composables/mobile";

const MobileLayout = defineAsyncComponent(() => import("@/components/MobileLayout.vue"));

const session = sessionStore();
const { load: loadBrand } = useSettings();
const logoUrl = "/assets/swiftservice/logo-white.png";
const extrasReady = ref(false);

const layoutComponent = computed(() => (isMobileView.value ? MobileLayout : DesktopLayout));

onMounted(() => {
	try {
		initializeTheme();
	} catch (e) {
		console.warn("theme init failed", e);
	}
	loadBrand(true).catch(() => {});
	requestAnimationFrame(() => {
		extrasReady.value = true;
	});
});
</script>
