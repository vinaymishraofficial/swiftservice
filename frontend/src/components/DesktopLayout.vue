<template>
	<div class="ss-shell relative flex h-screen w-screen overflow-hidden bg-surface-gray-1">
		<Sidebar
			v-model:collapsed="isSidebarCollapsed"
			:sections="sidebarSections"
		>
			<template #header>
				<UserDropdown
					:isCollapsed="isSidebarCollapsed"
					:module-id="activeModuleId"
					@update:moduleId="onModuleSwitch"
				/>
			</template>
			<template #sidebar-item="{ item }">
				<SidebarItem
					:id="item.id"
					:data-ss-notifications="item.key === 'notifications' ? '' : undefined"
					:label="item.label"
					:icon="item.icon"
					:suffix="item.suffix"
					:to="item.to"
					:isActive="item.isActive"
					:onClick="item.onClick"
				/>
			</template>
			<template #footer-items="{ isCollapsed }">
				<div class="flex flex-col items-stretch gap-1">
					<GettingStartedBanner
						v-if="!isOnboardingStepsCompleted"
						:isSidebarCollapsed="isCollapsed"
						:appName="ONBOARDING_APP"
					/>
					<Button
						v-else
						variant="ghost"
						class="!w-full text-ink-gray-8 hover:text-ink-gray-9"
						:class="isCollapsed ? 'ss-rail-btn' : 'justify-start'"
						:label="isCollapsed ? undefined : 'Help'"
						@click="toggleHelp"
					>
						<template #prefix>
							<span class="lucide-circle-help size-4 text-ink-gray-8" />
						</template>
					</Button>
				</div>
			</template>
		</Sidebar>

		<Notifications />
		<GlobalSearch v-model="showCommandPalette" />

		<div class="flex min-w-0 flex-1 flex-col overflow-hidden bg-surface-white">
			<div
				class="flex min-h-0 flex-1 flex-col overflow-hidden"
				:class="contentWidth === 'box' ? 'mx-auto w-full max-w-6xl border-x border-outline-gray-1' : ''"
			>
				<slot />
			</div>
		</div>

		<SettingsModal v-if="modalsReady" />

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
import { computed, markRaw, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useStorage } from "@vueuse/core";
import { Button, Sidebar, SidebarItem } from "frappe-ui";
import {
	GettingStartedBanner,
	HelpModal,
	showHelpModal,
	minimize,
	useOnboarding,
} from "frappe-ui/frappe";
import SettingsModal from "@/components/Settings/SettingsModal.vue";
import UserDropdown from "@/components/UserDropdown.vue";
import SwiftServiceLogo from "@/components/SwiftServiceLogo.vue";
import Notifications from "@/components/Notifications.vue";
import GlobalSearch from "@/components/GlobalSearch.vue";
import { helpArticles } from "@/config/help";
import { ONBOARDING_APP, createOnboardingSteps } from "@/config/onboarding";
import {
	getModuleForPath,
	getModuleSidebar,
	getStoredModuleId,
	setStoredModuleId,
} from "@/config/modules";
import { contentWidth } from "@/composables/layout";
import { notificationsStore } from "@/stores/notifications";
import LucideSearch from "~icons/lucide/search";
import LucideBell from "~icons/lucide/bell";

const route = useRoute();
const router = useRouter();
const isSidebarCollapsed = useStorage("ss_sidebar_collapsed", false);
const articles = ref(helpArticles);
const docsLink = `${window.location.origin}/swiftservice/help`;
const modalsReady = ref(false);
const activeModuleId = ref(getStoredModuleId() || "home");
const showCommandPalette = ref(false);
const notifStore = notificationsStore();

const onboarding = useOnboarding(ONBOARDING_APP);
const isOnboardingStepsCompleted = onboarding?.isOnboardingStepsCompleted || ref(true);
const setUp = onboarding?.setUp || (() => {});

const isMac =
	typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform || "");

function toggleHelp() {
	showHelpModal.value = minimize.value ? true : !showHelpModal.value;
	minimize.value = !showHelpModal.value;
}

function isActive(to) {
	if (!to) return false;
	const [path, qs] = String(to).split("?");
	if (path === "/dashboard") {
		return route.path === "/dashboard" || route.path === "/";
	}
	if (path === "/reports") {
		if (route.path !== "/reports") return false;
		if (!qs) return !route.query.module;
		const params = new URLSearchParams(qs);
		const mod = params.get("module");
		const report = params.get("report");
		if (mod && route.query.module !== mod) return false;
		if (report && route.query.report && route.query.report !== report) return false;
		return true;
	}
	return route.path === path || route.path.startsWith(`${path}/`);
}

const toolItems = computed(() => [
	{
		key: "search",
		label: "Search",
		icon: markRaw(LucideSearch),
		suffix: isMac ? "⌘K" : "Ctrl K",
		onClick: () => {
			showCommandPalette.value = true;
		},
	},
	{
		key: "notifications",
		id: "notifications-btn",
		label: "Notifications",
		icon: markRaw(LucideBell),
		suffix: notifStore.unreadCount
			? notifStore.unreadCount > 9
				? "9+"
				: String(notifStore.unreadCount)
			: undefined,
		onClick: () => notifStore.toggle(),
	},
]);

const sidebarSections = computed(() => {
	const tools = {
		label: "",
		collapsible: false,
		items: toolItems.value,
	};
	const rest = getModuleSidebar(activeModuleId.value, isActive);
	return [tools, ...rest];
});

function syncModuleFromRoute() {
	const q = route.query?.module;
	const preferred = activeModuleId.value || getStoredModuleId();
	const fromPath = getModuleForPath(
		route.path,
		typeof q === "string" ? q : "",
		preferred,
	);
	if (fromPath?.id && fromPath.id !== activeModuleId.value) {
		activeModuleId.value = fromPath.id;
		setStoredModuleId(fromPath.id);
	}
}

function onModuleSwitch(id) {
	activeModuleId.value = id;
	setStoredModuleId(id);
}

watch(
	() => [route.path, route.query?.module],
	() => syncModuleFromRoute(),
	{ immediate: true },
);

watch(isSidebarCollapsed, () => {
	requestAnimationFrame(() => {
		const el = document.querySelector(".ss-shell .bg-surface-menu-bar");
		if (el) {
			document.documentElement.style.setProperty(
				"--ss-sidebar-width",
				`${el.getBoundingClientRect().width}px`,
			);
		}
	});
});

onMounted(() => {
	requestAnimationFrame(() => {
		modalsReady.value = true;
	});
	try {
		if (onboarding?.setUp) {
			setUp(createOnboardingSteps(router));
		}
	} catch (e) {
		console.warn("onboarding setup failed", e);
	}
	syncModuleFromRoute();
	notifStore.reload();
});
</script>
