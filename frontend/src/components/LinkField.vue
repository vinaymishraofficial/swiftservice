<template>
	<div ref="root" class="ss-link-field relative w-full" :class="compact ? '' : 'space-y-1.5'">
		<label v-if="showLabel" class="block text-sm text-ink-gray-5">
			{{ displayLabel }}
			<span v-if="reqd" class="text-ink-red-3">*</span>
		</label>
		<div ref="trigger" class="relative">
			<input
				v-model="query"
				type="text"
				autocomplete="off"
				class="form-input w-full rounded-md border-0 bg-surface-gray-2 text-ink-gray-8 placeholder:text-ink-gray-4 focus:bg-surface-white focus:ring-1 focus:ring-outline-gray-3 disabled:opacity-60"
				:class="[
					compact ? 'pl-8' : 'pl-3',
					size === 'md' ? 'py-2 pr-10 text-base' : 'h-7 py-0 pr-9 text-base',
				]"
				:placeholder="placeholder || displayLabel || (doctype ? `Search ${doctype}…` : 'Search…')"
				:disabled="disabled"
				@focus="onFocus"
				@input="onInput"
				@keydown.enter.prevent="pickFirst"
				@keydown.escape="open = false"
			/>
			<span
				v-if="compact"
				class="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-gray-4"
			>
				⌕
			</span>
			<button
				v-if="modelValue && !disabled"
				type="button"
				class="absolute right-2 top-1/2 flex size-6 -translate-y-1/2 items-center justify-center rounded text-ink-gray-5 hover:bg-surface-gray-3 hover:text-ink-gray-8"
				title="Clear"
				@click.stop="clear"
			>
				<span class="text-base leading-none">×</span>
			</button>
		</div>

		<Teleport to="body">
			<div
				v-if="open && !disabled"
				ref="panel"
				class="ss-link-field-panel fixed z-[9999] overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-modal shadow-lg"
				:style="panelStyle"
			>
				<div class="max-h-52 overflow-auto">
					<div v-if="loading" class="px-3 py-2.5 text-sm text-ink-gray-5">Searching…</div>
					<button
						v-for="row in results"
						:key="row.value"
						type="button"
						class="flex w-full items-start gap-2 px-3 py-2 text-left hover:bg-surface-gray-2"
						@mousedown.prevent="select(row)"
						@click.prevent="select(row)"
					>
						<div class="min-w-0 flex-1">
							<div class="truncate text-sm font-medium text-ink-gray-8">
								{{ row.label || row.value }}
							</div>
							<div
								v-if="row.description"
								class="truncate text-xs text-ink-gray-5"
							>
								{{ row.description }}
							</div>
						</div>
					</button>
					<div
						v-if="!loading && !results.length"
						class="px-3 py-2.5 text-sm text-ink-gray-5"
					>
						No {{ doctype }} found
					</div>
				</div>
				<div class="border-t border-outline-gray-1 bg-surface-white p-1">
					<button
						v-if="canCreate"
						type="button"
						class="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-ink-gray-8 hover:bg-surface-gray-2"
						@mousedown.prevent="openCreate"
						@click.prevent="openCreate"
					>
						<span class="text-base leading-none text-ink-gray-6">+</span>
						Create New
					</button>
					<button
						type="button"
						class="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-ink-gray-8 hover:bg-surface-gray-2"
						@mousedown.prevent="clear"
						@click.prevent="clear"
					>
						<span class="text-base leading-none text-ink-gray-6">×</span>
						Clear
					</button>
				</div>
			</div>
		</Teleport>

		<Dialog
			v-model="showCreate"
			:options="{ title: `New ${doctype}`, size: 'md' }"
			:disable-outside-click-to-close="true"
		>
			<template #body-content>
				<div class="space-y-3">
					<label class="block text-sm text-ink-gray-5">
						Name <span class="text-ink-red-3">*</span>
					</label>
					<input
						v-model="createTitle"
						type="text"
						class="form-input w-full rounded-md border-0 bg-surface-gray-2 px-3 py-2 text-base text-ink-gray-8 focus:bg-surface-white focus:ring-1 focus:ring-outline-gray-3"
						:placeholder="`Enter ${doctype} name`"
						@keydown.enter.prevent="doCreate"
					/>
					<p v-if="createError" class="text-sm text-ink-red-3">{{ createError }}</p>
				</div>
			</template>
			<template #actions>
				<Button class="w-full" variant="solid" label="Create" :loading="creating" @click="doCreate" />
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Button, Dialog, call, toast } from "frappe-ui";

