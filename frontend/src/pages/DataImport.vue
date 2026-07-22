<template>
	<DataImport
		:doctype="route.params.doctype"
		:importName="route.params.importName"
		:doctypeMap="doctypeMap"
	/>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { DataImport } from "frappe-ui/frappe";
import { resources } from "@/config/resources";

const route = useRoute();

/** Map SwiftService DocTypes → list/detail routes for frappe-ui DataImport. */
const doctypeMap = computed(() => {
	const map = {};
	for (const r of Object.values(resources)) {
		if (!r?.doctype || !r.route) continue;
		map[r.doctype] = {
			title: r.title || r.singular || r.doctype,
			listRoute: `/swiftservice/${r.route}`,
			pageRoute: `/swiftservice/${r.route}/docname`,
		};
	}
	return map;
});
</script>
