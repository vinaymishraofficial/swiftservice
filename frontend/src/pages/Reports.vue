<template>
	<div class="flex h-full flex-col overflow-hidden">
		<LayoutHeader>
			<template #left-header>
				<div class="min-w-0">
					<div class="text-lg font-medium text-ink-gray-9">Reports</div>
					<div v-if="moduleLabel" class="truncate text-sm text-ink-gray-5">
						{{ moduleLabel }}
					</div>
				</div>
			</template>
			<template #right-header>
				<Button
					variant="outline"
					label="Refresh"
					iconLeft="lucide-refresh-cw"
					:loading="loading"
					@click="loadReport(active)"
				/>
			</template>
		</LayoutHeader>

		<div class="border-b border-outline-gray-2 px-3 py-3 sm:px-5">
			<div class="flex gap-1 overflow-x-auto rounded-lg bg-surface-gray-1 p-1">
				<button
					v-for="r in visibleReports"
					:key="r.key"
					type="button"
					class="shrink-0 rounded-md px-3 py-1.5 text-sm transition"
					:class="
						active === r.key
							? 'bg-surface-white font-medium text-ink-gray-9 shadow-sm'
							: 'text-ink-gray-6 hover:text-ink-gray-8'
					"
					@click="selectReport(r.key)"
				>
					{{ r.label }}
				</button>
			</div>
		</div>

		<div class="flex-1 overflow-auto px-3 py-4 sm:px-5">
			<div v-if="loading" class="py-12 text-center text-sm text-ink-gray-5">Loading…</div>
			<div
				v-else-if="!rows.length"
				class="rounded-xl border border-dashed border-outline-gray-2 py-16 text-center text-sm text-ink-gray-5"
			>
				No rows for this report
			</div>
			<div v-else class="overflow-hidden rounded-xl border border-outline-gray-2 bg-surface-white">
				<table class="min-w-full text-left text-sm">
					<thead class="bg-surface-gray-1">
						<tr class="text-ink-gray-5">
							<th
								v-for="col in tableColumns"
								:key="col"
								class="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide"
							>
								{{ col.replace(/_/g, " ") }}
							</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="(row, idx) in rows"
							:key="idx"
							class="border-t border-outline-gray-1 hover:bg-surface-gray-1"
						>
							<td
								v-for="col in tableColumns"
								:key="col"
								class="max-w-[14rem] truncate px-3 py-2.5 text-ink-gray-8"
							>
								{{ row[col] ?? "—" }}
							</td>
						</tr>
					</tbody>
				</table>
				<div class="border-t border-outline-gray-1 px-3 py-2 text-xs text-ink-gray-5">
					{{ rows.length }} row(s)
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, call } from "frappe-ui";
import LayoutHeader from "@/components/LayoutHeader.vue";
import { ALL_REPORTS, getModuleById } from "@/config/modules";

const route = useRoute();
const router = useRouter();

const active = ref("open_tickets");
const rows = ref([]);
const loading = ref(false);

const moduleId = computed(() => {
	const q = route.query?.module;
	return typeof q === "string" && q ? q : "home";
});

const moduleLabel = computed(() => {
	if (moduleId.value === "home") return "";
	return getModuleById(moduleId.value)?.label || "";
});

const visibleReports = computed(() => {
	const mid = moduleId.value;
	if (!mid || mid === "home") return ALL_REPORTS;
	const filtered = ALL_REPORTS.filter((r) => (r.modules || []).includes(mid));
	return filtered.length ? filtered : ALL_REPORTS;
});

const tableColumns = computed(() => {
	if (!rows.value.length) return ["name"];
	return Object.keys(rows.value[0]);
});

async function loadReport(key) {
	active.value = key;
	loading.value = true;
	try {
		rows.value = (await call("swiftservice.api.get_report_data", { report_name: key })) || [];
	} finally {
		loading.value = false;
	}
}

function selectReport(key) {
	const query = { ...route.query, report: key };
	if (moduleId.value && moduleId.value !== "home") {
		query.module = moduleId.value;
	}
	router.replace({ path: "/reports", query });
	loadReport(key);
}

watch(
	() => [route.query?.module, route.query?.report, visibleReports.value],
	() => {
		const reportQ = route.query?.report;
		const keys = visibleReports.value.map((r) => r.key);
		const next =
			typeof reportQ === "string" && keys.includes(reportQ)
				? reportQ
				: keys[0] || "open_tickets";
		if (next !== active.value || !rows.value.length) {
			loadReport(next);
		}
	},
	{ immediate: true },
);

onMounted(() => {
	/* watch immediate handles initial load */
});
</script>
