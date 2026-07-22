<template>
	<div>
		<button
			type="button"
			class="flex items-center rounded-md duration-300 ease-in-out"
			:class="
				isCollapsed
					? 'mx-auto h-8 w-8 justify-center px-0'
					: open
						? 'h-11 w-full bg-surface-white px-2 py-1.5 shadow-sm'
						: 'h-11 w-full px-2 py-1.5 hover:bg-surface-gray-3'
			"
			@click="open = true"
		>
			<div
				class="ss-module-tile flex size-8 shrink-0 items-center justify-center rounded-[10px] text-white"
			>
				<component :is="current.icon" class="size-4 text-white" stroke-width="1.75" />
			</div>
			<div
				class="flex flex-1 flex-col truncate text-left duration-300 ease-in-out"
				:class="
					isCollapsed
						? 'ml-0 w-0 overflow-hidden opacity-0'
						: 'ml-2 w-auto opacity-100'
				"
			>
				<div class="truncate text-xs font-medium uppercase tracking-wide text-ink-gray-5">
					SwiftService
				</div>
				<div class="truncate text-sm font-medium leading-tight text-ink-gray-9">
					{{ current.label }}
				</div>
			</div>
			<div
				class="duration-300 ease-in-out"
				:class="
					isCollapsed
						? 'ml-0 w-0 overflow-hidden opacity-0'
						: 'ml-1 w-auto opacity-100'
				"
			>
				<span class="lucide-layout-grid size-4 text-ink-gray-5" aria-hidden="true" />
			</div>
		</button>

		<ModulePickerModal
			v-model="open"
			:module-id="moduleId"
			@update:moduleId="(id) => $emit('update:moduleId', id)"
		/>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import ModulePickerModal from "@/components/ModulePickerModal.vue";
import { getModuleById } from "@/config/modules";

const props = defineProps({
	isCollapsed: { type: Boolean, default: false },
	moduleId: { type: String, required: true },
});

defineEmits(["update:moduleId"]);

const open = ref(false);
const current = computed(() => getModuleById(props.moduleId));
</script>

<style scoped>
.ss-module-tile {
	background-color: rgb(var(--ss-pink-500));
}
</style>
