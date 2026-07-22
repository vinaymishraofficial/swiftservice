<template>
	<div class="flex h-full flex-col overflow-hidden">
		<LayoutHeader>
			<template #left-header>
				<PageBreadcrumbs
					:parent="title"
					:parent-route="detailPath || undefined"
					current="List"
					:view-options="viewOptions"
				/>
			</template>
			<template #right-header>
				<div class="flex items-center gap-2">
					<Button
						v-if="creatable"
						variant="solid"
						label="Create"
						iconLeft="lucide-plus"
						@click="showCreate = true"
					/>
				</div>
			</template>
		</LayoutHeader>

		<!-- Customize Quick Filters (FCRM-style) -->
		<section
			v-if="customizeQuickFilter"
			class="flex shrink-0 items-center justify-between gap-2 border-b border-outline-gray-2 bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<div class="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto">
				<Draggable
					class="flex items-center gap-2"
					:list="draftQuickFilters"
					item-key="fieldname"
					group="filters"
				>
					<template #item="{ element: filter }">
						<div class="group whitespace-nowrap">
							<Button class="cursor-grab" variant="outline">
								<template #default>
									<span>{{ filter.label }}</span>
								</template>
								<template #suffix>
									<span
										class="hidden cursor-pointer text-ink-gray-5 group-hover:inline"
										@click.stop="removeDraftQuickFilter(filter)"
									>
										×
									</span>
								</template>
							</Button>
						</div>
					</template>
				</Draggable>
				<Autocomplete
					:options="quickFilterAddOptions"
					placeholder="Add Filter"
					@update:modelValue="onAddQuickFilter"
				>
					<template #target="{ togglePopover }">
						<Button
							class="whitespace-nowrap"
							variant="ghost"
							label="Add Filter"
							iconLeft="lucide-plus"
							@click="togglePopover()"
						/>
					</template>
				</Autocomplete>
			</div>
			<div class="flex shrink-0 items-center gap-1">
				<Button variant="solid" label="Save" @click="saveQuickFilters" />
				<Button variant="ghost" icon="lucide-x" @click="cancelCustomizeQuickFilters" />
			</div>
		</section>

		<!-- Filters toolbar (FCRM ViewControls: Refresh / Filter / Sort / Columns / More) -->
		<section
			v-else
			class="shrink-0 border-b border-outline-gray-2 bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<div class="flex flex-wrap items-center gap-2">
				<div
					v-for="filter in visibleQuickFilters"
					:key="filter.fieldname"
					class="w-40 shrink-0 sm:w-44"
				>
					<LinkField
						v-if="filter.type === 'Link'"
						:compact="true"
						:label="''"
						size="sm"
						v-model="filterValues[filter.fieldname]"
						:doctype="filter.options"
						:placeholder="filter.label"
						@update:modelValue="reload"
					/>
					<FilterSelect
						v-else-if="filter.type === 'Select'"
						v-model="filterValues[filter.fieldname]"
						:placeholder="filter.label"
						:options="selectOptionsFor(filter)"
						@change="reload"
					/>
					<div v-else-if="filter.type === 'Date' || filter.type === 'Datetime'" class="w-full">
						<DatePicker
							class="w-full"
							:placeholder="filter.label"
							v-model="filterValues[filter.fieldname]"
							@update:modelValue="reload"
						/>
					</div>
					<FormControl
						v-else
						type="text"
						class="w-full"
						size="sm"
						:placeholder="filter.label"
						v-model="filterValues[filter.fieldname]"
						@keydown.enter="reload"
						@update:modelValue="debouncedReload"
					/>
				</div>

				<div class="w-40 shrink-0 sm:w-44">
					<FormControl
						type="text"
						class="w-full"
						size="sm"
						placeholder="Search"
						v-model="search"
						@keydown.enter="reload"
						@update:modelValue="debouncedReload"
					/>
				</div>

				<div class="ml-auto flex shrink-0 items-center gap-1.5" @click.stop>
					<Button
						variant="ghost"
						icon="lucide-refresh-cw"
						:tooltip="'Refresh'"
						:loading="loading"
						@click="reload"
					/>

					<div class="relative flex items-center">
						<div class="flex items-center">
							<Button
								variant="outline"
								label="Filter"
								iconLeft="lucide-filter"
								data-ss-filter-btn
								:class="advancedFilters.length ? 'rounded-r-none' : ''"
								@click.stop="toggleFilterPopover"
							>
								<template v-if="advancedFilters.length" #suffix>
									<span
										class="flex h-5 w-5 items-center justify-center rounded bg-surface-white text-xs font-medium text-ink-gray-8 shadow-sm"
									>
										{{ advancedFilters.length }}
									</span>
								</template>
							</Button>
							<Button
								v-if="advancedFilters.length"
								variant="outline"
								class="rounded-l-none border-l"
								icon="lucide-x"
								@click.stop="clearAdvancedFilters"
							/>
						</div>

						<Teleport to="body">
							<div
								v-if="showFilterPopover"
								ref="filterPanelRef"
								class="ss-advanced-filter-panel fixed right-3 top-24 z-[200] w-[min(520px,calc(100vw-1.5rem))] overflow-hidden rounded-xl border border-outline-gray-2 bg-surface-modal shadow-2xl sm:right-5"
								@pointerdown.stop
								@click.stop
							>
								<div
									class="flex items-center justify-between border-b border-outline-gray-1 px-3 py-2.5"
								>
									<div class="text-sm font-semibold text-ink-gray-9">Filters</div>
									<button
										type="button"
										class="rounded p-1 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8"
										@click="closeFilterPopover"
									>
										×
									</button>
								</div>

								<div class="max-h-[min(360px,50vh)] space-y-1.5 overflow-y-auto px-3 py-2.5">
									<div
										v-for="(f, i) in advancedFilters"
										:key="f._id || i"
										class="flex items-center gap-1.5"
									>
										<span
											class="w-10 shrink-0 text-[11px] font-medium uppercase tracking-wide text-ink-gray-5"
										>
											{{ i === 0 ? "Where" : "And" }}
										</span>
										<div class="min-w-0 w-[32%]">
											<FilterSelect
												v-model="f.fieldname"
												:options="filterFieldOptions"
												:show-empty="false"
												:allow-clear="false"
												placeholder="Field"
											/>
										</div>
										<div class="w-[22%] shrink-0">
											<FilterSelect
												v-model="f.operator"
												:options="operatorOptions"
												:show-empty="false"
												:allow-clear="false"
												placeholder="Op"
											/>
										</div>
										<input
											v-model="f.value"
											type="text"
											class="form-input h-7 min-w-0 flex-1 rounded border-0 bg-surface-gray-2 px-2 text-sm text-ink-gray-8 placeholder:text-ink-gray-4 focus:bg-surface-white focus:ring-1 focus:ring-outline-gray-3"
											placeholder="Value"
											@keydown.enter="applyAdvancedFilters"
										/>
										<button
											type="button"
											class="flex size-7 shrink-0 items-center justify-center rounded text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8"
											title="Remove"
											@click.stop="removeAdvancedFilter(i)"
										>
											×
										</button>
									</div>
								</div>

								<div
									class="flex items-center justify-between gap-2 border-t border-outline-gray-1 bg-surface-gray-1 px-3 py-2.5"
								>
									<Button
										variant="ghost"
										label="Add Filter"
										iconLeft="lucide-plus"
										@click.stop="addAdvancedFilter"
									/>
									<div class="flex gap-1.5">
										<Button
											v-if="advancedFilters.length"
											variant="ghost"
											label="Clear"
											@click.stop="clearAdvancedFilters"
										/>
										<Button
											variant="solid"
											label="Apply"
											@click.stop="applyAdvancedFilters"
										/>
									</div>
								</div>
							</div>
						</Teleport>
					</div>

					<div class="relative">
						<Button
							variant="ghost"
							icon="lucide-arrow-up-down"
							:tooltip="'Sort'"
							@click="showSort = !showSort"
						/>
						<Teleport to="body">
							<div v-if="showSort" class="fixed inset-0 z-[60]" @click="showSort = false">
								<div
									class="absolute right-4 top-28 z-[61] w-52 rounded-lg border border-outline-gray-2 bg-surface-modal p-1 shadow-xl"
									@click.stop
								>
									<button
										v-for="opt in sortOptions"
										:key="opt.value"
										type="button"
										class="flex w-full rounded px-3 py-2 text-left text-sm text-ink-gray-8 hover:bg-surface-gray-2"
										:class="sortBy === opt.value ? 'bg-surface-gray-2 font-medium' : ''"
										@click="
											sortBy = opt.value;
											showSort = false;
											reload();
										"
									>
										{{ opt.label }}
									</button>
								</div>
							</div>
						</Teleport>
					</div>

					<ColumnSettings
						:columns="editableColumns"
						:available-fields="columnFieldOptions"
						:is-default="columnsAreDefault"
						:hide-label="true"
						@update="onColumnsUpdate"
						@reset="resetColumnsToDefault"
					/>

					<Dropdown v-if="doctype" :options="listMenuOptions" placement="right">
						<Button variant="ghost" icon="lucide-more-horizontal" :tooltip="'More Options'" />
					</Dropdown>
				</div>
			</div>
		</section>

		<!-- Bulk actions -->
		<div
			v-if="selected.length"
			class="flex items-center gap-2 border-b border-outline-gray-2 bg-surface-gray-1 px-3 py-2 sm:px-5"
		>
			<span class="text-sm text-ink-gray-7">{{ selected.length }} selected</span>
			<Button size="sm" variant="outline" label="Assign" @click="showBulkAssign = true" />
			<Button size="sm" variant="outline" label="Export" @click="openExportDialog" />
			<Button size="sm" variant="outline" class="text-red-600" label="Delete" :loading="bulkBusy" @click="bulkDelete" />
			<Button size="sm" variant="ghost" label="Clear" @click="selected = []" />
		</div>

		<div
			class="relative flex min-h-0 flex-1 flex-col overflow-hidden [&>div]:min-h-0 [&>div]:overflow-hidden"
		>
			<ListView
				class="flex h-full min-h-0 flex-1 flex-col"
				:columns="listColumns"
				:rows="listRows"
				row-key="name"
				:options="{
					selectable: true,
					showTooltip: true,
					resizeColumn: true,
					getRowRoute: (row) => rowRoute(row),
					onRowClick: (row) => openDoc(row),
					emptyState: {
						title: `No ${title} Found`,
						description: 'Create a record or clear filters.',
					},
				}"
				@update:selections="onSelections"
			>
				<ListHeader class="mx-3 shrink-0 sm:mx-5" />
				<template v-if="listRows.length">
					<CustomListRows class="mx-3 min-h-0 flex-1 sm:mx-5" :rows="listRows">
						<template #default="{ column, item, row }">
							<ListRowItem :item="item" :column="column" :align="column.align">
								<template #default="{ label }">
									<div
										v-if="isTitleColumn(column.key)"
										class="flex min-w-0 items-center gap-2"
									>
										<Avatar
											size="sm"
											:label="String(label || row.name || '?')"
										/>
										<span class="truncate font-medium text-ink-gray-9">
											{{ label || "—" }}
										</span>
									</div>
									<div
										v-else-if="column.key === '_assign'"
										class="flex min-w-0 items-center"
										@click.stop
									>
										<MultipleAvatar :avatars="row._assign || []" />
									</div>
									<Badge
										v-else-if="column.key === 'docstatus'"
										variant="subtle"
										:label="docstatusLabel(row.docstatus)"
										:theme="docstatusTheme(row.docstatus)"
									/>
									<div
										v-else-if="
											['status', 'repair_status', 'approval_status', 'stock_status'].includes(
												column.key,
											)
										"
										class="inline-flex items-center gap-1.5 rounded-full bg-surface-gray-2 px-2.5 py-1 text-sm font-medium text-ink-gray-8"
									>
										<IndicatorIcon :class="parseStatusColor(label)" />
										<span>{{ label || "—" }}</span>
									</div>
									<Tooltip
										v-else-if="['modified', 'creation'].includes(column.key)"
										:text="formatExact(label)"
									>
										<span class="text-base text-ink-gray-6">{{ timeAgo(label) }}</span>
									</Tooltip>
									<span
										v-else-if="column.key === 'name'"
										class="font-medium text-ink-gray-9"
									>
										{{ label || "—" }}
									</span>
									<span v-else class="truncate text-base text-ink-gray-8">{{
										label || "—"
									}}</span>
								</template>
							</ListRowItem>
						</template>
					</CustomListRows>
				</template>
				<div
					v-else-if="!loading"
					class="flex flex-1 flex-col items-center justify-center gap-2 px-5 py-16 text-center"
				>
					<div class="text-lg font-medium text-ink-gray-8">No {{ title }} Found</div>
					<div class="max-w-sm text-sm text-ink-gray-5">
						Create a record or clear filters. ID series comes from DocType naming.
					</div>
					<div class="mt-2 flex gap-2">
						<Button
							v-if="creatable"
							variant="solid"
							label="Create"
							iconLeft="lucide-plus"
							@click="showCreate = true"
						/>
					</div>
				</div>
			</ListView>

			<div
				v-if="loading && !listRows.length"
				class="absolute inset-0 flex items-center justify-center bg-surface-white/60 text-sm text-ink-gray-5"
			>
				Loading...
			</div>

			<ListFooter
				v-model="pageLength"
				class="shrink-0 border-t border-outline-gray-2 bg-surface-white px-3 py-2 sm:px-5"
				:options="{ rowCount: listRows.length, totalCount }"
				@loadMore="loadMore"
			/>
		</div>

		<CreateDocModal
			v-if="showCreate"
			v-model="showCreate"
			:title="`Create ${singular}`"
			:doctype="doctype"
			:fields="createFieldsWithSeries"
			:create-method="createMethod"
			:detail-route="detailRoute"
			:detail-path="detailPath"
			@created="onCreated"
			@full-view="onFullView"
		/>

		<Dialog v-model="showExportDialog" :options="{ title: 'Export', size: 'sm' }">
			<template #body-content>
				<div class="flex flex-col gap-3">
					<FormControl
						v-model="exportType"
						type="select"
						label="Export Type"
						variant="outline"
						:options="[
							{ label: 'Excel', value: 'Excel' },
							{ label: 'CSV', value: 'CSV' },
						]"
					/>
					<label class="flex items-center gap-2 text-sm text-ink-gray-7">
						<input v-model="exportAll" type="checkbox" class="rounded border-outline-gray-3" />
						Export all matching records (current filters)
					</label>
					<p v-if="selected.length && !exportAll" class="text-p-sm text-ink-gray-5">
						{{ selected.length }} selected row(s) will be exported.
					</p>
				</div>
			</template>
			<template #actions>
				<Button variant="solid" class="w-full" label="Download" @click="runExport" />
			</template>
		</Dialog>

		<Dialog v-model="showBulkAssign" :options="{ title: 'Bulk Assign', size: 'md' }">
			<template #body-content>
				<div class="space-y-3">
					<p class="text-sm text-ink-gray-5">
						Assign {{ selected.length }} record(s) to one or more users.
					</p>
					<div v-if="bulkUsers.length" class="flex flex-wrap gap-1.5">
						<div
							v-for="(u, i) in bulkUsers"
							:key="u"
							class="flex items-center gap-1 rounded-full border border-outline-gray-2 bg-surface-gray-1 py-0.5 pl-2 pr-1 text-xs"
						>
							{{ u }}
							<button type="button" class="px-1 text-ink-gray-5" @click="bulkUsers.splice(i, 1)">
								×
							</button>
						</div>
					</div>
					<LinkField
						v-model="bulkAssignUser"
						doctype="User"
						label="Add User"
						placeholder="Search user…"
						:filters="{ enabled: 1 }"
						@update:modelValue="onBulkPick"
					/>
				</div>
			</template>
			<template #actions>
				<Button
					class="w-full"
					variant="solid"
					label="Assign"
					:loading="bulkBusy"
					:disabled="!bulkUsers.length"
					@click="bulkAssign"
				/>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
	Autocomplete,
	Avatar,
	Badge,
	Button,
	DatePicker,
	Dialog,
	Dropdown,
	FormControl,
	ListFooter,
	ListHeader,
	ListRowItem,
	ListView,
	Tooltip,
	call,
	confirmDialog,
	toast,
} from "frappe-ui";
import { useDebounceFn } from "@vueuse/core";
import Draggable from "vuedraggable";
import LayoutHeader from "@/components/LayoutHeader.vue";
import PageBreadcrumbs from "@/components/PageBreadcrumbs.vue";
import CreateDocModal from "@/components/CreateDocModal.vue";
import CustomListRows from "@/components/CustomListRows.vue";
import ColumnSettings from "@/components/ColumnSettings.vue";
import FilterSelect from "@/components/FilterSelect.vue";
import LinkField from "@/components/LinkField.vue";
import MultipleAvatar from "@/components/MultipleAvatar.vue";
import IndicatorIcon from "@/components/Icons/IndicatorIcon.vue";
import LucideList from "~icons/lucide/list";
import LucideKanban from "~icons/lucide/columns-3";
import { formatExact, parseStatusColor, timeAgo } from "@/utils/format";
import { exportQuery } from "@/utils/frappeDocs";

