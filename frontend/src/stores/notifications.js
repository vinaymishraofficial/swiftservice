import { defineStore } from "pinia";
import { call } from "frappe-ui";
import { computed, ref } from "vue";

export const notificationsVisible = ref(false);

export const notificationsStore = defineStore("ss-notifications", () => {
	const items = ref([]);
	const unread = ref(0);
	const loading = ref(false);

	const unreadCount = computed(() => unread.value || 0);

	async function reload() {
		loading.value = true;
		try {
			const data = await call("swiftservice.api.get_notifications", { limit: 40 });
			items.value = data?.notifications || [];
			unread.value = data?.unread || 0;
		} catch (e) {
			console.warn("notifications load failed", e);
			items.value = [];
			unread.value = 0;
		} finally {
			loading.value = false;
		}
	}

	function toggle(force) {
		if (typeof force === "boolean") {
			notificationsVisible.value = force;
		} else {
			notificationsVisible.value = !notificationsVisible.value;
		}
		if (notificationsVisible.value) reload();
	}

	async function markAsRead(name) {
		try {
			const data = await call("swiftservice.api.mark_notification_read", { name });
			items.value = data?.notifications || items.value;
			unread.value = data?.unread ?? unread.value;
		} catch (e) {
			console.warn(e);
		}
		notificationsVisible.value = false;
	}

	async function markAllAsRead() {
		try {
			const data = await call("swiftservice.api.mark_all_notifications_read");
			items.value = data?.notifications || [];
			unread.value = data?.unread || 0;
		} catch (e) {
			console.warn(e);
		}
	}

	return {
		items,
		unread,
		unreadCount,
		loading,
		reload,
		toggle,
		markAsRead,
		markAllAsRead,
	};
});
