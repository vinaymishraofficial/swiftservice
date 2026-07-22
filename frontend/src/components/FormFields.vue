<template>
	<div class="space-y-8">
		<template v-if="groupedSections.length">
			<section v-for="section in groupedSections" :key="section.label" class="space-y-4">
				<div
					v-if="section.label"
					class="border-b border-outline-gray-2 pb-2 text-base font-medium text-ink-gray-9"
				>
					{{ section.label }}
				</div>
				<div class="grid grid-cols-1 gap-x-5 gap-y-5 sm:grid-cols-2 xl:grid-cols-3">
					<div
						v-for="field in section.fields"
						:key="field.fieldname"
						class="min-w-0"
						:class="colClass(field)"
					>
						<FieldControl
							:field="withLabel(field)"
							:model="model"
							:disabled="isFieldDisabled(field)"
							:size="size"
						/>
					</div>
				</div>
			</section>
		</template>
		<div v-else class="grid grid-cols-1 gap-x-5 gap-y-5 sm:grid-cols-2 xl:grid-cols-3">
			<div
				v-for="field in fields"
				:key="field.fieldname"
				class="min-w-0"
				:class="colClass(field)"
			>
				<FieldControl
					:field="withLabel(field)"
					:model="model"
					:disabled="isFieldDisabled(field)"
					:size="size"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import FieldControl from "@/components/FieldControl.vue";

const props = defineProps({
	fields: { type: Array, default: () => [] },
	model: { type: Object, required: true },
	disabled: { type: Boolean, default: false },
	/** When true, only fields with allow_on_submit stay editable */
	submitted: { type: Boolean, default: false },
	size: { type: String, default: "md" },
});

const WIDE = new Set(["Text", "Long Text", "Small Text", "Text Editor", "Table", "HTML Editor"]);

const groupedSections = computed(() => {
	const hasSection = props.fields.some((f) => f.section);
	if (!hasSection) return [];
	const map = [];
	const index = {};
	for (const f of props.fields) {
		const label = f.section || "Details";
		if (index[label] === undefined) {
			index[label] = map.length;
			map.push({ label, fields: [] });
		}
		map[index[label]].fields.push(f);
	}
	return map;
});

function humanize(name) {
	return String(name || "")
		.replace(/_/g, " ")
		.replace(/\b\w/g, (c) => c.toUpperCase());
}

function withLabel(field) {
	if (field.label) return field;
	return { ...field, label: humanize(field.fieldname) };
}

function colClass(field) {
	if (field.col) return field.col;
	if (WIDE.has(field.fieldtype)) return "sm:col-span-2 xl:col-span-3";
	return "";
}

function isFieldDisabled(field) {
	if (props.disabled || field.read_only) return true;
	if (props.submitted && !field.allow_on_submit) return true;
	return false;
}
</script>
