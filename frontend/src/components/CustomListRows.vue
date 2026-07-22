<template>
	<div class="h-full overflow-y-auto" :class="$attrs.class">
		<ListRow v-for="row in rows" :key="row[rowKey]" :row="row">
			<template #default="slotProps">
				<slot v-bind="slotProps" />
			</template>
		</ListRow>
	</div>
</template>

<script setup>
import { ListRow } from "frappe-ui";
import { computed, inject } from "vue";

defineOptions({ inheritAttrs: false });

defineProps({
	rows: { type: Array, required: true },
});

const list = inject("list");
const rowKey = computed(() => list.value.rowKey);
</script>
