<template>
	<Dropdown :options="themeOptions">
		<Button variant="ghost" :tooltip="'Theme'" icon="lucide-sun-moon" />
	</Dropdown>
</template>

<script setup>
import { computed } from "vue";
import { Button, Dropdown } from "frappe-ui";
import { useAppTheme } from "@/composables/theme";

const { currentTheme, setTheme } = useAppTheme();

const themeOptions = computed(() => [
	{
		group: "Theme",
		hideLabel: true,
		items: [
			{
				label: "Light",
				icon: "lucide-sun",
				onClick: () => setTheme("light"),
				...(currentTheme.value === "light" ? { suffix: "✓" } : {}),
			},
			{
				label: "Dark",
				icon: "lucide-moon",
				onClick: () => setTheme("dark"),
				...(currentTheme.value === "dark" ? { suffix: "✓" } : {}),
			},
			{
				label: "System",
				icon: "lucide-monitor",
				onClick: () => setTheme("system"),
				...(currentTheme.value === "system" ? { suffix: "✓" } : {}),
			},
		],
	},
]);
</script>
