<template>
	<div class="ss-shell flex h-[100dvh] w-screen flex-col overflow-hidden bg-surface-gray-1">
		<!-- Top bar -->
		<header
			class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-2 bg-surface-white px-2"
		>
			<Button variant="ghost" class="!size-9" @click="mobileSidebarOpened = true">
				<template #prefix>
					<span class="lucide-menu size-5 text-ink-gray-8" aria-hidden="true" />
				</template>
			</Button>
			<div class="min-w-0 flex-1 truncate text-base font-medium text-ink-gray-9">
				{{ headerTitle }}
			</div>
			<Button variant="ghost" class="!size-9" @click="showCommandPalette = true">
				<template #prefix>
					<span class="lucide-search size-5 text-ink-gray-8" aria-hidden="true" />
				</template>
			</Button>
			<Button variant="ghost" class="relative !size-9" @click="openNotifications">
				<template #prefix>
					<span class="lucide-bell size-5 text-ink-gray-8" aria-hidden="true" />
				</template>
				<span
					v-if="notifStore.unreadCount"
					class="absolute right-1.5 top-1.5 size-1.5 rounded-full bg-surface-blue-5"
				/>
			</Button>
			<UserDropdown :isCollapsed="true" :module-id="activeModuleId" @update:moduleId="onModuleSwitch" />
		</header>

		<!-- Content -->
		<main class="min-h-0 flex-1 overflow-hidden bg-surface-white">
			<slot />
		</main>

		<!-- Bottom nav (field engineer primary) -->
		<nav
			class="flex shrink-0 items-stretch justify-around border-t border-outline-gray-2 bg-surface-white pb-[env(safe-area-inset-bottom)]"
		>
			<button
				v-for="item in bottomItems"
				:key="item.to"
				type="button"
				class="flex min-w-0 flex-1 flex-col items-center gap-0.5 px-1 py-2 text-[11px] font-medium"
				:class="isActive(item.to) ? 'text-ink-gray-9' : 'text-ink-gray-5'"
				@click="go(item.to)"
			>
				<span :class="[item.icon, 'size-5']" aria-hidden="true" />
				<span class="truncate">{{ item.label }}</span>
			</button>
			<button
				type="button"
				class="flex min-w-0 flex-1 flex-col items-center gap-0.5 px-1 py-2 text-[11px] font-medium text-ink-gray-5"
				@click="mobileSidebarOpened = true"
			>
				<span class="lucide-layout-grid size-5" aria-hidden="true" />
				<span>More</span>
			</button>
		</nav>

		<!-- Drawer menu -->
		<Dialog v-model="mobileSidebarOpened" :options="{ size: 'sm', title: 'Menu' }">
			<template #body-content>
				<div class="flex max-h-[70vh] flex-col gap-1 overflow-y-auto">
					<button
						v-for="link in flatLinks"
						:key="link.to + link.label"
						type="button"
						class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-ink-gray-8 hover:bg-surface-gray-2"
						:class="isActive(link.to) ? 'bg-surface-selected font-medium' : ''"
						@click="go(link.to)"
					>
						<component
							:is="link.icon"
							v-if="link.icon"
							class="size-4 shrink-0 text-ink-gray-6"
						/>
						{{ link.label }}
					</button>
				</div>
			</template>
		</Dialog>

		<SettingsModal v-if="modalsReady" />
		<GlobalSearch v-model="showCommandPalette" />
		<Notifications />
		<HelpModal
			v-if="modalsReady && showHelpModal"
			v-model="showHelpModal"
			v-model:articles="articles"
			:appName="ONBOARDING_APP"
			title="SwiftService"
			:logo="SwiftServiceLogo"
			:docsLink="docsLink"
		/>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, Dialog } from "frappe-ui";
import { HelpModal, showHelpModal, useOnboarding } from "frappe-ui/frappe";
import SettingsModal from "@/components/Settings/SettingsModal.vue";
import UserDropdown from "@/components/UserDropdown.vue";
import SwiftServiceLogo from "@/components/SwiftServiceLogo.vue";
import GlobalSearch from "@/components/GlobalSearch.vue";
import Notifications from "@/components/Notifications.vue";
import { helpArticles } from "@/config/help";
import { ONBOARDING_APP, createOnboardingSteps } from "@/config/onboarding";
import {
	getModuleForPath,
	getModuleSidebar,
	getStoredModuleId,
	setStoredModuleId,
} from "@/config/modules";
import { mobileSidebarOpened } from "@/composables/mobile";
import { notificationsStore } from "@/stores/notifications";

const route = useRoute();
const router = useRouter();
const articles = ref(helpArticles);
const docsLink = `${window.location.origin}/swiftservice/help`;
const modalsReady = ref(false);
const activeModuleId = ref(getStoredModuleId() || "home");
const showCommandPalette = ref(false);
const notifStore = notificationsStore();

const onboarding = useOnboarding(ONBOARDING_APP);
const setUp = onboarding?.setUp || (() => {});

const bottomItems = [
	{ label: "Home", to: "/dashboard", icon: "lucide-home" },
	{ label: "Visits", to: "/engineer-visits", icon: "lucide-hard-hat" },
	{ label: "Tickets", to: "/service-requests", icon: "lucide-clipboard-list" },
	{ label: "Dispatch", to: "/dispatch", icon: "lucide-map" },
];

const headerTitle = computed(() => {
	const mod = getModuleForPath(route.path, route.query?.module, activeModuleId.value);
	return mod?.label || "SwiftService";
});

function isActive(to) {
	if (!to) return false;
	const path = String(to).split("?")[0];
	if (path === "/dashboard") return route.path === "/dashboard" || route.path === "/";
	return route.path === path || route.path.startsWith(`${path}/`);
}

function go(to) {
	mobileSidebarOpened.value = false;
	if (to) router.push(to);
}

function onModuleSwitch(id) {
	activeModuleId.value = id;
	setStoredModuleId(id);
}

function openNotifications() {
	document.documentElement.style.setProperty("--ss-sidebar-width", "0px");
	notifStore.toggle(true);
}

const flatLinks = computed(() => {
	const sections = getModuleSidebar(activeModuleId.value, isActive) || [];
	const out = [];
	for (const sec of sections) {
		for (const item of sec.items || []) {
			if (item.to) out.push({ label: item.label, to: item.to, icon: item.icon });
		}
	}
	if (!out.length) {
		return bottomItems.map((i) => ({ label: i.label, to: i.to }));
	}
	return out;
});

function syncModuleFromRoute() {
	const preferred = activeModuleId.value || getStoredModuleId();
	const fromPath = getModuleForPath(
		route.path,
		typeof route.query?.module === "string" ? route.query.module : "",
		preferred,
	);
	if (fromPath?.id && fromPath.id !== activeModuleId.value) {
		activeModuleId.value = fromPath.id;
		setStoredModuleId(fromPath.id);
	}
}

watch(
	() => [route.path, route.query?.module],
	() => syncModuleFromRoute(),
	{ immediate: true },
);

onMounted(() => {
	requestAnimationFrame(() => {
		modalsReady.value = true;
	});
	try {
		if (onboarding?.setUp) setUp(createOnboardingSteps(router));
	} catch (e) {
		console.warn("onboarding setup failed", e);
	}
	syncModuleFromRoute();
	notifStore.reload();
});
</script>