const props = defineProps({
	title: { type: String, required: true },
	singular: { type: String, default: "" },
	doctype: { type: String, required: true },
	fields: { type: Array, required: true },
	columns: { type: Array, required: true },
	quickFilters: { type: Array, default: () => [] },
	createFields: { type: Array, default: () => [] },
	createMethod: { type: String, default: "" },
	creatable: { type: Boolean, default: true },
	detailRoute: { type: String, default: "" },
	detailPath: { type: String, default: "" },
});

const router = useRouter();
const route = useRoute();
const loading = ref(false);
const meta = ref(null);
const showCreate = ref(false);
const showFilterPopover = ref(false);
const filterPanelRef = ref(null);
const showSort = ref(false);
const showBulkAssign = ref(false);
const showExportDialog = ref(false);
const exportType = ref("Excel");
const exportAll = ref(false);
const bulkAssignUser = ref("");
const bulkUsers = ref([]);
const bulkBusy = ref(false);
const search = ref("");
const sortBy = ref("modified desc");
const pageLength = ref(20);
const totalCount = ref(0);
const rawRows = ref([]);
const selected = ref([]);
const filterValues = reactive({});
const advancedFilters = ref([]);
const customizeQuickFilter = ref(false);
const draftQuickFilters = ref([]);
const customColumns = ref(null);
const customQuickFilters = ref(null);
const columnsHydrated = ref(false);

