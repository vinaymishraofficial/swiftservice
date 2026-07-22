<template>
	<div class="flex flex-col gap-4">
		<div class="flex items-center justify-between gap-3">
			<div class="text-base font-medium text-ink-gray-9">Attachments</div>
			<div>
				<input ref="fileInput" type="file" class="hidden" @change="onFile" />
				<Button
					variant="solid"
					label="Upload"
					size="sm"
					:loading="busy"
					:disabled="!props.name"
					@click="pickFile"
				/>
			</div>
		</div>
		<div v-if="loading" class="text-sm text-ink-gray-5">Loading…</div>
		<div
			v-else-if="!files.length"
			class="rounded-lg border border-dashed border-outline-gray-2 px-4 py-10 text-center text-sm text-ink-gray-5"
		>
			No attachments yet. Upload files related to this document.
		</div>
		<ul v-else class="divide-y divide-outline-gray-1 rounded-lg border border-outline-gray-2">
			<li
				v-for="f in files"
				:key="f.name"
				class="flex items-center justify-between gap-3 px-4 py-3"
			>
				<div class="min-w-0 flex-1">
					<a
						:href="f.file_url"
						target="_blank"
						rel="noopener"
						class="block truncate text-sm font-medium text-ink-gray-9 hover:underline"
					>
						{{ f.file_name || f.name }}
					</a>
					<div class="text-xs text-ink-gray-5">{{ f.creation }}</div>
				</div>
				<Button
					variant="ghost"
					size="sm"
					label="Remove"
					class="shrink-0 text-ink-red-3"
					:loading="removing === f.name"
					:disabled="busy"
					@click="removeFile(f)"
				/>
			</li>
		</ul>
		<ErrorMessage :message="error" />
	</div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import { Button, ErrorMessage, call, confirmDialog, toast } from "frappe-ui";
import { uploadDocFile } from "@/utils/upload";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
});

const loading = ref(false);
const busy = ref(false);
const removing = ref("");
const error = ref("");
const files = ref([]);
const fileInput = ref(null);

async function load() {
	if (!props.doctype || !props.name) {
		files.value = [];
		return;
	}
	loading.value = true;
	error.value = "";
	try {
		files.value =
			(await call("swiftservice.api.get_attachments", {
				doctype: props.doctype,
				name: props.name,
			})) || [];
	} catch (e) {
		files.value = [];
		error.value = e?.messages?.[0] || e?.message || "Could not load attachments";
	} finally {
		loading.value = false;
	}
}

function pickFile() {
	fileInput.value?.click();
}

async function onFile(e) {
	const file = e.target.files?.[0];
	e.target.value = "";
	if (!file) return;
	busy.value = true;
	error.value = "";
	try {
		await uploadDocFile(file, {
			doctype: props.doctype,
			docname: props.name,
			isPrivate: false,
		});
		toast.success("Uploaded");
		await load();
	} catch (err) {
		error.value = err?.message || "Upload failed";
		toast.error(error.value);
		console.error("Attachment upload failed:", err);
	} finally {
		busy.value = false;
	}
}

function removeFile(f) {
	confirmDialog({
		title: "Remove attachment?",
		message: `Remove “${f.file_name || f.name}” from this document?`,
		onConfirm: async ({ hideDialog }) => {
			removing.value = f.name;
			error.value = "";
			try {
				await call("swiftservice.api.delete_attachment", {
					doctype: props.doctype,
					name: props.name,
					file_name: f.name,
				});
				files.value = files.value.filter((x) => x.name !== f.name);
				toast.success("Removed");
				hideDialog();
			} catch (e) {
				error.value = e?.messages?.[0] || e?.message || "Could not remove";
				toast.error(error.value);
			} finally {
				removing.value = "";
			}
		},
	});
}

watch(() => [props.doctype, props.name], () => load());
onMounted(load);
</script>
