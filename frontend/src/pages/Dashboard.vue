<template>
	<div class="flex h-full flex-col overflow-hidden">
		<LayoutHeader>
			<template #left-header>
				<div class="text-lg font-medium text-ink-gray-9">{{ dashboardTitle }}</div>
			</template>
			<template #right-header>
				<div class="flex flex-wrap items-center justify-end gap-2">
					<TabButtons v-model="activeTab" :buttons="tabButtons" />
					<Button
						variant="outline"
						label="Refresh"
						iconLeft="lucide-refresh-cw"
						:loading="loading"
						@click="loadDashboard"
					/>
					<Button
						variant="solid"
						label="New Request"
						iconLeft="lucide-plus"
						@click="$router.push('/service-requests/new')"
					/>
				</div>
			</template>
		</LayoutHeader>

		<div class="flex-1 overflow-auto bg-surface-gray-1 px-3 py-4 sm:px-5 sm:py-5">
			<!-- Welcome -->
			<section
				class="mb-5 flex flex-col gap-4 rounded-xl border border-outline-gray-2 bg-surface-white p-5 sm:flex-row sm:items-center sm:justify-between"
			>
				<div class="flex min-w-0 items-center gap-3">
					<Avatar
						size="xl"
						:image="brand.logo || undefined"
						:label="brand.name || firstName"
					/>
					<div class="min-w-0">
						<div class="text-p-sm text-ink-gray-5">{{ todayLabel }}</div>
						<div class="truncate text-lg font-medium text-ink-gray-9">
							{{ greeting }}, {{ firstName }}
						</div>
						<div class="truncate text-p-sm text-ink-gray-6">
							{{
								activeTab === "my_stats"
									? "Your assigned work"
									: `${brand.name || "SwiftService"} overview`
							}}
						</div>
					</div>
				</div>
				<div class="flex flex-wrap gap-2">
					<Button
						variant="outline"
						label="Dispatch"
						iconLeft="lucide-map"
						@click="$router.push('/dispatch')"
					/>
					<Button
						variant="outline"
						label="Tickets"
						iconLeft="lucide-clipboard-list"
						@click="$router.push('/service-requests')"
					/>
					<Button
						variant="outline"
						label="Visits"
						iconLeft="lucide-hard-hat"
						@click="$router.push('/engineer-visits')"
					/>
				</div>
			</section>

			<!-- Modules -->
			<section class="mb-5 rounded-xl border border-outline-gray-2 bg-surface-white p-5">
				<div class="mb-4">
					<div class="text-base font-medium text-ink-gray-9">Modules</div>
					<div class="text-p-sm text-ink-gray-5">Open a process area</div>
				</div>
				<ModuleIconGrid exclude-home variant="home" @select="openModule" />
			</section>

			<!-- KPIs (frappe-ui NumberChart) -->
			<section class="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
				<button
					v-for="card in kpiCards"
					:key="card.title"
					type="button"
					class="overflow-hidden rounded-xl border border-outline-gray-2 text-left shadow-sm transition hover:border-outline-gray-3"
					:class="card.emphasis"
					@click="card.to && $router.push(card.to)"
				>
					<NumberChart :config="card.config" />
				</button>
			</section>

			<!-- Panels -->
			<section class="grid gap-4 xl:grid-cols-5">
				<div
					class="rounded-xl border border-outline-gray-2 bg-surface-white p-5 xl:col-span-2"
				>
					<div class="mb-4">
						<div class="text-base font-medium text-ink-gray-9">Status mix</div>
						<div class="text-p-sm text-ink-gray-5">Service requests by status</div>
					</div>
					<div class="space-y-3">
						<div v-for="row in topStatuses" :key="row.status" class="space-y-1.5">
							<div class="flex items-center justify-between gap-2 text-p-sm">
								<span class="truncate text-ink-gray-7">{{ row.status }}</span>
								<span class="tabular-nums text-ink-gray-8">{{ row.count }}</span>
							</div>
							<div
								class="h-1.5 w-full shrink-0 overflow-hidden rounded-full bg-surface-gray-2"
								role="progressbar"
								:aria-valuenow="statusPercent(row.count)"
								aria-valuemin="0"
								aria-valuemax="100"
							>
								<div
									class="h-full rounded-full bg-surface-gray-7"
									:style="{ width: `${statusPercent(row.count)}%` }"
								/>
							</div>
						</div>
						<div
							v-if="!topStatuses.length"
							class="flex h-32 items-center justify-center text-p-sm text-ink-gray-5"
						>
							No status data yet
						</div>
					</div>
				</div>

				<div
					class="rounded-xl border border-outline-gray-2 bg-surface-white p-5 xl:col-span-3"
				>
					<div class="mb-3 flex items-center justify-between gap-2">
						<div>
							<div class="text-base font-medium text-ink-gray-9">Recent requests</div>
							<div class="text-p-sm text-ink-gray-5">Latest tickets</div>
						</div>
						<Button
							variant="ghost"
							label="View all"
							@click="$router.push('/service-requests')"
						/>
					</div>
					<div class="divide-y divide-outline-gray-1">
						<button
							v-for="row in dashboard.recent_requests || []"
							:key="row.name"
							type="button"
							class="flex w-full items-center gap-3 py-3 text-left hover:bg-surface-gray-1"
							@click="$router.push(`/service-requests/${encodeURIComponent(row.name)}`)"
						>
							<Avatar size="md" :label="row.subject || row.name" />
							<div class="min-w-0 flex-1">
								<div class="truncate text-sm font-medium text-ink-gray-9">
									{{ row.subject || row.name }}
								</div>
								<div class="truncate text-p-sm text-ink-gray-5">
									{{ row.customer || "—" }} · {{ row.name }}
								</div>
							</div>
							<div class="flex shrink-0 flex-col items-end gap-1 sm:flex-row sm:items-center">
								<Badge
									v-if="row.priority"
									:label="row.priority"
									:theme="priorityTheme(row.priority)"
									variant="subtle"
								/>
								<Badge
									:label="row.status || '—'"
									:theme="statusTheme(row.status)"
									variant="subtle"
								/>
							</div>
						</button>
						<div
							v-if="!(dashboard.recent_requests || []).length"
							class="flex h-32 items-center justify-center text-p-sm text-ink-gray-5"
						>
							No recent requests
						</div>
					</div>
				</div>
			</section>
		</div>
	</div>