function storageKey(kind) {
	return `ss-list-${kind}:${props.doctype}`;
}

function loadStored(kind) {
	try {
		const raw = localStorage.getItem(storageKey(kind));
		return raw ? JSON.parse(raw) : null;
	} catch {
		return null;
	}
}

function saveStored(kind, value) {
	try {
		localStorage.setItem(storageKey(kind), JSON.stringify(value));
	} catch {
		/* ignore quota */
	}
}

function clearStored(kind) {
	try {
		localStorage.removeItem(storageKey(kind));
	} catch {
		/* ignore */
	}
}

function cloneCols(cols) {
	return (cols || []).map((c) => ({
		label: c.key === "name" ? "ID" : c.label,
		key: c.key,
		width: c.width || (c.key === "name" ? "11rem" : "12rem"),
		align: c.align || "left",
		fieldtype: c.fieldtype,
	}));
}

const viewOptions = computed(() => [
	{
		group: "Views",
		hideLabel: true,
		items: [
			{
				label: "List",
				icon: LucideList,
				onClick: () => {},
			},
			{
				label: "Board (soon)",
				icon: LucideKanban,
				onClick: () => {},
			},
		],
	},
]);

const operatorOptions = [
	{ label: "Equals", value: "=" },
	{ label: "Like", value: "like" },
	{ label: "Not Equals", value: "!=" },
	{ label: "Greater Than", value: ">" },
	{ label: "Less Than", value: "<" },
];

