<template>
	<div ref="root" class="relative w-full">
		<button
			type="button"
			class="flex w-full items-center gap-1 rounded border-0 bg-surface-gray-2 px-2 text-left text-base transition hover:bg-surface-gray-3 focus:bg-surface-white focus:outline-none focus-visible:ring-1 focus-visible:ring-outline-gray-3 disabled:opacity-60"
			:class="[
				size === 'md' ? 'h-9 py-2' : 'h-7',
				open ? 'bg-surface-white ring-1 ring-outline-gray-3' : '',
			]"
			:disabled="disabled"
			@click.stop="toggle"
		>
			<span
				class="min-w-0 flex-1 truncate"
				:class="hasValue ? 'font-medium text-ink-gray-8' : 'text-ink-gray-4'"
			>
				{{ display }}
			</span>
			<button
				v-if="allowClear && hasValue && !disabled"
				type="button"
				class="flex size-5 shrink-0 items-center justify-center rounded text-ink-gray-5 hover:bg-surface-gray-3 hover:text-ink-gray-8"
				title="Clear"
				@click.stop="clear"
			>
				×
			</button>
			<span
				class="lucide-chevron-down size-3.5 shrink-0 text-ink-gray-4 transition"
				:class="open ? 'rotate-180' : ''"
				aria-hidden="true"
			/>
		</button>

		<Teleport to="body">
			<div
				v-if="open"
				ref="panel"
				class="ss-filter-select-panel fixed z-[400] max-h-60 overflow-auto rounded-lg border border-outline-gray-2 bg-surface-modal py-1 shadow-xl"
				:style="panelStyle"
				@click.stop
				@mousedown.stop
			>
				<button
					v-if="showEmpty"
					type="button"
					class="flex w-full items-center px-3 py-1.5 text-left text-sm text-ink-gray-5 hover:bg-surface-gray-2"
					:class="!hasValue ? 'bg-surface-gray-2 font-medium text-ink-gray-8' : ''"
					@mousedown.prevent="pick('')"
				>
					{{ emptyLabel || placeholder || "—" }}
				</button>
				<button
					v-for="opt in options"
					:key="String(opt.value)"
					type="button"
					class="flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-sm text-ink-gray-8 hover:bg-surface-gray-2"
					:class="modelValue === opt.value ? 'bg-surface-gray-2 font-medium' : ''"
					@mousedown.prevent="pick(opt.value)"
				>
					<span class="truncate">{{ opt.label }}</span>
					<span
						v-if="modelValue === opt.value"
						class="lucide-check size-3.5 shrink-0 text-ink-gray-6"
						aria-hidden="true"
					/>
				</button>
				<div v-if="!options.length" class="px-3 py-2 text-sm text-ink-gray-5">No options</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
	options: { type: Array, default: () => [] },
	placeholder: { type: String, default: "All" },
	emptyLabel: { type: String, default: "" },
	showEmpty: { type: Boolean, default: true },
	allowClear: { type: Boolean, default: true },
	disabled: { type: Boolean, default: false },
	size: { type: String, default: "sm" },
});

const modelValue = defineModel({ default: "" });
const emit = defineEmits(["change"]);

const open = ref(false);
const root = ref(null);
const panel = ref(null);
const panelStyle = ref({});

const hasValue = computed(() => modelValue.value !== "" && modelValue.value != null);

const display = computed(() => {
	if (!hasValue.value) return props.placeholder || props.emptyLabel || "All";
	const hit = (props.options || []).find((o) => o.value === modelValue.value);
	return hit?.label || String(modelValue.value);
});

function toggle() {
	if (props.disabled) return;
	open.value = !open.value;
	if (open.value) nextTick(position);
}

function pick(value) {
	modelValue.value = value;
	open.value = false;
	emit("change", value);
}

function clear() {
	pick("");
}

function position() {
	const el = root.value;
	if (!el) return;
	const rect = el.getBoundingClientRect();
	const width = Math.max(rect.width, 160);
	let left = rect.left;
	if (left + width > window.innerWidth - 8) {
		left = Math.max(8, window.innerWidth - width - 8);
	}
	const spaceBelow = window.innerHeight - rect.bottom;
	const openUp = spaceBelow < 220 && rect.top > spaceBelow;
	panelStyle.value = {
		width: `${width}px`,
		left: `${left}px`,
		top: openUp ? "auto" : `${rect.bottom + 4}px`,
		bottom: openUp ? `${window.innerHeight - rect.top + 4}px` : "auto",
	};
}

function onDocPointerDown(e) {
	if (!open.value) return;
	const t = e.target;
	if (root.value?.contains(t) || panel.value?.contains(t)) return;
	open.value = false;
}

function onScrollOrResize() {
	if (open.value) position();
}

watch(open, (v) => {
	if (v) nextTick(position);
});

onMounted(() => {
	document.addEventListener("pointerdown", onDocPointerDown, true);
	window.addEventListener("resize", onScrollOrResize);
	window.addEventListener("scroll", onScrollOrResize, true);
});
onBeforeUnmount(() => {
	document.removeEventListener("pointerdown", onDocPointerDown, true);
	window.removeEventListener("resize", onScrollOrResize);
	window.removeEventListener("scroll", onScrollOrResize, true);
});
</script>
