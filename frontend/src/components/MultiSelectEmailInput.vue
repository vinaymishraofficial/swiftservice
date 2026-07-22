<template>
	<div class="ss-email-ms w-full">
		<div
			class="flex min-h-9 flex-wrap items-center gap-1 rounded-md border-0 bg-surface-gray-2 px-2 py-1 focus-within:bg-surface-white focus-within:ring-1 focus-within:ring-outline-gray-3"
		>
			<span
				v-for="email in model"
				:key="email"
				class="inline-flex max-w-full items-center gap-1 rounded bg-surface-white px-1.5 py-0.5 text-xs font-medium text-ink-gray-8 ring-1 ring-outline-gray-2"
			>
				<span class="truncate">{{ email }}</span>
				<button
					type="button"
					class="shrink-0 text-ink-gray-5 hover:text-ink-gray-8"
					title="Remove"
					@click="remove(email)"
				>
					×
				</button>
			</span>
			<input
				ref="inputEl"
				v-model="query"
				type="text"
				class="min-w-[8rem] flex-1 border-0 bg-transparent py-1 text-sm text-ink-gray-9 outline-none placeholder:text-ink-gray-4"
				:placeholder="model.length ? '' : placeholder"
				autocomplete="off"
				@keydown="onKeydown"
				@input="onInput"
				@blur="onBlur"
				@focus="open = true"
			/>
		</div>
		<div
			v-if="open && (suggestions.length || query.trim())"
			class="relative z-10 mt-1 max-h-48 overflow-auto rounded-lg border border-outline-gray-2 bg-surface-modal py-1 shadow-lg"
		>
			<button
				v-for="(s, i) in suggestions"
				:key="s.value"
				type="button"
				class="flex w-full flex-col px-3 py-1.5 text-left hover:bg-surface-gray-2"
				:class="i === activeIndex ? 'bg-surface-gray-2' : ''"
				@mousedown.prevent="pick(s.value)"
			>
				<span class="text-sm font-medium text-ink-gray-9">{{ s.label || s.value }}</span>
				<span v-if="s.description || s.value" class="text-xs text-ink-gray-5">
					{{ s.description || s.value }}
				</span>
			</button>
			<button
				v-if="canAddTyped"
				type="button"
				class="flex w-full items-center px-3 py-1.5 text-left text-sm text-ink-gray-8 hover:bg-surface-gray-2"
				@mousedown.prevent="pick(query.trim())"
			>
				Add “{{ query.trim() }}”
			</button>
			<div
				v-if="!suggestions.length && !canAddTyped"
				class="px-3 py-2 text-sm text-ink-gray-5"
			>
				Type an email address
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { call } from "frappe-ui";

const props = defineProps({
	placeholder: { type: String, default: "Add email…" },
});

const model = defineModel({ type: Array, default: () => [] });

const query = ref("");
const open = ref(false);
const suggestions = ref([]);
const activeIndex = ref(0);
const inputEl = ref(null);
let timer = null;

const canAddTyped = computed(() => {
	const v = query.value.trim();
	if (!v || !looksLikeEmail(v)) return false;
	return !model.value.includes(v);
});

function looksLikeEmail(v) {
	return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
}

function remove(email) {
	model.value = model.value.filter((e) => e !== email);
}

function pick(email) {
	const v = String(email || "").trim();
	if (!v) return;
	if (!model.value.includes(v)) {
		model.value = [...model.value, v];
	}
	query.value = "";
	suggestions.value = [];
	open.value = false;
	activeIndex.value = 0;
	inputEl.value?.focus();
}

function commitTyped() {
	const v = query.value.trim().replace(/,$/, "");
	if (!v) return;
	if (looksLikeEmail(v) || v.includes("@")) {
		pick(v);
	}
}

function onKeydown(e) {
	if (e.key === "Enter" || e.key === "," || e.key === "Tab") {
		if (suggestions.value[activeIndex.value]) {
			e.preventDefault();
			pick(suggestions.value[activeIndex.value].value);
			return;
		}
		if (canAddTyped.value) {
			e.preventDefault();
			commitTyped();
		}
	} else if (e.key === "Backspace" && !query.value && model.value.length) {
		remove(model.value[model.value.length - 1]);
	} else if (e.key === "ArrowDown") {
		e.preventDefault();
		activeIndex.value = Math.min(activeIndex.value + 1, Math.max(suggestions.value.length - 1, 0));
	} else if (e.key === "ArrowUp") {
		e.preventDefault();
		activeIndex.value = Math.max(activeIndex.value - 1, 0);
	} else if (e.key === "Escape") {
		open.value = false;
	}
}

function onInput() {
	open.value = true;
	clearTimeout(timer);
	timer = setTimeout(search, 200);
}

function onBlur() {
	setTimeout(() => {
		commitTyped();
		open.value = false;
	}, 150);
}

async function search() {
	const txt = query.value.trim();
	try {
		const rows = (await call("swiftservice.api.get_email_contacts", { txt })) || [];
		suggestions.value = rows
			.map((r) => ({
				value: r.value || r.email || r.name,
				label: r.label || r.full_name || r.value,
				description: r.description || r.email || r.value,
			}))
			.filter((r) => r.value && !model.value.includes(r.value))
			.slice(0, 12);
		activeIndex.value = 0;
	} catch {
		suggestions.value = [];
	}
}

watch(open, (v) => {
	if (v && !suggestions.value.length) search();
});

onBeforeUnmount(() => clearTimeout(timer));
</script>
