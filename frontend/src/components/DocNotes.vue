<template>
	<div class="flex flex-col gap-4">
		<div class="text-base font-medium text-ink-gray-9">Notes</div>
		<div class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
			<TextEditor
				:key="editorKey"
				:content="draft"
				:editable="!busy && !!name && name !== 'new'"
				:fixed-menu="editorButtons"
				:bubble-menu="false"
				:floating-menu="false"
				placeholder="Add an internal note…"
				editor-class="prose-sm min-h-[7rem] max-w-none px-3 py-2.5 text-sm text-ink-gray-9"
				@change="(html) => (draft = html)"
			/>
			<div class="flex justify-end border-t border-outline-gray-1 px-3 py-2">
				<Button
					variant="solid"
					label="Add note"
					size="sm"
					:loading="busy"
					:disabled="isEmpty || !name || name === 'new'"
					@click="submit"
				/>
			</div>
		</div>
		<div v-if="loading" class="text-sm text-ink-gray-5">Loading…</div>
		<ul v-else class="space-y-3">
			<li
				v-for="n in notes"
				:key="n.name"
				class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 px-4 py-3"
			>
				<div class="mb-1 flex items-baseline gap-2">
					<span class="text-sm font-medium text-ink-gray-9">{{ n.owner_name || n.owner }}</span>
					<span class="text-xs text-ink-gray-4">{{ timeAgo(n.creation) }}</span>
				</div>
				<div class="prose-sm max-w-none text-sm text-ink-gray-8" v-html="n.content" />
			</li>
			<li
				v-if="!notes.length"
				class="rounded-lg border border-dashed border-outline-gray-2 px-4 py-8 text-center text-sm text-ink-gray-5"
			>
				No notes yet.
			</li>
		</ul>
		<ErrorMessage :message="error" />
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { Button, ErrorMessage, TextEditor, call, toast } from "frappe-ui";
import { timeAgo } from "@/utils/format";
import { SAFE_TEXT_EDITOR_BUTTONS } from "@/utils/textEditor";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
});

const loading = ref(false);
const busy = ref(false);
const error = ref("");
const draft = ref("");
const editorKey = ref(0);
const notes = ref([]);

const editorButtons = SAFE_TEXT_EDITOR_BUTTONS;

const isEmpty = computed(() => {
	const t = (draft.value || "").replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").trim();
	return !t;
});

async function load() {
	if (!props.doctype || !props.name || props.name === "new") {
		notes.value = [];
		return;
	}
	loading.value = true;
	try {
		notes.value =
			(await call("swiftservice.api.get_comments", {
				doctype: props.doctype,
				name: props.name,
				comment_type: "Info",
			})) || [];
	} catch (e) {
		notes.value = [];
		error.value = e?.messages?.[0] || e?.message || "Could not load notes";
	} finally {
		loading.value = false;
	}
}

async function submit() {
	if (isEmpty.value) return;
	busy.value = true;
	error.value = "";
	try {
		const row = await call("swiftservice.api.add_comment", {
			doctype: props.doctype,
			name: props.name,
			content: draft.value,
			comment_type: "Info",
		});
		notes.value = [row, ...notes.value];
		draft.value = "";
		editorKey.value += 1;
		toast.success("Note added");
	} catch (e) {
		error.value = e?.messages?.[0] || e?.message || "Could not add note";
		toast.error(error.value);
	} finally {
		busy.value = false;
	}
}

watch(() => [props.doctype, props.name], () => load());
onMounted(load);
</script>