const NO_CREATE = new Set(["User", "Company", "Currency", "UOM", "Role", "DocType"]);

const props = defineProps({
	doctype: { type: String, required: true },
	label: { type: String, default: "" },
	placeholder: { type: String, default: "" },
	filters: { type: Object, default: () => ({}) },
	reqd: { type: Boolean, default: false },
	disabled: { type: Boolean, default: false },
	compact: { type: Boolean, default: false },
	size: { type: String, default: "md" },
});

const modelValue = defineModel({ default: "" });
const query = ref("");
const open = ref(false);
const loading = ref(false);
const results = ref([]);
const root = ref(null);
const trigger = ref(null);
const panel = ref(null);
const panelStyle = ref({});
const showCreate = ref(false);
const createTitle = ref("");
const createError = ref("");
const creating = ref(false);
let timer = null;

const displayLabel = computed(() => props.label || "");
/** Never fall back to doctype as a visible label (filters use placeholder only). */
const showLabel = computed(() => !props.compact && !!props.label);
const canCreate = computed(() => props.doctype && !NO_CREATE.has(props.doctype));

watch(
	modelValue,
	(v) => {
		if (v && !open.value) query.value = v;
		if (!v && !open.value) query.value = "";
	},
	{ immediate: true },
);

watch(
	() => props.filters,
	() => {
		if (open.value) search();
	},
	{ deep: true },
);

watch(open, async (v) => {
	if (v) {
		await nextTick();
		updatePanelPosition();
	}
});

function updatePanelPosition() {
	const el = trigger.value;
	if (!el) return;
	const rect = el.getBoundingClientRect();
	const width = Math.max(rect.width, 220);
	let left = rect.left;
	if (left + width > window.innerWidth - 8) {
		left = Math.max(8, window.innerWidth - width - 8);
	}
	const spaceBelow = window.innerHeight - rect.bottom;
	const openUp = spaceBelow < 240 && rect.top > spaceBelow;
	panelStyle.value = {
		left: `${left}px`,
		width: `${width}px`,
		top: openUp ? "auto" : `${rect.bottom + 4}px`,
		bottom: openUp ? `${window.innerHeight - rect.top + 4}px` : "auto",
	};
}

function onFocus() {
	if (props.disabled) return;
	open.value = true;
	search();
}

function onInput() {
	open.value = true;
	clearTimeout(timer);
	timer = setTimeout(search, 200);
}

async function search() {
	if (!props.doctype) return;
	loading.value = true;
	try {
		const txt = open.value ? query.value : modelValue.value || "";
		results.value =
			(await call("swiftservice.api.search_link", {
				doctype: props.doctype,
				txt: txt === modelValue.value ? "" : txt,
				filters: props.filters || {},
				limit: 20,
			})) || [];
	} catch (e) {
		results.value = [];
	} finally {
		loading.value = false;
		await nextTick();
		updatePanelPosition();
	}
}

function select(row) {
	modelValue.value = row.value;
	query.value = row.label || row.value;
	open.value = false;
}

function pickFirst() {
	if (results.value.length) select(results.value[0]);
}

function clear() {
	modelValue.value = "";
	query.value = "";
	results.value = [];
	open.value = false;
}

function openCreate() {
	createTitle.value = (query.value || "").trim();
	createError.value = "";
	open.value = false;
	showCreate.value = true;
}

async function doCreate() {
	const title = (createTitle.value || "").trim();
	if (!title) {
		createError.value = "Name is required";
		return;
	}
	creating.value = true;
	createError.value = "";
	try {
		const res = await call("swiftservice.api.quick_create_link", {
			doctype: props.doctype,
			title,
		});
		modelValue.value = res.value;
		query.value = res.label || res.value;
		showCreate.value = false;
		toast.success(`${props.doctype} created`);
	} catch (e) {
		createError.value = e?.messages?.[0] || e?.message || "Could not create";
	} finally {
		creating.value = false;
	}
}

function onDocClick(e) {
	if (root.value?.contains(e.target) || panel.value?.contains(e.target)) return;
	open.value = false;
}

function onScrollOrResize() {
	if (open.value) updatePanelPosition();
}

onMounted(() => {
	document.addEventListener("click", onDocClick);
	window.addEventListener("resize", onScrollOrResize);
	window.addEventListener("scroll", onScrollOrResize, true);
});
onBeforeUnmount(() => {
	document.removeEventListener("click", onDocClick);
	window.removeEventListener("resize", onScrollOrResize);
	window.removeEventListener("scroll", onScrollOrResize, true);
	clearTimeout(timer);
});
</script>
