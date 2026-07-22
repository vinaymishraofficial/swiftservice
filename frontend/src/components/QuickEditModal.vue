<template>
	<Dialog v-model="open" :options="{ size: '3xl' }">
		<template #body>
			<div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
				<div class="mb-5 flex items-center justify-between">
					<div>
						<h3 class="text-2xl font-semibold text-ink-gray-9">{{ title }}</h3>
						<p class="mt-1 text-sm text-ink-gray-5">Quick edit — key fields</p>
					</div>
					<Button variant="ghost" icon="x" @click="open = false" />
				</div>
				<FormFields :fields="fields" :model="local" />
				<p v-if="error" class="mt-4 text-sm text-red-600">{{ error }}</p>
			</div>
			<div class="flex justify-end gap-2 px-4 pb-7 pt-4 sm:px-6">
				<Button variant="outline" label="Cancel" @click="open = false" />
				<Button variant="solid" label="Save" :loading="saving" @click="save" />
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { reactive, ref, watch } from "vue";
import { Button, Dialog, call } from "frappe-ui";
import FormFields from "@/components/FormFields.vue";

const props = defineProps({
	title: { type: String, required: true },
	doctype: { type: String, required: true },
	fields: { type: Array, default: () => [] },
	doc: { type: Object, required: true },
});

const emit = defineEmits(["saved"]);
const open = defineModel({ type: Boolean });
const saving = ref(false);
const error = ref("");
const local = reactive({});

watch(
	open,
	(v) => {
		if (v) {
			Object.keys(local).forEach((k) => delete local[k]);
			Object.assign(local, props.doc || {});
			error.value = "";
		}
	},
	{ immediate: true },
);

async function save() {
	saving.value = true;
	error.value = "";
	try {
		const result = await call("swiftservice.api.save_doc", {
			doctype: props.doctype,
			doc: { ...local, doctype: props.doctype, name: props.doc.name },
		});
		emit("saved", result);
		open.value = false;
	} catch (e) {
		error.value = e?.messages?.[0] || e?.message || String(e);
	} finally {
		saving.value = false;
	}
}
</script>
