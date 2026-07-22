<template>
	<div class="flex flex-col gap-4">
		<div v-if="loading" class="text-sm text-ink-gray-5">Loading activity…</div>
		<div
			v-else-if="!items.length"
			class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 px-4 py-8 text-center text-sm text-ink-gray-5"
		>
			No activity yet for this document.
		</div>
		<ul
			v-else
			class="space-y-0 divide-y divide-outline-gray-1 rounded-lg border border-outline-gray-2 bg-surface-white"
		>
			<li
				v-for="item in items"
				:key="`${item.type}-${item.name}`"
				class="flex gap-3 px-4 py-3"
			>
				<div
					class="flex size-8 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
				>
					<span
						v-if="item.type === 'email'"
						class="lucide-mail size-3.5"
						aria-hidden="true"
					/>
					<span
						v-else-if="item.type === 'notification'"
						class="lucide-bell size-3.5"
						aria-hidden="true"
					/>
					<Avatar
						v-else
						shape="circle"
						size="sm"
						:image="item.image"
						:label="item.owner_name || item.owner || '?'"
					/>
				</div>
				<div class="min-w-0 flex-1">
					<div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
						<span class="text-sm font-medium text-ink-gray-9">
							{{ item.owner_name || item.owner || "System" }}
						</span>
						<span class="text-xs text-ink-gray-5">{{ subtypeLabel(item) }}</span>
						<span class="ml-auto text-xs text-ink-gray-4">{{ timeAgo(item.creation) }}</span>
					</div>

					<div
						v-if="item.type === 'email'"
						class="mt-1 rounded-md border border-outline-gray-1 bg-surface-gray-1 px-3 py-2"
					>
						<div class="truncate text-sm font-medium text-ink-gray-8">
							{{ item.subject || "(no subject)" }}
						</div>
						<div v-if="item.recipients" class="mt-0.5 text-xs text-ink-gray-5">
							To: {{ item.recipients }}
						</div>
						<div
							v-if="item.content"
							class="prose-sm mt-2 max-h-40 max-w-none overflow-y-auto text-sm text-ink-gray-7"
							v-html="item.content"
						/>
						<div
							v-if="item.delivery_status"
							class="mt-1 text-xs text-ink-gray-4"
						>
							{{ item.delivery_status }}
						</div>
					</div>

					<div
						v-else-if="item.type === 'notification'"
						class="mt-1 text-sm text-ink-gray-7"
						v-html="item.content"
					/>

					<div
						v-else-if="item.type === 'comment' && item.content"
						class="prose-sm mt-1 max-w-none text-sm text-ink-gray-8"
						v-html="item.content"
					/>
					<div
						v-else-if="item.type === 'event' && item.content"
						class="mt-1 text-sm text-ink-gray-7"
						v-html="item.content"
					/>
					<ul
						v-else-if="item.type === 'version' && item.changed?.length"
						class="mt-1 space-y-0.5 text-xs text-ink-gray-6"
					>
						<li v-for="(ch, i) in item.changed" :key="i">
							<span class="font-medium text-ink-gray-7">{{ ch.field }}</span>:
							<span class="line-through opacity-60">{{ fmt(ch.old) }}</span>
							→
							<span>{{ fmt(ch.new) }}</span>
						</li>
					</ul>
					<div v-else-if="item.type === 'version'" class="mt-1 text-xs text-ink-gray-5">
						Updated document
					</div>
				</div>
			</li>
		</ul>
	</div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import { Avatar, call } from "frappe-ui";
import { timeAgo } from "@/utils/format";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
});

const loading = ref(false);
const items = ref([]);

function subtypeLabel(item) {
	if (item.type === "version") return "edited";
	if (item.type === "email") return "sent an email";
	if (item.type === "notification") return "notification";
	if (item.subtype === "Comment") return "commented";
	return (item.subtype || "activity").toLowerCase();
}

function fmt(v) {
	if (v == null || v === "") return "—";
	return String(v);
}

async function load() {
	if (!props.doctype || !props.name || props.name === "new") {
		items.value = [];
		return;
	}
	loading.value = true;
	try {
		items.value =
			(await call("swiftservice.api.get_activity", {
				doctype: props.doctype,
				name: props.name,
			})) || [];
	} catch (e) {
		items.value = [];
	} finally {
		loading.value = false;
	}
}

watch(
	() => [props.doctype, props.name],
	() => load(),
);
onMounted(load);

defineExpose({ reload: load });
</script>
