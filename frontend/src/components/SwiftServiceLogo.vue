<template>
	<img
		:src="src"
		alt="SwiftService"
		class="size-10 rounded-md object-cover"
	/>
</template>

<script setup>
import { computed } from "vue";
import { useSettings } from "@/stores/settings";

const { brand } = useSettings();
const src = computed(() => brand.logo || "/assets/swiftservice/logo-white.png");
</script>
