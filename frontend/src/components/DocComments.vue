<template>
	<div class="flex flex-col gap-4">
		<div class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
			<TextEditor
				:key="editorKey"
				:content="draft"
				:editable="!busy"
				:fixed-menu="editorButtons"
				:bubble-menu="false"
				:floating-menu="false"
				placeholder="Write a comment…"
				editor-class="prose-sm min-h-[5.5rem] max-w-none px-3 py-2.5 text-sm text-ink-gray-9"
				@change="(html) => (draft = html)"
			/>
			<div
				class="flex flex-wrap items-center justify-between gap-2 border-t border-outline-gray-1 px-3 py-2"
			>
				<span class="text-xs text-ink-gray-4">Use bold / lists from the toolbar</span>
				<div class="flex gap-2">
					<Button
						v-if="!isEmpty"
						variant="ghost"
						label="Discard"
						size="sm"
						:disabled="busy"
						@click="discard"
					/>
					<Button
						variant="solid"
						label="Comment"
						size="sm"
						:loading="busy"
						:disabled="isEmpty"
						@click="submit"
					/>
				</div>
			</div>
			<ErrorMessage class="px-3 pb-2" :message="error" />
		</div>

		<div v-if="loading" class="text-sm text-ink-gray-5">Loading comments…</div>
		<div
			v-else-if="loadError"
			class="rounded-lg border border-outline-red-1 bg-surface-red-1 px-4 py-3 text-sm text-ink-red-3"
		>
			{{ loadError }}
		</div>
		<div
			v-else-if="!comments.length"
			class="rounded-lg border border-dashed border-outline-gray-2 px-4 py-8 text-center text-sm text-ink-gray-5"
		>
			No comments yet. Be the first to leave a note.
		</div>
		<ul v-else class="space-y-3">
			<li
				v-for="c in comments"
				:key="c.name"
				class="flex gap-3 rounded-lg border border-outline-gray-2 bg-surface-gray-1 px-3 py-3"
			>
				<Avatar
					shape="circle"
					size="md"
					:image="c.image"
					:label="c.owner_name || c.owner || '?'"
				/>
				<div class="min-w-0 flex-1">
					<div class="flex items-baseline gap-2">
						<span class="text-sm font-medium text-ink-gray-9">
							{{ c.owner_name || c.owner }}
						</span>
						<span class="text-xs text-ink-gray-4">{{ timeAgo(c.creation) }}</span>
					</div>
					<div
						class="prose-sm mt-1 max-w-none text-sm text-ink-gray-8 [&_.mention]:rounded [&_.mention]:bg-surface-gray-3 [&_.mention]:px-1 [&_.mention]:font-semibold"
						v-html="c.content"
					/>
				</div>
			</li>
		</ul>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { Avatar, Button, ErrorMessage, TextEditor, call, toast } from "frappe-ui";
import { timeAgo } from "@/utils/format";
import { SAFE_TEXT_EDITOR_BUTTONS } from "@/utils/textEditor";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
});

const emit = defineEmits(["updated"]);

const loading = ref(false);
const busy = ref(false);
const error = ref("");
const loadError = ref("");
const draft = ref("");
const editorKey = ref(0);
const comments = ref([]);

const editorButtons = SAFE_TEXT_EDITOR_BUTTONS;

const isEmpty = computed(() => {
	const t = (draft.value || "").replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").trim();
	return !t;
});

async function load() {
	if (!props.doctype || !props.name || props.name === "new") {
		comments.value = [];
		return;
	}
	loading.value = true;
	loadError.value = "";
	try {
		comments.value =
			(await call("swiftservice.api.get_comments", {
				doctype: props.doctype,
				name: props.name,
			})) || [];
	} catch (e) {
		comments.value = [];
		loadError.value = e?.messages?.[0] || e?.message || "Could not load comments";
	} finally {
		loading.value = false;
	}
}

function discard() {
	draft.value = "";
	editorKey.value += 1;
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
		});
		comments.value = [row, ...comments.value];
		discard();
		emit("updated");
		toast.success("Comment added");
	} catch (e) {
		error.value = e?.messages?.[0] || e?.message || "Could not add comment";
		toast.error(error.value);
	} finally {
		busy.value = false;
	}
}

watch(
	() => [props.doctype, props.name],
	() => load(),
);
onMounted(load);

defineExpose({ reload: load });
</script>
