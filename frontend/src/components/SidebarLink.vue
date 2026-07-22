<template>
	<button
		type="button"
		class="mx-2 my-[1.5px] flex h-8 w-[calc(100%-1rem)] cursor-pointer items-center rounded text-ink-gray-8 duration-200 focus:outline-none"
		:class="isActive ? 'bg-surface-white shadow-sm' : 'hover:bg-surface-gray-2'"
		@click.stop.prevent="go"
	>
		<div
			class="flex w-full items-center truncate"
			:class="isCollapsed ? 'justify-center p-1' : 'gap-2 px-2 py-1.5'"
		>
			<span class="grid size-4 shrink-0 place-items-center text-ink-gray-7">
				<component :is="icon" v-if="icon" class="size-4" />
			</span>
			<span v-if="!isCollapsed" class="truncate text-sm">{{ label }}</span>
		</div>
	</button>
</template>

<script setup>
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const props = defineProps({
	icon: { type: [Object, Function, String], default: null },
	label: { type: String, default: "" },
	to: { type: String, required: true },
	isCollapsed: { type: Boolean, default: false },
});

const router = useRouter();
const route = useRoute();

function go() {
	const path = props.to.startsWith("/") ? props.to : `/${props.to}`;
	if (route.path !== path) {
		router.push(path).catch(() => {});
	}
}

const isActive = computed(() => {
	const path = props.to.startsWith("/") ? props.to : `/${props.to}`;
	if (path === "/dashboard") return route.path === "/dashboard" || route.path === "/";
	return route.path === path || route.path.startsWith(`${path}/`);
});
</script>
