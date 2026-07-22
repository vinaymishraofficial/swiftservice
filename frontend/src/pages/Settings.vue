<template>
	<div class="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
		<p class="text-sm text-ink-gray-6">Opening settings…</p>
	</div>
</template>

<script setup>
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { openSettings } from "@/composables/settings";

const router = useRouter();

onMounted(() => {
	openSettings("General");
	router.replace("/dashboard");
});
</script>