</template>

<script setup>
import { computed, h, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useStorage } from "@vueuse/core";
import { Avatar, Badge, Button, NumberChart, TabButtons, call } from "frappe-ui";
import LayoutHeader from "@/components/LayoutHeader.vue";
import ModuleIconGrid from "@/components/ModuleIconGrid.vue";
import { setStoredModuleId } from "@/config/modules";
import { useSettings } from "@/stores/settings";
import { sessionStore } from "@/stores/session";
import LucideBuilding2 from "~icons/lucide/building-2";
import LucideUser from "~icons/lucide/user";

const router = useRouter();
const { brand } = useSettings();
const session = sessionStore();
const loading = ref(false);
const hydrated = ref(false);
const activeTab = useStorage("ss_dashboard_active_tab", "organization");

const dashboard = reactive({
	open_requests: 0,
	in_progress: 0,
	pending_visits: 0,
	active_amc: 0,
	critical_tickets: 0,
	sla_breach: 0,
	completed_month: 0,
	status_breakdown: [],
	recent_requests: [],
});

const tabButtons = [
	{
		value: "organization",
		label: "My Organization",
		iconLeft: h(LucideBuilding2, { class: "size-4" }),
	},
	{
		value: "my_stats",
		label: "My Stats",
		iconLeft: h(LucideUser, { class: "size-4" }),
	},
];

const dashboardTitle = computed(() =>
	activeTab.value === "my_stats" ? "My Dashboard" : "Organization Dashboard",
);

const firstName = computed(() => {
	const name = session.fullName || session.user || "there";
	return String(name).split(" ")[0] || "there";
});

const greeting = computed(() => {
	const hour = new Date().getHours();
	if (hour < 12) return "Good morning";
	if (hour < 17) return "Good afternoon";
	return "Good evening";
});

const todayLabel = computed(() =>
	new Date().toLocaleDateString(undefined, {
		weekday: "long",
		month: "short",
		day: "numeric",
	}),
);

const topStatuses = computed(() => (dashboard.status_breakdown || []).slice(0, 8));

const kpiCards = computed(() => {
	const v = (n) => (loading.value && !hydrated.value ? 0 : n || 0);
	return [
		{
			title: "Open tickets",
			to: "/service-requests",
			emphasis: "bg-surface-white",
			config: { title: "Open tickets", value: v(dashboard.open_requests) },
		},
		{
			title: "In progress",
			to: "/service-requests",
			emphasis: "bg-surface-white",
			config: { title: "In progress", value: v(dashboard.in_progress) },
		},
		{
			title: "Critical priority",
			to: "/service-requests",
			emphasis: "bg-surface-white border-outline-red-2",
			config: { title: "Critical priority", value: v(dashboard.critical_tickets) },
		},
		{
			title: "SLA breach",
			to: "/reports?module=home&report=sla_breach",
			emphasis: "bg-surface-white",
			config: { title: "SLA breach", value: v(dashboard.sla_breach) },
		},
		{
			title: "Pending visits",
			to: "/engineer-visits",
			emphasis: "bg-surface-white",
			config: { title: "Pending visits", value: v(dashboard.pending_visits) },
		},
		{
			title: "Active AMC",
			to: "/amc-contracts",
			emphasis: "bg-surface-white",
			config: { title: "Active AMC", value: v(dashboard.active_amc) },
		},
	];
});

function openModule(mod) {
	setStoredModuleId(mod.id);
	router.push(mod.homeRoute || "/dashboard");
}

/** Frappe Badge themes for priority */
function priorityTheme(priority) {
	const v = String(priority || "").toLowerCase();
	if (["critical", "urgent"].includes(v)) return "red";
	if (v === "high") return "orange";
	if (v === "medium") return "blue";
	if (v === "low") return "gray";
	return "gray";
}

function statusTheme(status) {
	const v = String(status || "").toLowerCase();
	if (["completed", "closed", "resolved"].includes(v)) return "green";
	if (["cancelled", "rejected", "failed"].includes(v)) return "red";
	if (["open", "draft", "pending", "under validation"].includes(v)) return "orange";
	return "gray";
}

function statusPercent(count) {
	const max = Math.max(1, ...topStatuses.value.map((r) => r.count || 0));
	return Math.round(((count || 0) / max) * 100);
}

async function loadDashboard() {
	loading.value = true;
	try {
		const data = await call("swiftservice.api.get_dashboard_data", {
			scope: activeTab.value === "my_stats" ? "my_stats" : "organization",
		});
		Object.assign(dashboard, data || {});
		hydrated.value = true;
	} catch (e) {
		console.warn("Dashboard load failed:", e);
	} finally {
		loading.value = false;
	}
}

watch(activeTab, () => loadDashboard());

onMounted(() => {
	if (!session.user) session.fetchUser?.();
	loadDashboard();
});
</script>
