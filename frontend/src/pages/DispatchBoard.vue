<template>
	<div class="flex h-full flex-col overflow-hidden">
		<LayoutHeader>
			<template #left-header>
				<div class="text-lg font-medium text-ink-gray-9">Dispatch Board</div>
			</template>
			<template #right-header>
				<DatePicker
					class="w-40"
					placeholder="Select date"
					v-model="date"
					@update:modelValue="load"
				/>
				<Button label="Refresh" variant="outline" :loading="loading" @click="load" />
			</template>
		</LayoutHeader>

		<div class="flex-1 overflow-auto px-3 py-4 sm:px-5">
			<div v-if="!Object.keys(columns).length" class="text-sm text-ink-gray-5">
				No visits for this date.
			</div>
			<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
				<div
					v-for="(visits, engineer) in columns"
					:key="engineer"
					class="rounded-xl border border-outline-gray-2 bg-surface-white p-4"
				>
					<div class="mb-3 text-sm font-semibold text-ink-gray-9">{{ engineer }}</div>
					<div class="space-y-2">
						<button
							v-for="v in visits"
							:key="v.name"
							class="block w-full rounded-lg border border-outline-gray-2 px-3 py-2 text-left hover:bg-surface-gray-1"
							@click="$router.push(`/engineer-visits/${encodeURIComponent(v.name)}`)"
						>
							<div class="text-sm font-medium text-ink-gray-9">{{ v.service_request }}</div>
							<div class="text-xs text-ink-gray-5">{{ v.name }} · {{ v.status }}</div>
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { Button, DatePicker, call } from "frappe-ui";
import LayoutHeader from "@/components/LayoutHeader.vue";

const loading = ref(false);
const date = ref(new Date().toISOString().slice(0, 10));
const columns = ref({});

async function load() {
	loading.value = true;
	try {
		const data = await call("swiftservice.api.get_dispatch_board", { date: date.value });
		columns.value = data.columns || {};
	} finally {
		loading.value = false;
	}
}

onMounted(load);
</script>