const defaultQuickFilters = computed(() => {
	if (meta.value?.quick_filters?.length) return meta.value.quick_filters;
	return props.quickFilters || [];
});

const effectiveFilters = computed(() => {
	if (customQuickFilters.value?.length) return customQuickFilters.value;
	return defaultQuickFilters.value || [];
});

/** Cap bar filters so the toolbar stays usable; rest stay in Filter popover */
const visibleQuickFilters = computed(() => (effectiveFilters.value || []).slice(0, 6));

const defaultColumnsBase = computed(() => {
	if (meta.value?.columns?.length) return meta.value.columns;
	return props.columns || [];
});

const columnsAreDefault = computed(() => !customColumns.value);

const columnFieldOptions = computed(() => {
	const fromMeta = meta.value?.all_fields || [];
	const base = fromMeta.length
		? [...fromMeta]
		: (props.fields || [])
				.filter((f) => typeof f === "string")
				.map((f) => ({ label: f, value: f, fieldname: f, fieldtype: "Data", options: "" }));
	if (!base.some((f) => f.value === "_assign")) {
		base.push({
			label: "Assigned To",
			value: "_assign",
			fieldname: "_assign",
			fieldtype: "Data",
			options: "",
		});
	}
	return base;
});

const editableColumns = computed(() => {
	if (customColumns.value?.length) return customColumns.value;
	return cloneCols(defaultColumnsBase.value);
});

