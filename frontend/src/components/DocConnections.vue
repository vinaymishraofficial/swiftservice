<template>
	<div>
		<div class="mb-3 flex items-center justify-between gap-2">
			<div class="text-sm font-semibold text-ink-gray-9">Connections</div>
			<p class="text-xs text-ink-gray-5">Open linked lists · create with link filled</p>
		</div>
		<div v-if="loading" class="text-sm text-ink-gray-5">Loading connections…</div>
		<div v-else-if="!connections.length" class="text-sm text-ink-gray-5">No linked documents</div>
		<div v-else class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
			<div
				v-for="c in connections"
				:key="c.doctype"
				class="flex items-stretch overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white"
			>
				<button
					type="button"
					class="flex min-w-0 flex-1 items-center justify-between gap-2 px-3 py-2.5 text-left hover:bg-surface-gray-1"
					@click="openList(c)"
				>
					<div class="min-w-0">
						<div class="truncate text-sm font-medium text-ink-gray-9">{{ c.label }}</div>
						<div class="truncate text-xs text-ink-gray-5">{{ c.doctype }}</div>
					</div>
					<span
						class="flex h-7 min-w-7 shrink-0 items-center justify-center rounded-md bg-surface-gray-2 px-1.5 text-xs font-semibold text-ink-gray-8"
					>
						{{ c.count }}
					</span>
				</button>
				<button
					v-if="!c.is_parent_link"
					type="button"
					class="flex w-9 shrink-0 items-center justify-center border-l border-outline-gray-2 text-ink-gray-6 hover:bg-surface-gray-1 hover:text-ink-gray-9"
					:title="`New ${c.label}`"
					@click="createLinked(c)"
				>
					<span class="lucide-plus size-4" aria-hidden="true" />
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { call } from "frappe-ui";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
});

const router = useRouter();
const loading = ref(false);
const connections = ref([]);

async function load() {
	if (!props.doctype || !props.name || props.name === "new") {
		connections.value = [];
		return;
	}
	loading.value = true;
	try {
		connections.value =
			(await call("swiftservice.api.get_connections", {
				doctype: props.doctype,
				name: props.name,
			})) || [];
	} catch (e) {
		connections.value = [];
	} finally {
		loading.value = false;
	}
}

/** ERPNext Desk: open List with link filter pre-applied */
function openList(c) {
	if (c.is_parent_link) {
		const parent = c.items?.[0]?.name;
		if (parent) {
			router.push(`/${c.route}/${encodeURIComponent(parent)}`);
		} else {
			router.push(`/${c.route}`);
		}
		return;
	}
	const field = c.fieldname;
	if (field) {
		router.push({ path: `/${c.route}`, query: { [field]: props.name } });
	} else {
		router.push(`/${c.route}`);
	}
}

/** ERPNext Desk: new doc with parent link filled */
async function createLinked(c) {
	const field = c.fieldname;
	if (!field) {
		router.push(`/${c.route}/new`);
		return;
	}
	let linkName = props.name;
	// If current doc is cancelled SSR, prefer amendment for new links
	try {
		const parent = await call("swiftservice.api.get_doc", {
			doctype: props.doctype,
			name: props.name,
		});
		if (Number(parent?.docstatus) === 2 && parent?._amendment) {
			linkName = parent._amendment;
		}
	} catch (e) {
		/* use original */
	}
	router.push({
		path: `/${c.route}/new`,
		query: { [field]: linkName },
	});
}

watch(
	() => [props.doctype, props.name],
	() => load(),
);
onMounted(load);

defineExpose({ reload: load });
</script>
