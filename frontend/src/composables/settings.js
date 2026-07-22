import { ref } from "vue";

export const showSettings = ref(false);
export const activeSettingsPage = ref("");

export function openSettings(page = "Profile") {
	activeSettingsPage.value = page;
	showSettings.value = true;
}
