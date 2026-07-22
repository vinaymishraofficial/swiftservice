<template>
	<div class="flex h-full flex-col overflow-hidden">
		<LayoutHeader>
			<template #left-header>
				<div>
					<div class="text-lg font-medium text-ink-gray-9">Help</div>
					<div class="text-p-sm text-ink-gray-5">{{ article.title }}</div>
				</div>
			</template>
			<template #right-header>
				<Button
					variant="outline"
					label="Dashboard"
					@click="$router.push('/dashboard')"
				/>
			</template>
		</LayoutHeader>

		<div class="flex-1 overflow-auto px-5 py-6 sm:px-8">
			<div class="mx-auto max-w-2xl">
				<h1 class="text-xl font-semibold text-ink-gray-9">{{ article.title }}</h1>
				<div class="mt-5 space-y-3">
					<p
						v-for="(para, i) in article.body"
						:key="i"
						class="text-base leading-relaxed text-ink-gray-7"
					>
						{{ para }}
					</p>
				</div>
				<div class="mt-8 flex flex-wrap gap-2">
					<Button
						class="ss-accent-btn"
					variant="solid"
					label="Open Getting started"
					@click="openGettingStarted"
				/>
					<Button variant="outline" label="Back to dashboard" @click="$router.push('/dashboard')" />
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { Button } from "frappe-ui";
import { showHelpModal, minimize, showHelpCenter } from "frappe-ui/frappe";
import LayoutHeader from "@/components/LayoutHeader.vue";
import { helpContent } from "@/config/help";

const route = useRoute();

const article = computed(() => {
	const slug = route.params.article || "introduction";
	return (
		helpContent[slug] || {
			title: "Help",
			body: ["Article not found. Open Help centre from the right panel for the full index."],
		}
	);
});

function openGettingStarted() {
	showHelpCenter.value = false;
	minimize.value = false;
	showHelpModal.value = true;
}
</script>
