<template>
	<div class="w-full space-y-1.5">
		<LinkField
			v-if="field.fieldtype === 'Link'"
			v-model="model[field.fieldname]"
			:doctype="field.options"
			:label="displayLabel"
			:filters="resolveFilters(field)"
			:reqd="!!field.reqd"
			:disabled="isDisabled"
			:size="size"
			:placeholder="field.placeholder || displayLabel"
		/>
		<div v-else-if="field.fieldtype === 'Select'" class="w-full space-y-1.5">
			<label class="block text-sm text-ink-gray-5">
				{{ displayLabel }}
				<span v-if="field.reqd" class="text-ink-red-3">*</span>
			</label>
			<select
				class="form-input w-full rounded-md border-0 bg-surface-gray-2 text-ink-gray-8 focus:bg-surface-white focus:ring-1 focus:ring-outline-gray-3 disabled:opacity-60"
				:class="size === 'md' ? 'py-2 pl-3 pr-8 text-base' : 'h-7 py-0 pl-2 pr-7 text-base'"
				:disabled="isDisabled"
				:value="model[field.fieldname] ?? ''"
				@change="onSelectChange($event)"
			>
				<option v-if="!field.reqd" value="">
					{{ field.placeholder || displayLabel || "—" }}
				</option>
				<option
					v-for="opt in normalizeOptions(field)"
					:key="String(opt.value)"
					:value="opt.value"
				>
					{{ opt.label }}
				</option>
			</select>
		</div>
		<FormControl
			v-else-if="isPlainText"
			type="textarea"
			:size="size"
			:label="displayLabel"
			:required="!!field.reqd"
			:rows="field.fieldtype === 'Long Text' ? 5 : 3"
			v-model="model[field.fieldname]"
			:placeholder="field.placeholder || displayLabel"
			:disabled="isDisabled"
		/>
		<div v-else-if="isRichText" class="w-full space-y-1.5">
			<label class="block text-sm text-ink-gray-5">
				{{ displayLabel }}
				<span v-if="field.reqd" class="text-ink-red-3">*</span>
			</label>
			<TextEditor
				:key="`${field.fieldname}-${isDisabled}`"
				:content="model[field.fieldname] || ''"
				:editable="!isDisabled"
				:placeholder="field.placeholder || `Write ${displayLabel.toLowerCase()}…`"
				:fixed-menu="isDisabled ? false : SAFE_TEXT_EDITOR_BUTTONS"
				:bubble-menu="false"
				:floating-menu="false"
				editor-class="prose-sm min-h-[140px] max-w-none rounded-b-lg border border-outline-gray-2 border-t-0 bg-surface-white px-3 py-2.5 text-base text-ink-gray-9"
				@change="(html) => (model[field.fieldname] = html)"
			/>
		</div>
		<FormControl
			v-else-if="field.fieldtype === 'Check'"
			type="checkbox"
			:size="size"
			:label="displayLabel"
			v-model="model[field.fieldname]"
			:disabled="isDisabled"
		/>
		<FormControl
			v-else-if="field.fieldtype === 'Float' || field.fieldtype === 'Int' || field.fieldtype === 'Currency'"
			type="number"
			:size="size"
			:label="displayLabel"
			:required="!!field.reqd"
			:placeholder="field.placeholder || displayLabel"
			v-model="model[field.fieldname]"
			:disabled="isDisabled"
		/>
		<div v-else-if="isDateField" class="w-full space-y-1.5">
			<label class="block text-sm text-ink-gray-5">
				{{ displayLabel }}
				<span v-if="field.reqd" class="text-ink-red-3">*</span>
			</label>
			<DateTimePicker
				v-if="field.fieldtype === 'Datetime'"
				class="w-full"
				:placeholder="field.placeholder || 'Select date & time'"
				:disabled="isDisabled"
				v-model="model[field.fieldname]"
			/>
			<DatePicker
				v-else
				class="w-full"
				:placeholder="field.placeholder || 'Select date'"
				:disabled="isDisabled"
				v-model="model[field.fieldname]"
			/>
		</div>
		<div v-else-if="field.fieldtype === 'Attach' || field.fieldtype === 'Attach Image'" class="w-full space-y-1.5">
			<label class="block text-sm text-ink-gray-5">
				{{ displayLabel }}
				<span v-if="field.reqd" class="text-ink-red-3">*</span>
			</label>
			<FormControl
				type="text"
				:size="size"
				:placeholder="field.placeholder || 'File URL /path'"
				v-model="model[field.fieldname]"
				:disabled="isDisabled"
			/>
		</div>
		<FormControl
			v-else
			type="text"
			:size="size"
			:label="displayLabel"
			:required="!!field.reqd"
			:placeholder="field.placeholder || displayLabel"
			v-model="model[field.fieldname]"
			:disabled="isDisabled"
		/>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { DatePicker, DateTimePicker, FormControl, TextEditor } from "frappe-ui";
import LinkField from "@/components/LinkField.vue";
import { SAFE_TEXT_EDITOR_BUTTONS } from "@/utils/textEditor";

const props = defineProps({
	field: { type: Object, required: true },
	model: { type: Object, required: true },
	disabled: { type: Boolean, default: false },
	size: { type: String, default: "md" },
});

const isDisabled = computed(() => props.disabled || !!props.field.read_only);

const displayLabel = computed(() => {
	if (props.field.label) return props.field.label;
	return String(props.field.fieldname || "")
		.replace(/_/g, " ")
		.replace(/\b\w/g, (c) => c.toUpperCase());
});

const isPlainText = computed(() => {
	const ft = props.field.fieldtype;
	return ft === "Text" || ft === "Long Text" || ft === "Small Text";
});

const isRichText = computed(() => props.field.fieldtype === "Text Editor");

const isDateField = computed(() => {
	const ft = props.field.fieldtype;
	if (ft === "Date" || ft === "Datetime" || ft === "Time") return true;
	const ph = (props.field.placeholder || "").toLowerCase();
	const name = (props.field.fieldname || "").toLowerCase();
	if (ft === "Data" && (ph.includes("yyyy") || name.endsWith("_date") || name.includes("date"))) {
		return true;
	}
	return false;
});

function onSelectChange(e) {
	props.model[props.field.fieldname] = e.target.value;
}

function normalizeOptions(field) {
	const opts = field.options || [];
	if (!opts.length) return [];
	if (typeof opts[0] === "object") {
		return opts.map((o) => ({
			label: o.label ?? o.value ?? "",
			value: o.value ?? o.label ?? "",
		}));
	}
	return opts.map((o) => ({
		label: o === "" || o == null ? "—" : String(o),
		value: o,
	}));
}

function resolveFilters(field) {
	const base = { ...(field.filters || {}) };
	for (const [k, v] of Object.entries(base)) {
		if (typeof v === "string" && v.startsWith("$")) {
			const key = v.slice(1);
			const val = props.model?.[key];
			if (val) base[k] = val;
			else delete base[k];
		}
	}
	return base;
}
</script>
