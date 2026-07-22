<template>
	<div class="flex h-full flex-col overflow-hidden border-l border-outline-gray-2 bg-surface-white">
		<div
			class="flex h-[45px] cursor-copy items-center border-b border-outline-gray-2 px-5 py-2.5 text-lg font-medium text-ink-gray-9"
			:title="'Click to copy'"
			@click="copyId"
		>
			{{ docname }}
		</div>

		<div class="flex items-start gap-4 border-b border-outline-gray-2 p-5">
			<Avatar size="3xl" class="size-12 shrink-0" :label="titleLabel" />
			<div class="min-w-0 flex-1">
				<div class="flex items-center gap-1">
					<div class="min-w-0 flex-1 truncate text-xl font-medium text-ink-gray-9">
						{{ titleLabel }}
					</div>
					<Button
						v-if="canPrint"
						variant="ghost"
						class="shrink-0"
						icon="lucide-printer"
						:tooltip="'Print'"
						@click="$emit('print')"
					/>
				</div>
				<div class="mt-2 flex flex-wrap gap-1.5">
					<span
						v-if="status"
						class="inline-flex items-center gap-1.5 text-sm text-ink-gray-8"
					>
						<IndicatorIcon :class="parseStatusColor(status)" />
						{{ status }}
					</span>
					<span v-if="docstatusLabel" class="text-xs text-ink-gray-5">
						· {{ docstatusLabel }}
					</span>
				</div>
			</div>
		</div>

		<div class="min-h-0 flex-1 overflow-y-auto">
			<section v-if="summaryFields.length" class="border-b border-outline-gray-2 py-3">
				<div class="px-5 pb-2 text-sm font-medium text-ink-gray-9">Details</div>
				<div
					v-for="f in summaryFields"
					:key="f.fieldname"
					class="flex items-center gap-2 px-5 py-1.5"
				>
					<div class="w-[38%] shrink-0 truncate text-sm text-ink-gray-5">{{ f.label }}</div>
					<div class="min-w-0 flex-1 truncate text-sm text-ink-gray-8">
						{{ display(f) }}
					</div>
				</div>
			</section>

			<div class="p-4">
				<slot />
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { Avatar, Button, toast } from "frappe-ui";
import IndicatorIcon from "@/components/Icons/IndicatorIcon.vue";
import { parseStatusColor } from "@/utils/format";

const props = defineProps({
	doc: { type: Object, required: true },
	docname: { type: String, required: true },
	titleField: { type: String, default: "subject" },
	statusField: { type: String, default: "status" },
	fields: { type: Array, default: () => [] },
	docstatusLabel: { type: String, default: "" },
	/** Match Desk: allow print for submitted, or draft/cancelled per Print Settings (we allow always for saved docs). */
	canPrint: { type: Boolean, default: true },
});

defineEmits(["print"]);

const titleLabel = computed(() => {
	const t = props.doc?.[props.titleField] || props.doc?.customer || props.docname;
	return t || "—";
});

const status = computed(() => props.doc?.[props.statusField] || "");

const summaryFields = computed(() => {
	const skip = new Set([props.titleField, "naming_series", "amended_from"]);
	return (props.fields || [])
		.filter((f) => f.fieldtype !== "Text" && f.fieldtype !== "Long Text" && !skip.has(f.fieldname))
		.slice(0, 10);
});

function display(f) {
	const v = props.doc?.[f.fieldname];
	if (v == null || v === "") return "—";
	return String(v);
}

async function copyId() {
	try {
		await navigator.clipboard.writeText(props.docname);
		toast.success("Copied");
	} catch (e) {
		toast.error("Could not copy");
	}
}
</script>