const listColumns = computed(() => {
	const source = editableColumns.value;
	const cols = source.map((c) => ({
		label: c.key === "name" ? c.label || "ID" : c.label,
		key: c.key === "assigned_to" ? "_assign" : c.key,
		width: c.width || (c.key === "name" ? "11rem" : "12rem"),
		align: c.align || "left",
		fieldtype: c.fieldtype,
	}));
	cols.forEach((c) => {
		if (c.key === "_assign") {
			c.label = c.label || "Assigned To";
			c.width = c.width || "10rem";
		}
	});
	// Defaults only: inject submit status + assignee until user customizes columns
	if (!customColumns.value) {
		if (meta.value?.is_submittable && !cols.some((c) => c.key === "docstatus")) {
			cols.splice(Math.min(1, cols.length), 0, {
				label: "DocStatus",
				key: "docstatus",
				width: "8rem",
				align: "left",
			});
		}
		if (!cols.some((c) => c.key === "_assign")) {
			cols.push({ label: "Assigned To", key: "_assign", width: "10rem", align: "left" });
		}
	}
	return cols;
});

function hydrateListPrefs() {
	const savedCols = loadStored("columns");
	customColumns.value = Array.isArray(savedCols) && savedCols.length ? savedCols : null;
	const savedQf = loadStored("quick-filters");
	customQuickFilters.value = Array.isArray(savedQf) && savedQf.length ? savedQf : null;
	columnsHydrated.value = true;
	(effectiveFilters.value || []).forEach((f) => {
		if (!(f.fieldname in filterValues)) filterValues[f.fieldname] = "";
	});
}

function onColumnsUpdate({ columns, reload: shouldReload }) {
	customColumns.value = (columns || []).map((c) => ({ ...c }));
	saveStored("columns", customColumns.value);
	if (shouldReload) reload();
}

function resetColumnsToDefault() {
	customColumns.value = null;
	clearStored("columns");
	reload();
}

const quickFilterAddOptions = computed(() => {
	const used = new Set((draftQuickFilters.value || []).map((f) => f.fieldname));
	const allow = new Set([
		"Link",
		"Select",
		"Data",
		"Date",
		"Datetime",
		"Check",
		"Int",
		"Float",
		"Currency",
		"Dynamic Link",
	]);
	return (columnFieldOptions.value || [])
		.filter((f) => !used.has(f.value) && allow.has(f.fieldtype))
		.map((f) => ({
			label: f.label,
			value: f.value,
			fieldtype: f.fieldtype,
			options: f.options,
			select_options: f.select_options,
		}));
});

function startCustomizeQuickFilters() {
	draftQuickFilters.value = (effectiveFilters.value || []).map((f) => ({ ...f }));
	customizeQuickFilter.value = true;
}

function cancelCustomizeQuickFilters() {
	customizeQuickFilter.value = false;
	draftQuickFilters.value = [];
}

function removeDraftQuickFilter(filter) {
	draftQuickFilters.value = draftQuickFilters.value.filter(
		(f) => f.fieldname !== filter.fieldname,
	);
}

