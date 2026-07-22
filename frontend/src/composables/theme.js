import { ref } from "vue";

/** Shared theme state — frappe-ui useTheme() creates a new ref per call. */
export const currentTheme = ref(
	typeof localStorage !== "undefined" ? localStorage.getItem("theme") || "system" : "system",
);

function getSystemTheme() {
	return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(theme) {
	const next = ["light", "dark", "system"].includes(theme) ? theme : "system";
	currentTheme.value = next;
	const resolved = next === "system" ? getSystemTheme() : next;
	document.documentElement.setAttribute("data-theme", resolved);
	localStorage.setItem("theme", next);
}

export function toggleTheme() {
	applyTheme(currentTheme.value === "dark" ? "light" : "dark");
}

export function initializeTheme() {
	applyTheme(currentTheme.value || "system");
	const mq = window.matchMedia("(prefers-color-scheme: dark)");
	const onChange = () => {
		if (currentTheme.value === "system") {
			document.documentElement.setAttribute("data-theme", getSystemTheme());
		}
	};
	mq.addEventListener("change", onChange);
}

export function useAppTheme() {
	return {
		currentTheme,
		setTheme: applyTheme,
		toggleTheme,
		initializeTheme,
	};
}
