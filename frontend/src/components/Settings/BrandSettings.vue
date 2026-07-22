<template>
	<div class="flex h-full min-h-[420px] flex-col">
		<div class="flex-1 space-y-6 overflow-y-auto px-6 py-6 text-ink-gray-8">
			<p class="text-sm text-ink-gray-5">Configure your Brand Name, Logo, and Favicon.</p>

			<div class="flex max-w-3xl flex-col gap-6">
				<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
					<div>
						<div class="text-sm font-medium text-ink-gray-8">Brand Name</div>
						<div class="text-sm text-ink-gray-5">
							Set the name of your brand. Appears in the left sidebar.
						</div>
					</div>
					<FormControl
						class="sm:w-56"
						type="text"
						placeholder="Enter Brand Name"
						v-model="form.brand_name"
					/>
				</div>

				<div class="border-t border-outline-gray-1" />

				<div class="flex items-center gap-5">
					<div
						class="flex size-20 shrink-0 items-center justify-center rounded border border-outline-gray-2 bg-surface-gray-1"
					>
						<img
							v-if="form.brand_logo"
							:src="form.brand_logo"
							class="size-8 rounded object-cover"
							alt="Logo"
						/>
						<span v-else class="text-xs text-ink-gray-4">Logo</span>
					</div>
					<div class="min-w-0 flex-1">
						<div class="text-sm font-medium">Brand Logo</div>
						<div class="text-sm text-ink-gray-5">
							Appears in the left sidebar. Recommended size is 32×32 px in PNG or SVG.
						</div>
					</div>
					<ImageUploader
						:image-url="form.brand_logo"
						@upload="(url) => (form.brand_logo = url)"
						@remove="() => (form.brand_logo = '')"
					/>
				</div>

				<div class="flex items-center gap-5">
					<div
						class="flex size-20 shrink-0 items-center justify-center rounded border border-outline-gray-2 bg-surface-gray-1"
					>
						<img
							v-if="form.favicon"
							:src="form.favicon"
							class="size-8 rounded object-cover"
							alt="Favicon"
						/>
						<span v-else class="text-xs text-ink-gray-4">Icon</span>
					</div>
					<div class="min-w-0 flex-1">
						<div class="text-sm font-medium">Favicon</div>
						<div class="text-sm text-ink-gray-5">
							Appears next to the title in your browser tab. Recommended size is 32×32 px.
						</div>
					</div>
					<ImageUploader
						:image-url="form.favicon"
						@upload="(url) => (form.favicon = url)"
						@remove="() => (form.favicon = '')"
					/>
				</div>
			</div>
		</div>
		<div
			class="flex shrink-0 items-center justify-end border-t border-outline-gray-2 bg-surface-white px-6 py-3"
		>
			<Button variant="solid" label="Update" :loading="saving" @click="save" />
		</div>
	</div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { Button, FormControl, toast } from "frappe-ui";
import { useOnboarding } from "frappe-ui/frappe";
import ImageUploader from "./ImageUploader.vue";
import { useSettings } from "@/stores/settings";
import { ONBOARDING_APP } from "@/config/onboarding";

const { load, save: saveSettings } = useSettings();
const form = reactive({
	brand_name: "SwiftService",
	brand_logo: "",
	favicon: "",
});
const saving = ref(false);
const updateOnboardingStep = useOnboarding(ONBOARDING_APP)?.updateOnboardingStep;

async function init() {
	const data = await load(true);
	form.brand_name = data.brand_name || "SwiftService";
	form.brand_logo = data.brand_logo || "";
	form.favicon = data.favicon || "";
}

async function save() {
	saving.value = true;
	try {
		const current = await load();
		await saveSettings({ ...current, ...form });
		toast.success("Brand settings saved");
		updateOnboardingStep?.("configure_brand");
	} catch (e) {
		toast.error(e?.messages?.[0] || e?.message || "Save failed");
	} finally {
		saving.value = false;
	}
}

onMounted(init);
</script>
