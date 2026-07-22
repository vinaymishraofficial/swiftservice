<template>
	<div
		class="grid"
		:class="
			variant === 'home'
				? 'grid-cols-3 gap-x-2 gap-y-4 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-7 lg:gap-y-5'
				: 'grid-cols-3 gap-x-3 gap-y-5 sm:grid-cols-4 sm:gap-x-4 sm:gap-y-6'
		"
	>
		<button
			v-for="mod in items"
			:key="mod.id"
			type="button"
			class="group flex flex-col items-center gap-1.5 rounded-lg text-center outline-none transition hover:bg-surface-gray-2 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
			:class="[
				variant === 'home' ? 'px-1 py-2.5' : 'px-1.5 py-2',
				mod.id === activeId ? 'bg-surface-selected' : '',
			]"
			@click="$emit('select', mod)"
		>
			<div
				class="flex items-center justify-center rounded-xl bg-surface-gray-3 text-ink-gray-8 transition group-hover:bg-surface-gray-4"
				:class="variant === 'home' ? 'size-12 sm:size-[3.25rem]' : 'size-11 sm:size-12'"
			>
				<component
					:is="mod.icon"
					:class="variant === 'home' ? 'size-5 sm:size-6' : 'size-5 sm:size-[22px]'"
					stroke-width="1.75"
				/>
			</div>
			<div
				class="line-clamp-2 font-medium leading-snug text-ink-gray-8"
				:class="
					variant === 'home'
						? 'max-w-[5.5rem] text-[12px] sm:max-w-[6.5rem] sm:text-[13px]'
						: 'max-w-[4.75rem] text-[12px] sm:max-w-[5.5rem] sm:text-[13px]'
				"
			>
				{{ shortLabel(mod.label) }}
			</div>
		</button>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { modules } from "@/config/modules";

const props = defineProps({
	activeId: { type: String, default: "" },
	excludeHome: { type: Boolean, default: true },
	variant: { type: String, default: "default" },
});

defineEmits(["select"]);

const SHORT = {
	"Installed Base": "Installed Base",
	"Service Requests": "Requests",
	"Field Operations": "Field",
	"Factory & RMA": "Factory",
	"Closure & Billing": "Closure",
	"Contracts & PM": "Contracts",
};

function shortLabel(label) {
	if (props.variant !== "home") return label;
	return SHORT[label] || label;
}

const items = computed(() =>
	modules.filter((m) => {
		if (m.showInGrid === false) return false;
		if (props.excludeHome && m.id === "home") return false;
		return true;
	}),
);
</script>
