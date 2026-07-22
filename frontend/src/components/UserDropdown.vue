<template>
	<div>
		<Dropdown :options="dropdownItems">
			<template #default="{ open }">
				<button
					type="button"
					class="flex items-center rounded-md duration-300 ease-in-out"
					:class="
						isCollapsed
							? 'mx-auto h-8 w-8 justify-center px-0'
							: open
								? 'h-12 w-full bg-surface-white px-2 py-2 shadow-sm'
								: 'h-12 w-full px-2 py-2 hover:bg-surface-gray-3'
					"
				>
					<div class="size-8 shrink-0 overflow-hidden rounded-md">
						<img
							v-if="brand.logo"
							:src="brand.logo"
							class="size-full object-cover"
							alt=""
						/>
						<SwiftLogo v-else />
					</div>
					<div
						class="flex flex-1 flex-col truncate text-left duration-300 ease-in-out"
						:class="
							isCollapsed
								? 'ml-0 w-0 overflow-hidden opacity-0'
								: 'ml-2 w-auto opacity-100'
						"
					>
						<div class="truncate text-base font-medium leading-none text-ink-gray-9">
							{{ brand.name || "SwiftService" }}
						</div>
						<div class="mt-1 truncate text-sm leading-none text-ink-gray-7">
							{{ moduleLabel }}
							<span class="text-ink-gray-4"> · </span>
							{{ session.fullName || session.user }}
						</div>
					</div>
					<div
						class="duration-300 ease-in-out"
						:class="
							isCollapsed
								? 'ml-0 w-0 overflow-hidden opacity-0'
								: 'ml-2 w-auto opacity-100'
						"
					>
						<span class="lucide-chevron-down size-4 text-ink-gray-5" aria-hidden="true" />
					</div>
				</button>
			</template>
		</Dropdown>

		<Dialog v-model="showAbout" :options="{ title: 'About SwiftService', size: 'sm' }">
			<template #body-content>
				<div class="space-y-3 text-p-sm text-ink-gray-7">
					<div class="flex items-center gap-3">
						<div class="size-10 overflow-hidden rounded-md">
							<img
								v-if="brand.logo"
								:src="brand.logo"
								class="size-full object-cover"
								alt=""
							/>
							<SwiftLogo v-else />
						</div>
						<div>
							<div class="text-base font-medium text-ink-gray-9">
								{{ brand.name || "SwiftService" }}
							</div>
							<div class="text-xs text-ink-gray-5">After-sales field service</div>
						</div>
					</div>
					<p>
						Install Base → Complaint → Visit → Resolve → Close, plus AMC/PM — built with
						frappe-ui.
					</p>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { computed, h, markRaw, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { call, Dialog, Dropdown } from "frappe-ui";
import LucideLayoutGrid from "~icons/lucide/layout-grid";
import LucideSettings from "~icons/lucide/settings";
import LucideInfo from "~icons/lucide/info";
import LucideLogOut from "~icons/lucide/log-out";
import LucideSun from "~icons/lucide/sun";
import LucideMoon from "~icons/lucide/moon";
import LucideMonitor from "~icons/lucide/monitor";
import LucideSunMoon from "~icons/lucide/sun-moon";
import LucideBoxes from "~icons/lucide/boxes";
import SwiftLogo from "@/components/Icons/SwiftLogo.vue";
import { sessionStore } from "@/stores/session";
import { useSettings } from "@/stores/settings";
import { openSettings } from "@/composables/settings";
import { useAppTheme } from "@/composables/theme";
import { getModuleById, modules, setStoredModuleId } from "@/config/modules";

const props = defineProps({
	isCollapsed: { type: Boolean, default: false },
	moduleId: { type: String, default: "home" },
});

const emit = defineEmits(["update:moduleId"]);
const router = useRouter();

const session = sessionStore();
const { brand, load: loadBrand } = useSettings();
const { currentTheme, setTheme } = useAppTheme();
const apps = ref([]);
const showAbout = ref(false);

const moduleLabel = computed(() => getModuleById(props.moduleId)?.label || "Home");

const moduleMenuItems = computed(() =>
	modules
		.filter((m) => m.showInGrid !== false)
		.map((m) => ({
			label: m.label,
			icon: m.icon,
			onClick: () => selectModule(m),
			...(m.id === props.moduleId ? { suffix: "✓" } : {}),
		})),
);

function selectModule(m) {
	setStoredModuleId(m.id);
	emit("update:moduleId", m.id);
	if (m.homeRoute) {
		router.push(m.homeRoute);
	}
}

const appMenuItems = computed(() =>
	(apps.value || []).map((app) => ({
		label: app.title,
		onClick: () => {
			window.location.href = app.route;
		},
		slots: {
			prefix: () =>
				h("img", {
					class: "size-5 rounded",
					src: app.logo || "/assets/frappe/images/framework.png",
				}),
		},
	})),
);

const themeMenuItems = computed(() =>
	[
		{ label: "Light", value: "light", icon: markRaw(LucideSun) },
		{ label: "Dark", value: "dark", icon: markRaw(LucideMoon) },
		{ label: "System", value: "system", icon: markRaw(LucideMonitor) },
	].map((t) => ({
		label: t.label,
		icon: t.icon,
		onClick: () => setTheme(t.value),
		...(currentTheme.value === t.value ? { suffix: "✓" } : {}),
	})),
);

const dropdownItems = computed(() => [
	{
		group: "Menu",
		hideLabel: true,
		items: [
			{
				label: "Modules",
				icon: markRaw(LucideBoxes),
				submenu: moduleMenuItems.value,
			},
			{
				label: "Apps",
				icon: markRaw(LucideLayoutGrid),
				submenu: appMenuItems.value,
			},
			{
				label: "Theme",
				icon: markRaw(LucideSunMoon),
				submenu: themeMenuItems.value,
			},
			{
				label: "Settings",
				icon: markRaw(LucideSettings),
				onClick: () => openSettings("Profile"),
			},
			{
				label: "About",
				icon: markRaw(LucideInfo),
				onClick: () => {
					showAbout.value = true;
				},
			},
		],
	},
	{
		group: "Session",
		hideLabel: true,
		items: [
			{
				label: "Log out",
				icon: markRaw(LucideLogOut),
				onClick: () => session.logout(),
			},
		],
	},
]);

onMounted(async () => {
	loadBrand();
	try {
		apps.value = await call("swiftservice.api.get_apps");
	} catch (e) {
		apps.value = [
			{
				title: "Desk",
				route: "/app",
				logo: "/assets/frappe/images/framework.png",
			},
		];
	}
});
</script>
