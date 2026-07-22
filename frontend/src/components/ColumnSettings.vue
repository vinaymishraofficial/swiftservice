<template>
	<Popover placement="bottom-end">
		<template #target="{ togglePopover }">
			<Button
				:variant="hideLabel ? 'ghost' : 'outline'"
				:label="hideLabel ? undefined : 'Columns'"
				:tooltip="hideLabel ? 'Columns' : undefined"
				@click="togglePopover()"
			>
				<template v-if="hideLabel" #icon>
					<ColumnsIcon class="h-4 w-4" />
				</template>
				<template v-else #prefix>
					<ColumnsIcon class="h-4 w-4" />
				</template>
			</Button>
		</template>
		<template #body>
			<div
				class="my-2 min-w-52 rounded-lg bg-surface-modal p-1.5 shadow-2xl ring-1 ring-black/5"
			>
				<div v-if="!edit">
					<Draggable
						:list="localColumns"
						item-key="key"
						handle=".ss-col-drag"
						class="list-group"
						@end="emitColumns"
					>
						<template #item="{ element }">
							<div
								class="flex cursor-default items-center justify-between gap-4 rounded px-2 py-1.5 text-sm text-ink-gray-8 hover:bg-surface-gray-2"
							>
								<div class="flex min-w-0 items-center gap-2">
									<span class="ss-col-drag cursor-grab text-ink-gray-5">
										<DragIcon class="h-3.5 w-3.5" />
									</span>
									<span class="truncate">{{ element.label }}</span>
								</div>
								<div class="flex shrink-0 items-center gap-0.5">
									<Button
										variant="ghost"
										class="!h-5 !w-5 !p-1"
										@click="editColumn(element)"
									>
										<template #icon>
											<EditIcon class="h-3.5 w-3.5" />
										</template>
									</Button>
									<Button
										variant="ghost"
										class="!h-5 !w-5 !p-1"
										:disabled="localColumns.length <= 1"
										@click="removeColumn(element)"
									>
										<template #icon>
											<span class="text-base leading-none text-ink-gray-6">×</span>
										</template>
									</Button>
								</div>
							</div>
						</template>
					</Draggable>

					<div class="mt-1.5 flex flex-col gap-1 border-t border-outline-gray-2 pt-1.5">
						<Autocomplete
							:options="addableFields"
							placeholder="Add Column"
							@update:modelValue="onAddField"
						>
							<template #target="{ togglePopover }">
								<Button
									class="w-full !justify-start !text-ink-gray-5"
									variant="ghost"
									label="Add Column"
									iconLeft="lucide-plus"
									@click="togglePopover()"
								/>
							</template>
						</Autocomplete>
						<Button
							v-if="!isDefault"
							class="w-full !justify-start !text-ink-gray-5"
							variant="ghost"
							label="Reset to Default"
							iconLeft="lucide-rotate-ccw"
							@click="resetToDefault"
						/>
					</div>
				</div>

				<div v-else class="space-y-3 px-2 py-1.5">
					<FormControl
						v-model="editDraft.label"
						type="text"
						size="md"
						label="Label"
						class="w-52"
					/>
					<FormControl
						v-model="editDraft.width"
						type="text"
						size="md"
						label="Width"
						class="w-52"
						placeholder="10rem"
						description="e.g. 3, 30px, 10rem"
					/>
					<div class="flex gap-2 border-t border-outline-gray-2 pt-2">
						<Button
							variant="subtle"
							label="Cancel"
							class="flex-1"
							@click="cancelEdit"
						/>
						<Button
							variant="solid"
							label="Update"
							class="flex-1"
							@click="saveEdit"
						/>
					</div>
				</div>
			</div>
		</template>
	</Popover>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Autocomplete, Button, FormControl, Popover } from "frappe-ui";
import Draggable from "vuedraggable";
import ColumnsIcon from "@/components/Icons/ColumnsIcon.vue";
import DragIcon from "@/components/Icons/DragIcon.vue";
import EditIcon from "@/components/Icons/EditIcon.vue";

const props = defineProps({
	columns: { type: Array, default: () => [] },
	availableFields: { type: Array, default: () => [] },
	isDefault: { type: Boolean, default: true },
	hideLabel: { type: Boolean, default: true },
});

const emit = defineEmits(["update", "reset"]);

const localColumns = ref([]);
const edit = ref(false);
const editDraft = ref({ key: "", label: "", width: "10rem", oldLabel: "", oldWidth: "" });

watch(
	() => props.columns,
	(cols) => {
		localColumns.value = (cols || []).map((c) => ({ ...c }));
	},
	{ immediate: true, deep: true },
);

const addableFields = computed(() => {
	const used = new Set(localColumns.value.map((c) => c.key));
	return (props.availableFields || [])
		.filter((f) => f.value && !used.has(f.value))
		.map((f) => ({
			label: f.label,
			value: f.value,
			fieldtype: f.fieldtype,
			options: f.options,
		}));
});

function emitColumns(reload = true) {
	emit("update", {
		columns: localColumns.value.map((c) => ({ ...c })),
		reload,
	});
}

function removeColumn(col) {
	if (localColumns.value.length <= 1) return;
	localColumns.value = localColumns.value.filter((c) => c.key !== col.key);
	emitColumns(true);
}

function editColumn(col) {
	edit.value = true;
	editDraft.value = {
		key: col.key,
		label: col.label,
		width: col.width || "10rem",
		oldLabel: col.label,
		oldWidth: col.width || "10rem",
	};
}

function cancelEdit() {
	edit.value = false;
}

function saveEdit() {
	const idx = localColumns.value.findIndex((c) => c.key === editDraft.value.key);
	if (idx >= 0) {
		localColumns.value[idx].label = editDraft.value.label;
		localColumns.value[idx].width = editDraft.value.width || "10rem";
	}
	edit.value = false;
	emitColumns(false);
}

function onAddField(option) {
	if (!option?.value) return;
	const align = ["Float", "Int", "Percent", "Currency", "Duration"].includes(option.fieldtype)
		? "right"
		: "left";
	localColumns.value.push({
		label: option.label,
		key: option.value,
		width: "10rem",
		align,
		fieldtype: option.fieldtype,
	});
	emitColumns(true);
}

function resetToDefault() {
	edit.value = false;
	emit("reset");
}
</script>