function onAddQuickFilter(option) {
	if (!option?.value) return;
	if (draftQuickFilters.value.some((f) => f.fieldname === option.value)) return;
	const type = option.fieldtype || "Data";
	const row = {
		fieldname: option.value,
		label: option.label || option.value,
		type,
		options: option.options || "",
	};
	if (type === "Select" && option.select_options) {
		row.options = option.select_options;
	}
	draftQuickFilters.value.push(row);
}

function saveQuickFilters() {
	customQuickFilters.value = draftQuickFilters.value.map((f) => ({ ...f }));
	saveStored("quick-filters", customQuickFilters.value);
	customQuickFilters.value.forEach((f) => {
		if (!(f.fieldname in filterValues)) filterValues[f.fieldname] = "";
	});
	customizeQuickFilter.value = false;
	draftQuickFilters.value = [];
	toast.success("Quick filters saved");
}

const createFieldsWithSeries = computed(() => {
	const fields = [...(props.createFields || [])];
	if (meta.value?.has_naming_series && meta.value.naming_series_options?.length) {
		if (!fields.find((f) => f.fieldname === "naming_series")) {
			fields.unshift({
				fieldname: "naming_series",
				label: "Series",
				fieldtype: "Select",
				reqd: 1,
				default: meta.value.naming_series_options[0],
				options: meta.value.naming_series_options.map((o) => ({ label: o, value: o })),
			});
		}
	}
	return fields;
});

function selectOptionsFor(filter) {
	const opts = filter?.options ?? filter?.select_options ?? [];
	if (typeof opts === "string") {
		return opts
			.split("\n")
			.map((o) => o.trim())
			.filter(Boolean)
			.map((o) => ({ label: o, value: o }));
	}
	if (!Array.isArray(opts) || !opts.length) return [];
	if (typeof opts[0] === "object") {
		return opts
			.filter((o) => o && o.value !== "" && o.value != null)
			.map((o) => ({ label: o.label || String(o.value), value: String(o.value) }));
	}
	return opts
		.filter((o) => o !== "" && o != null)
		.map((o) => ({ label: String(o), value: String(o) }));
}

/** @deprecated alias — advanced filter / callers */
function selectOptions(filter) {
	return [{ label: "All", value: "" }, ...selectOptionsFor(filter)];
}

const filterFieldOptions = computed(() => {
	const opts = effectiveFilters.value.map((f) => ({
		label: f.label,
		value: f.fieldname,
	}));
	opts.unshift({ label: "ID", value: "name" });
	listColumns.value.forEach((c) => {
		if (c.key && c.key !== "_assign" && !opts.find((o) => o.value === c.key)) {
			opts.push({ label: c.label, value: c.key });
		}
	});
	return opts;
});

const sortOptions = computed(() => {
	const opts = [
		{ label: "Modified (newest)", value: "modified desc" },
		{ label: "Modified (oldest)", value: "modified asc" },
		{ label: "ID A–Z", value: "name asc" },
		{ label: "ID Z–A", value: "name desc" },
	];
	listColumns.value.forEach((c) => {
		if (c.key && c.key !== "name" && c.key !== "modified" && c.key !== "_assign") {
			opts.push(
				{ label: `${c.label} A–Z`, value: `${c.key} asc` },
				{ label: `${c.label} Z–A`, value: `${c.key} desc` },
			);
		}
	});
	return opts;
});

const searchFields = computed(() => {
	const keys = ["name"];
	listColumns.value.forEach((c) => {
		if (
			c.key &&
			!keys.includes(c.key) &&
			!["status", "qty", "rating", "docstatus", "_assign"].includes(c.key)
		) {
			keys.push(c.key);
		}
	});
	return keys.slice(0, 6);
});

const requestFields = computed(() => {
	const keys = new Set(["name", "docstatus", "modified"]);
	listColumns.value.forEach((c) => {
		if (c.key && c.key !== "_assign") keys.add(c.key);
	});
	(meta.value?.fields || props.fields || []).forEach((f) => {
		if (typeof f === "string") keys.add(f);
	});
	return [...keys];
});

const listRows = computed(() =>
	rawRows.value.map((row) => {
		const mapped = {
			name: row.name,
			docstatus: row.docstatus,
			_assign: Array.isArray(row._assign) ? row._assign : [],
		};
		listColumns.value.forEach((c) => {
			if (c.key === "_assign") return;
			mapped[c.key] = row[c.key] ?? (c.key === "docstatus" ? row.docstatus : "");
		});
		return mapped;
	}),
);

function docstatusLabel(v) {
	const n = Number(v);
	if (n === 1) return "Submitted";
	if (n === 2) return "Cancelled";
	return "Draft";
}

function docstatusTheme(v) {
	const n = Number(v);
	if (n === 1) return "green";
	if (n === 2) return "red";
	return "orange";
}

