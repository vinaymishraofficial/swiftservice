<template>
	<DocListPage v-if="resource" v-bind="listProps" />
	<div v-else class="flex h-full items-center justify-center text-sm text-ink-gray-5">
		Unknown list: {{ resourceKey }}
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import DocListPage from "@/components/DocListPage.vue";
import { getResourceByRoute } from "@/config/resources";

const props = defineProps({
	resourceKey: { type: String, default: "" },
});

const route = useRoute();
const resourceKey = computed(() => props.resourceKey || route.meta.resourceKey || "");
const resource = computed(() => getResourceByRoute(resourceKey.value));

const listProps = computed(() => {
	const r = resource.value;
	if (!r) return {};
	return {
		title: r.title,
		singular: r.singular,
		doctype: r.doctype,
		fields: r.fields,
		columns: r.columns,
		quickFilters: r.quickFilters || [],
		createFields: r.createFields || [],
		createMethod: r.createMethod || "",
		creatable: r.creatable !== false,
		detailRoute: r.detailName,
		detailPath: `/${r.route}`,
	};
});
</script>
