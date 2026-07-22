<template>
	<Teleport to="body">
		<div
			v-if="modelValue"
			class="fixed inset-0 z-[300] flex items-center justify-center p-4 sm:p-6"
			role="dialog"
			aria-modal="true"
			aria-labelledby="ss-module-picker-title"
		>
			<div
				class="absolute inset-0 bg-[#160f18]/72 backdrop-blur-[3px]"
				@click="close"
			/>

			<div class="relative z-10 w-full max-w-[28rem] animate-[ss-picker-in_160ms_ease-out]">
				<header class="mb-3 flex flex-col items-center gap-2">
					<img
						v-if="brand.logo"
						:src="brand.logo"
						alt=""
						class="size-10 rounded-[12px] object-cover shadow-lg ring-2 ring-white/25"
					/>
					<h2
						id="ss-module-picker-title"
						class="text-center text-xl font-semibold tracking-tight text-white"
					>
						{{ brand.name || "SwiftService" }}
					</h2>
				</header>

				<div
					class="rounded-2xl bg-white px-5 py-6 shadow-[0_24px_64px_rgba(0,0,0,0.35)] sm:px-6 sm:py-7"
				>
					<ModuleIconGrid
						:active-id="moduleId"
						:exclude-home="true"
						@select="onSelect"
					/>
				</div>

				<div class="mt-3 flex justify-center">
					<button
						type="button"
						class="rounded-full px-4 py-1.5 text-sm font-medium text-white/95 transition hover:bg-white/15"
						@click="close"
					>
						Close
					</button>
				</div>
			</div>
		</div>
	</Teleport>
</template>

<script setup>
import { onBeforeUnmount, watch } from "vue";
import { useRouter } from "vue-router";
import ModuleIconGrid from "@/components/ModuleIconGrid.vue";
import { setStoredModuleId } from "@/config/modules";
import { useSettings } from "@/stores/settings";

defineProps({
	moduleId: { type: String, default: "home" },
});

const modelValue = defineModel({ type: Boolean, default: false });
const emit = defineEmits(["update:moduleId"]);
const router = useRouter();
const { brand } = useSettings();

function close() {
	modelValue.value = false;
}

function onSelect(mod) {
	setStoredModuleId(mod.id);
	emit("update:moduleId", mod.id);
	modelValue.value = false;
	if (mod.homeRoute) {
		router.push(mod.homeRoute);
	}
}

function onKey(e) {
	if (e.key === "Escape") close();
}

watch(modelValue, (open) => {
	if (open) document.addEventListener("keydown", onKey);
	else document.removeEventListener("keydown", onKey);
});

onBeforeUnmount(() => document.removeEventListener("keydown", onKey));
</script>

<style>
@keyframes ss-picker-in {
	from {
		opacity: 0;
		transform: translateY(6px) scale(0.98);
	}
	to {
		opacity: 1;
		transform: translateY(0) scale(1);
	}
}
</style>