function statusTheme(label) {
	const v = (label || "").toLowerCase();
	if (["draft", "planned", "pending", "waiting spare"].includes(v)) return "orange";
	if (["completed", "closed", "resolved", "active", "approved", "issued"].includes(v))
		return "green";
	if (["cancelled", "rejected"].includes(v)) return "red";
	return "gray";
}

function isOpenLike(label) {
	const v = (label || "").toLowerCase();
	return ["open", "failed", "overdue", "breached"].includes(v);
}

function isTitleColumn(key) {
	return ["subject", "customer_name", "title", "full_name", "lead_name", "item_name"].includes(key);
}

function buildFilters() {
	const filters = {};
	Object.entries(filterValues).forEach(([key, val]) => {
		if (val) filters[key] = val;
	});
	for (const f of advancedFilters.value) {
		if (!f.fieldname || f.value === "" || f.value == null) continue;
		if (f.operator === "like") filters[f.fieldname] = ["like", `%${f.value}%`];
		else if (f.operator === "!=") filters[f.fieldname] = ["!=", f.value];
		else if (f.operator === ">") filters[f.fieldname] = [">", f.value];
		else if (f.operator === "<") filters[f.fieldname] = ["<", f.value];
		else filters[f.fieldname] = f.value;
	}
	return filters;
}

function addAdvancedFilter() {
	advancedFilters.value.push({
		_id: `f-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
		fieldname: filterFieldOptions.value[0]?.value || "name",
		operator: "like",
		value: "",
	});
}

function removeAdvancedFilter(i) {
	advancedFilters.value.splice(i, 1);
	// Keep popover open; apply when user clicks Apply
}

function clearAdvancedFilters() {
	advancedFilters.value = [];
	showFilterPopover.value = false;
	reload();
}

function applyAdvancedFilters() {
	showFilterPopover.value = false;
	reload();
}

function closeFilterPopover() {
	showFilterPopover.value = false;
}

let ignoreFilterOutside = false;
function toggleFilterPopover() {
	if (showFilterPopover.value) {
		showFilterPopover.value = false;
		return;
	}
	showFilterPopover.value = true;
	ignoreFilterOutside = true;
	if (!advancedFilters.value.length) addAdvancedFilter();
	// Ignore the same click that opened the panel (and its synthetic follow-ups)
	setTimeout(() => {
		ignoreFilterOutside = false;
	}, 0);
}

function onAdvancedFilterOutside(e) {
	if (!showFilterPopover.value || ignoreFilterOutside) return;
	const t = e.target;
	if (!(t instanceof Element)) return;
	if (filterPanelRef.value?.contains(t)) return;
	if (t.closest(".ss-filter-select-panel")) return;
	if (t.closest("[data-ss-filter-btn]")) return;
	showFilterPopover.value = false;
}

const debouncedReload = useDebounceFn(() => reload(), 400);

async function loadMeta() {
	try {
		meta.value = await call("swiftservice.api.get_doctype_list_meta", {
			doctype: props.doctype,
		});
		hydrateListPrefs();
		(meta.value?.quick_filters || []).forEach((f) => {
			if (!(f.fieldname in filterValues)) filterValues[f.fieldname] = "";
		});
		props.quickFilters.forEach((f) => {
			if (!(f.fieldname in filterValues)) filterValues[f.fieldname] = "";
		});
		if (meta.value?.sort_field) {
			sortBy.value = `${meta.value.sort_field} ${meta.value.sort_order || "desc"}`;
		}
	} catch (e) {
		meta.value = null;
		hydrateListPrefs();
		props.quickFilters.forEach((f) => {
			filterValues[f.fieldname] = filterValues[f.fieldname] ?? "";
		});
	}
}

/** Seed filters from URL query (ERPNext connection → filtered list) */
function applyQueryFilters() {
	const q = route.query || {};
	let changed = false;
	for (const [key, raw] of Object.entries(q)) {
		if (raw == null || raw === "") continue;
		const val = Array.isArray(raw) ? raw[0] : String(raw);
		if (!(key in filterValues)) filterValues[key] = "";
		if (filterValues[key] !== val) {
			filterValues[key] = val;
			changed = true;
		}
		// Also mirror as advanced filter so Filter badge shows
		const exists = advancedFilters.value.some((f) => f.fieldname === key && f.value === val);
		if (!exists) {
			advancedFilters.value.push({
				_id: `f-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
				fieldname: key,
				operator: "=",
				value: val,
			});
			changed = true;
		}
	}
	return changed;
}

function onSelections(set) {
	selected.value = set ? [...set] : [];
}

async function reload() {
	loading.value = true;
	try {
		const res = await call("swiftservice.api.get_list", {
			doctype: props.doctype,
			fields: requestFields.value,
			filters: buildFilters(),
			order_by: sortBy.value,
			limit_page_length: pageLength.value,
			search: search.value || null,
			search_fields: searchFields.value,
		});
		rawRows.value = res?.data || res || [];
		totalCount.value = res?.total ?? rawRows.value.length;
		selected.value = [];
	} finally {
		loading.value = false;
	}
}

async function loadMore() {
	pageLength.value = pageLength.value + 20;
	await reload();
}

