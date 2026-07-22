<template>
	<Dialog
		v-model="show"
		:options="{ size: 'xl', position: 'top' }"
		:disable-outside-click-to-close="false"
	>
		<template #body>
			<div class="bg-surface-modal">
				<div class="relative">
					<div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
						<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
					</div>
					<input
						ref="inputRef"
						v-model="query"
						type="search"
						autocomplete="off"
						placeholder="Search modules, lists, pages…"
						class="w-full border-none bg-transparent py-3.5 pl-11 pr-4 text-base text-ink-gray-8 placeholder:text-ink-gray-4 focus:outline-none focus:ring-0"
						@keydown.down.prevent="move(1)"
						@keydown.up.prevent="move(-1)"
						@keydown.enter.prevent="goActive"
						@keydown.esc.prevent="show = false"
					/>
				</div>

				<div class="max-h-[min(28rem,60vh)] overflow-y-auto border-t border-outline-gray-1 pb-2">
					<div
						v-for="group in groups"
						:key="group.title"
						class="mt-3 first:mt-2"
					>
						<div
							v-if="!group.hideTitle"
							class="mb-1.5 px-4 text-xs font-medium uppercase tracking-wide text-ink-gray-5"
						>
							{{ group.title }}
						</div>
						<button
							v-for="(item, idx) in group.items"
							:key="item.name"
							type="button"
							class="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm text-ink-gray-8"
							:class="
								flatIndex(group, idx) === activeIndex
									? 'bg-surface-gray-2'
									: 'hover:bg-surface-gray-1'
							"
							@mouseenter="activeIndex = flatIndex(group, idx)"
							@click="select(item)"
						>
							<component
								:is="item.icon"
								v-if="item.icon"
								class="size-4 shrink-0 text-ink-gray-6"
							/>
							<span class="min-w-0 flex-1 truncate font-medium">{{ item.title }}</span>
							<span
								v-if="item.description"
								class="max-w-[40%] shrink-0 truncate text-xs text-ink-gray-5"
							>
								{{ item.description }}
							</span>
						</button>
					</div>
					<div
						v-if="!flatItems.length"
						class="px-4 py-10 text-center text-sm text-ink-gray-5"
					>
						No matches for “{{ query }}”
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { Dialog } from "frappe-ui";
import { modules, setStoredModuleId } from "@/config/modules";
import { resources } from "@/config/resources";
import LucideSearch from "~icons/lucide/search";
import LucideLayoutDashboard from "~icons/lucide/layout-dashboard";
import LucideMap from "~icons/lucide/map";
import LucideClipboardList from "~icons/lucide/clipboard-list";

const props = defineProps({
	modelValue: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);

const router = useRouter();
const query = ref("");
const activeIndex = ref(0);
const inputRef = ref(null);

const show = computed({
	get: () => props.modelValue,
	set: (v) => emit("update:modelValue", v),
});

const needle = computed(() => (query.value || "").trim().toLowerCase());

function matches(text) {
	if (!needle.value) return true;
	return String(text || "")
		.toLowerCase()
		.includes(needle.value);
}

const groups = computed(() => {
	const quick = [
		{
			name: "home",
			title: "Home",
			description: "Dashboard",
			icon: LucideLayoutDashboard,
			to: "/dashboard",
		},
		{
			name: "dispatch",
			title: "Dispatch Board",
			description: "Field",
			icon: LucideMap,
			to: "/dispatch",
		},
		{
			name: "tickets",
			title: "Service Requests",
			description: "Tickets",
			icon: LucideClipboardList,
			to: "/service-requests",
		},
	].filter((i) => matches(i.title) || matches(i.description));

	const moduleItems = modules
		.filter((m) => m.showInGrid !== false)
		.filter((m) => matches(m.label) || matches(m.description))
		.map((m) => ({
			name: `mod-${m.id}`,
			title: m.label,
			description: m.description || "Module",
			icon: m.icon || LucideLayoutDashboard,
			to: m.homeRoute || "/dashboard",
			moduleId: m.id,
		}));

	const resourceItems = Object.values(resources)
		.filter((r) => matches(r.title) || matches(r.doctype) || matches(r.route))
		.slice(0, 30)
		.map((r) => ({
			name: `res-${r.route}`,
			title: r.title,
			description: r.doctype || "List",
			icon: LucideSearch,
			to: `/${r.route}`,
		}));

	return [
		{ title: "Quick", items: quick, hideTitle: !needle.value },
		{ title: "Modules", items: moduleItems },
		{ title: "Lists", items: resourceItems },
	].filter((g) => g.items.length);
});

const flatItems = computed(() => groups.value.flatMap((g) => g.items));

function flatIndex(group, idxInGroup) {
	let i = 0;
	for (const g of groups.value) {
		if (g === group) return i + idxInGroup;
		i += g.items.length;
	}
	return idxInGroup;
}

function move(delta) {
	const len = flatItems.value.length;
	if (!len) return;
	activeIndex.value = (activeIndex.value + delta + len) % len;
}

function goActive() {
	const item = flatItems.value[activeIndex.value];
	if (item) select(item);
}

function select(item) {
	if (!item?.to) return;
	if (item.moduleId) setStoredModuleId(item.moduleId);
	show.value = false;
	router.push(item.to);
}

watch(show, async (open) => {
	if (open) {
		query.value = "";
		activeIndex.value = 0;
		await nextTick();
		inputRef.value?.focus?.();
	}
});

watch(needle, () => {
	activeIndex.value = 0;
});

function onGlobalKey(e) {
	if (e.key === "k" && (e.metaKey || e.ctrlKey) && !e.target?.closest?.(".ProseMirror")) {
		e.preventDefault();
		show.value = !show.value;
	}
}

onMounted(() => window.addEventListener("keydown", onGlobalKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onGlobalKey));
</script>
