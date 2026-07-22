<template>
	<div class="relative">
		<button
			type="button"
			class="flex h-12 w-full items-center rounded-md px-2 hover:bg-surface-gray-2"
			:class="[
				isCollapsed ? 'justify-center' : '',
				open ? 'bg-surface-white shadow-sm' : '',
			]"
			@click.stop="open = !open"
		>
			<img :src="brand.logo" class="h-8 w-8 shrink-0 rounded-md object-cover" alt="" />
			<div v-if="!isCollapsed" class="ml-2 min-w-0 flex-1 text-left">
				<div class="truncate text-sm font-medium text-ink-gray-9">{{ brand.name }}</div>
				<div class="truncate text-xs text-ink-gray-5">
					{{ session.fullName || session.user }}
				</div>
			</div>
			<span v-if="!isCollapsed" class="ml-1 text-ink-gray-5">{{ open ? "▴" : "▾" }}</span>
		</button>

		<div
			v-if="open"
			class="absolute left-0 right-0 top-full z-[60] mt-1 rounded-md border border-outline-gray-2 bg-surface-white p-1 shadow-lg"
			@click.stop
		>
			<button
				type="button"
				class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-surface-gray-2"
				@click="openUserSettings"
			>
				<span class="text-ink-gray-6">⚙</span>
				<span>Settings</span>
			</button>
			<div class="my-1 border-t border-outline-gray-1" />
			<div class="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-ink-gray-4">
				Switch App
			</div>
			<button
				v-for="app in apps"
				:key="app.title"
				type="button"
				class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-surface-gray-2"
				@click="goApp(app.route)"
			>
				<img
					:src="app.logo || '/assets/frappe/images/framework.png'"
					class="size-5 rounded"
					alt=""
				/>
				<span class="truncate">{{ app.title }}</span>
			</button>
			<div class="my-1 border-t border-outline-gray-1" />
			<button
				type="button"
				class="flex w-full items-center rounded px-2 py-1.5 text-left text-sm text-red-600 hover:bg-surface-gray-2"
				@click="session.logout()"
			>
				Logout
			</button>
		</div>
	</div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import { call } from "frappe-ui";
import { sessionStore } from "@/stores/session";
import { useSettings } from "@/stores/settings";
import { openSettings } from "@/composables/settings";

defineProps({
	isCollapsed: { type: Boolean, default: false },
});

const session = sessionStore();
const { brand, load: loadSettings } = useSettings();
const apps = ref([]);
const open = ref(false);

function goApp(route) {
	window.location.href = route;
}

function openUserSettings() {
	open.value = false;
	openSettings("Profile");
}

onMounted(async () => {
	loadSettings();
	try {
		apps.value = await call("swiftservice.api.get_apps");
	} catch (e) {
		apps.value = [{ title: "Desk", route: "/app", logo: "/assets/frappe/images/framework.png" }];
	}
	const close = () => {
		open.value = false;
	};
	document.addEventListener("click", close);
	onUnmounted(() => document.removeEventListener("click", close));
});
</script>