async function bulkDelete() {
	if (!selected.value.length) return;
	confirmDialog({
		title: "Delete records?",
		message: `Delete <strong>${selected.value.length}</strong> record(s)? This cannot be undone.`,
		onConfirm: async ({ hideDialog }) => {
			bulkBusy.value = true;
			try {
				const res = await call("swiftservice.api.bulk_delete", {
					doctype: props.doctype,
					names: selected.value,
				});
				if (res?.errors?.length) {
					toast.error(res.errors.join("<br>"));
				} else {
					toast.success("Deleted");
				}
				await reload();
				hideDialog();
			} catch (e) {
				toast.error(e?.messages?.[0] || e?.message || "Delete failed");
			} finally {
				bulkBusy.value = false;
			}
		},
	});
}

function onBulkPick(user) {
	if (!user) return;
	if (!bulkUsers.value.includes(user)) bulkUsers.value.push(user);
	bulkAssignUser.value = "";
}

async function bulkAssign() {
	if (!bulkUsers.value.length || !selected.value.length) return;
	bulkBusy.value = true;
	try {
		await call("swiftservice.api.bulk_assign", {
			doctype: props.doctype,
			names: selected.value,
			users: bulkUsers.value,
		});
		showBulkAssign.value = false;
		bulkUsers.value = [];
		bulkAssignUser.value = "";
		toast.success("Assigned");
		await reload();
	} catch (e) {
		toast.error(e?.messages?.[0] || e?.message || "Assign failed");
	} finally {
		bulkBusy.value = false;
	}
}

const listMenuOptions = computed(() => [
	{
		group: "Data",
		hideLabel: true,
		items: [
			{
				label: "Import",
				icon: "lucide-download",
				onClick: () =>
					router.push({
						name: "NewDataImport",
						params: { doctype: props.doctype },
					}),
			},
			{
				label: "Export",
				icon: "lucide-upload",
				onClick: () => openExportDialog(),
			},
			{
				label: "Customize Quick Filters",
				icon: "lucide-list-filter",
				onClick: () => startCustomizeQuickFilters(),
			},
		],
	},
]);

function openExportDialog() {
	exportAll.value = !selected.value.length;
	showExportDialog.value = true;
}

function runExport() {
	const fields = listColumns.value.map((c) => c.key).filter(Boolean);
	if (!fields.includes("name")) fields.unshift("name");

	const page_length = exportAll.value
		? Math.max(totalCount.value || pageLength.value, pageLength.value)
		: pageLength.value;

	exportQuery({
		doctype: props.doctype,
		fields,
		filters: buildFilters(),
		order_by: sortBy.value,
		page_length,
		selected_items: exportAll.value ? [] : selected.value,
		file_format_type: exportType.value,
		title: props.title || props.doctype,
	});

	showExportDialog.value = false;
	exportAll.value = false;
	exportType.value = "Excel";
}

function rowRoute(row) {
	const name = row?.name;
	if (!name) return null;
	if (props.detailPath) {
		// Keep path relative to router base (/swiftservice)
		return `${props.detailPath}/${encodeURIComponent(name)}`;
	}
	if (props.detailRoute) {
		return { name: props.detailRoute, params: { docname: name } };
	}
	return null;
}

function openDoc(row) {
	const to = rowRoute(row);
	if (to) router.push(to);
}

function openFullForm() {
	if (props.detailPath) {
		router.push(`${props.detailPath}/new`);
		return;
	}
	if (props.detailRoute) {
		router.push({ name: props.detailRoute, params: { docname: "new" } });
	}
}

function onFullView() {
	showCreate.value = false;
	openFullForm();
}

function onCreated(result) {
	showCreate.value = false;
	const name = result?.name;
	if (name && props.detailPath) {
		router.push(`${props.detailPath}/${encodeURIComponent(name)}`);
		return;
	}
	if (name && props.detailRoute) {
		router.push({ name: props.detailRoute, params: { docname: name } });
		return;
	}
	reload();
}

function onDocClick(e) {
	// Filter popover is closed via onAdvancedFilterOutside — do not close it here.
	// Teleported FilterSelect options unmount on mousedown; the following click
	// would otherwise hit the document and kill the whole filter panel.
	const t = e?.target;
	if (t instanceof Element) {
		if (t.closest(".ss-advanced-filter-panel") || t.closest(".ss-filter-select-panel")) {
			return;
		}
	}
	showSort.value = false;
}

watch(pageLength, () => reload());
watch(
	() => route.query,
	() => {
		applyQueryFilters();
		reload();
	},
);
onMounted(async () => {
	document.addEventListener("click", onDocClick);
	document.addEventListener("pointerdown", onAdvancedFilterOutside, true);
	await loadMeta();
	applyQueryFilters();
	await reload();
});
onUnmounted(() => {
	document.removeEventListener("click", onDocClick);
	document.removeEventListener("pointerdown", onAdvancedFilterOutside, true);
});

defineExpose({ reload });
</script>
