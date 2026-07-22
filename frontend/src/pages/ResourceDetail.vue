<template>
	<div v-if="crash" class="flex h-full flex-col items-center justify-center gap-3 p-8">
		<div class="text-sm text-ink-gray-7">Could not render this page.</div>
		<pre class="max-w-lg whitespace-pre-wrap break-words text-xs text-ink-gray-5">{{ crash }}</pre>
		<Button label="Back to list" @click="$router.back()" />
	</div>
	<DocFormPage v-else :resourceKey="resolvedKey" />
</template>

<script setup>
import { computed, onErrorCaptured, ref } from "vue";
import { useRoute } from "vue-router";
import { Button } from "frappe-ui";
import DocFormPage from "@/components/DocFormPage.vue";

const props = defineProps({
	resourceKey: { type: String, default: "" },
});

const route = useRoute();
const crash = ref("");
const resolvedKey = computed(
	() => props.resourceKey || route.meta.resourceKey || "",
);

onErrorCaptured((err) => {
	crash.value = err?.message || String(err);
	console.error("SwiftService detail page error:", err);
	return false;
});
</script>
