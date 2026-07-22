<template>
	<Dialog v-model="dialogOpen" :options="{ size: '5xl' }">
		<template #body>
			<div
				class="flex h-[min(720px,calc(100vh-8rem))] overflow-hidden rounded-xl bg-surface-gray-1"
			>
				<div
					class="flex w-52 shrink-0 flex-col overflow-y-auto border-r border-outline-gray-2 bg-surface-gray-1 p-2"
				>
					<template v-for="(tab, i) in tabs" :key="tab.label">
						<div
							class="mx-1 mb-1 text-[11px] font-medium uppercase tracking-wide text-ink-gray-4"
							:class="i > 0 ? 'mt-3' : 'mt-1'"
						>
							{{ tab.label }}
						</div>
						<button
							v-for="item in tab.items"
							:key="item.label"
							type="button"
							class="mb-0.5 flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm"
							:class="
								activeLabel === item.label
									? 'bg-surface-white text-ink-gray-9 shadow-sm'
									: 'text-ink-gray-7 hover:bg-surface-gray-2'
							"
							@click="setPage(item.label)"
						>
							<span class="grid size-4 place-items-center text-ink-gray-6">
								<component :is="item.icon" class="size-4" />
							</span>
							<span class="truncate">{{ item.label }}</span>
						</button>
					</template>
				</div>
				<div class="flex min-w-0 flex-1 flex-col bg-surface-white">
					<div
						class="flex shrink-0 items-center justify-between gap-3 border-b border-outline-gray-2 px-5 py-3"
					>
						<div>
							<div class="text-base font-semibold text-ink-gray-9">{{ activeLabel }}</div>
							<div class="text-xs text-ink-gray-5">User & system configuration</div>
						</div>
						<Button variant="ghost" @click="dialogOpen = false">
							<template #icon>
								<span class="lucide-x size-4 text-ink-gray-7" aria-hidden="true" />
							</template>
						</Button>
					</div>
					<div class="min-h-0 flex-1 overflow-y-auto">
						<component :is="activeComponent" v-if="activeComponent" :key="activeLabel" />
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { computed, markRaw, watch } from "vue";
import { Button, Dialog } from "frappe-ui";
import LucideUser from "~icons/lucide/user";
import LucideSlidersHorizontal from "~icons/lucide/sliders-horizontal";
import LucideSettings from "~icons/lucide/settings";
import LucideSparkles from "~icons/lucide/sparkles";
import { activeSettingsPage, showSettings } from "@/composables/settings";
import ProfileSettings from "./ProfileSettings.vue";
import PreferencesSettings from "./PreferencesSettings.vue";
import GeneralSettings from "./GeneralSettings.vue";
import BrandSettings from "./BrandSettings.vue";

const dialogOpen = computed({
	get: () => showSettings.value,
	set: (v) => {
		showSettings.value = v;
	},
});

const tabs = [
	{
		label: "User Configuration",
		items: [
			{ label: "Profile", icon: LucideUser, component: markRaw(ProfileSettings) },
			{
				label: "Preferences",
				icon: LucideSlidersHorizontal,
				component: markRaw(PreferencesSettings),
			},
		],
	},
	{
		label: "System Configuration",
		items: [
			{ label: "General", icon: LucideSettings, component: markRaw(GeneralSettings) },
			{ label: "Brand", icon: LucideSparkles, component: markRaw(BrandSettings) },
		],
	},
];

const allItems = computed(() => tabs.flatMap((t) => t.items));

const activeLabel = computed(() => {
	const found = allItems.value.find((i) => i.label === activeSettingsPage.value);
	return found?.label || "Profile";
});

const activeComponent = computed(() => {
	return allItems.value.find((i) => i.label === activeLabel.value)?.component;
});

function setPage(label) {
	activeSettingsPage.value = label;
}

watch(
	showSettings,
	(open) => {
		if (open && !activeSettingsPage.value) {
			activeSettingsPage.value = "Profile";
		}
	},
	{ immediate: true },
);
</script>
