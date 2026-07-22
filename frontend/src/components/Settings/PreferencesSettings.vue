<template>
	<div class="flex h-full min-h-[420px] flex-col">
		<div class="flex-1 space-y-0 overflow-y-auto px-6 py-6 text-ink-gray-8">
			<p class="mb-2 text-sm text-ink-gray-5">Personal display preferences for SwiftService.</p>

			<div class="flex max-w-xl items-center justify-between gap-8 border-b border-outline-gray-1 py-4">
				<div>
					<div class="text-sm font-medium text-ink-gray-8">Theme</div>
					<div class="text-sm text-ink-gray-5">Light, dark, or follow system.</div>
				</div>
				<TabButtons
					v-model="themeTab"
					:buttons="[
						{ label: 'Light', value: 'light' },
						{ label: 'Dark', value: 'dark' },
						{ label: 'System', value: 'system' },
					]"
				/>
			</div>

			<div class="flex max-w-xl items-center justify-between gap-8 border-b border-outline-gray-1 py-4">
				<div>
					<div class="text-sm font-medium text-ink-gray-8">Content width</div>
					<div class="text-sm text-ink-gray-5">
						Full width or boxed (centered), like Desk layout.
					</div>
				</div>
				<TabButtons
					v-model="widthTab"
					:buttons="[
						{ label: 'Full', value: 'full' },
						{ label: 'Box', value: 'box' },
					]"
				/>
			</div>

			<div class="flex max-w-xl items-center justify-between gap-8 border-b border-outline-gray-1 py-4">
				<div>
					<div class="text-sm font-medium text-ink-gray-8">Collapse sidebar by default</div>
					<div class="text-sm text-ink-gray-5">Start with a compact rail on next visit.</div>
				</div>
				<Switch v-model="collapsed" />
			</div>

			<div class="mt-4 rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4">
				<div class="mb-2 text-sm font-medium text-ink-gray-8">Preview</div>
				<div class="flex items-center gap-2">
					<img
						v-if="brand.logo"
						:src="brand.logo"
						class="size-8 rounded-md object-cover"
						alt=""
					/>
					<div>
						<div class="text-sm font-medium">{{ brand.name }}</div>
						<div class="text-xs text-ink-gray-5">{{ session.fullName || session.user }}</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useStorage } from "@vueuse/core";
import { Switch, TabButtons } from "frappe-ui";
import { sessionStore } from "@/stores/session";
import { useSettings } from "@/stores/settings";
import { useAppTheme } from "@/composables/theme";
import { contentWidth } from "@/composables/layout";

const session = sessionStore();
const { brand } = useSettings();
const { currentTheme, setTheme } = useAppTheme();
const collapsed = useStorage("ss_sidebar_collapsed", false);

const themeTab = computed({
	get: () => currentTheme.value || "system",
	set: (v) => setTheme(v),
});

const widthTab = computed({
	get: () => contentWidth.value || "full",
	set: (v) => {
		contentWidth.value = v === "box" ? "box" : "full";
	},
});
</script>
