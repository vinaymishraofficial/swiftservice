<template>
	<Dialog
		v-model="open"
		:options="{ title, size: '2xl' }"
		:disable-outside-click-to-close="true"
	>
		<template #body-content>
			<p class="mb-4 text-sm text-ink-gray-5">
				Fill required fields, or open the full form for all details.
			</p>
			<div class="ss-create-modal-fields max-h-[min(60vh,520px)] overflow-y-auto pr-0.5">
				<FormFields :fields="fields" :model="doc" size="md" />
			</div>
			<p v-if="error" class="mt-4 text-sm text-red-600">{{ error }}</p>
		</template>
		<template #actions="{ close }">
			<div class="flex w-full flex-wrap items-center justify-between gap-2">
				<Button
					variant="ghost"
					label="Edit in full page"
					@click="openFullPage"
				/>
				<div class="flex gap-2">
					<Button variant="outline" label="Cancel" @click="close" />
					<Button variant="solid" label="Create" :loading="saving" @click="create" />
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { reactive, ref, watch } from "vue";
import { Button, Dialog, call } from "frappe-ui";
import FormFields from "@/components/FormFields.vue";

const DRAFT_KEY_PREFIX = "ss_draft_";

const props = defineProps({
	title: { type: String, required: true },
	doctype: { type: String, required: true },
	fields: { type: Array, default: () => [] },
	createMethod: { type: String, default: "" },
	detailRoute: { type: String, default: "" },
	detailPath: { type: String, default: "" },
	listRoute: { type: String, default: "" },
});

const emit = defineEmits(["created", "full-view"]);
const open = defineModel({ type: Boolean });
const saving = ref(false);
const error = ref("");
const doc = reactive({});

function resetDoc() {
	Object.keys(doc).forEach((k) => delete doc[k]);
	props.fields.forEach((f) => {
		doc[f.fieldname] = f.default ?? (f.fieldtype === "Check" ? 0 : "");
	});
	error.value = "";
}

watch(
	open,
	(v) => {
		if (v) resetDoc();
	},
	{ immediate: true },
);

function openFullPage() {
	try {
		sessionStorage.setItem(DRAFT_KEY_PREFIX + props.doctype, JSON.stringify({ ...doc }));
	} catch {
		/* ignore */
	}
	open.value = false;
	emit("full-view", { ...doc });
}

async function create() {
	saving.value = true;
	error.value = "";
	try {
		for (const f of props.fields) {
			if (f.reqd && (doc[f.fieldname] === "" || doc[f.fieldname] == null)) {
				throw new Error(`${f.label} is required`);
			}
		}
		let result;
		if (props.createMethod) {
			result = await call(props.createMethod, { ...doc });
		} else {
			result = await call("swiftservice.api.save_doc", {
				doctype: props.doctype,
				doc: { doctype: props.doctype, ...doc },
			});
		}
		emit("created", result);
		open.value = false;
	} catch (e) {
		error.value = e?.messages?.[0] || e?.message || String(e);
	} finally {
		saving.value = false;
	}
}
</script>
