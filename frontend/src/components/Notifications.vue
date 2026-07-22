<template>
	<div
		v-if="visible"
		ref="panelRef"
		data-ss-notif-panel
		class="fixed top-0 z-30 flex h-screen flex-col bg-surface-modal text-ink-gray-9"
		:style="{
			left: 'var(--ss-sidebar-width, 15rem)',
			maxWidth: '350px',
			minWidth: '350px',
			boxShadow: '8px 0 8px rgba(0,0,0,0.08)',
		}"
	>
		<div
			class="flex shrink-0 items-center justify-between border-b border-outline-gray-2 px-4 py-2.5"
		>
			<div class="text-base font-medium text-ink-gray-9">Notifications</div>
			<div class="flex gap-1">
				<Button
					v-if="store.items.length"
					variant="ghost"
					:tooltip="'Mark all as read'"
					icon="lucide-check-check"
					@click="store.markAllAsRead()"
				/>
				<Button variant="ghost" icon="lucide-x" @click="store.toggle(false)" />
			</div>
		</div>

		<div v-if="store.loading" class="p-5 text-sm text-ink-gray-5">Loading…</div>
		<div
			v-else-if="store.items.length"
			class="min-h-0 flex-1 divide-y divide-outline-gray-1 overflow-y-auto"
		>
			<button
				v-for="n in store.items"
				:key="n.name"
				type="button"
				class="flex w-full cursor-pointer items-start gap-3 px-4 py-3 text-left hover:bg-surface-gray-2"
				@click="openNotification(n)"
			>
				<Avatar size="md" :label="n.from_user || 'S'" />
				<div class="min-w-0 flex-1">
					<div class="text-sm leading-5 text-ink-gray-8">
						<span class="font-medium text-ink-gray-9">{{ n.from_user || "System" }}</span>
						<span v-if="n.subject"> — {{ n.subject }}</span>
					</div>
					<div v-if="n.message" class="mt-0.5 line-clamp-2 text-p-sm text-ink-gray-5">
						{{ n.message }}
					</div>
					<div class="mt-1.5 flex items-center gap-2 text-xs text-ink-gray-5">
						<span>{{ timeAgo(n.creation) }}</span>
						<span
							v-if="!n.read"
							class="size-1.5 rounded-full bg-surface-blue-5"
							aria-hidden="true"
						/>
					</div>
				</div>
			</button>
		</div>
		<div
			v-else
			class="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center"
		>
			<span class="lucide-bell size-8 text-ink-gray-3" aria-hidden="true" />
			<div class="text-sm font-medium text-ink-gray-8">You are all caught up</div>
			<div class="text-p-sm text-ink-gray-5">No new notifications</div>
		</div>
	</div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { Avatar, Button } from "frappe-ui";
import { onClickOutside } from "@vueuse/core";
import {
	notificationsStore,
	notificationsVisible,
} from "@/stores/notifications";
import { getResourceByDoctype } from "@/config/resources";
import { timeAgo } from "@/utils/format";

const store = notificationsStore();
const router = useRouter();
const panelRef = ref(null);
const visible = notificationsVisible;

onClickOutside(
	panelRef,
	() => {
		if (visible.value) store.toggle(false);
	},
	{ ignore: ["#notifications-btn", "[data-ss-notifications]"] },
);

function openNotification(n) {
	store.markAsRead(n.name);
	const res = n.document_type ? getResourceByDoctype(n.document_type) : null;
	if (res?.route && n.document_name) {
		router.push(`/${res.route}/${encodeURIComponent(n.document_name)}`);
	}
}

function syncSidebarWidth() {
	const aside = document.querySelector(".ss-shell > .border-r, .ss-shell > div.border-r");
	const el =
		aside ||
		document.querySelector(".ss-shell .bg-surface-menu-bar") ||
		document.querySelector(".ss-shell > div:first-child");
	if (el) {
		document.documentElement.style.setProperty(
			"--ss-sidebar-width",
			`${el.getBoundingClientRect().width}px`,
		);
	}
}

watch(visible, (v) => {
	if (v) {
		syncSidebarWidth();
		store.reload();
	}
});

onMounted(() => {
	store.reload();
	window.addEventListener("resize", syncSidebarWidth);
	syncSidebarWidth();
});

onBeforeUnmount(() => {
	window.removeEventListener("resize", syncSidebarWidth);
});
</script>
