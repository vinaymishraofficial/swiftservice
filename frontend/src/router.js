import { createRouter, createWebHistory } from "vue-router";
import { resources } from "@/config/resources";
import Dashboard from "@/pages/Dashboard.vue";
import DispatchBoard from "@/pages/DispatchBoard.vue";
import Reports from "@/pages/Reports.vue";
import HelpArticle from "@/pages/HelpArticle.vue";
import Settings from "@/pages/Settings.vue";
import ResourceList from "@/pages/ResourceList.vue";
import ResourceDetail from "@/pages/ResourceDetail.vue";
import NotFound from "@/pages/NotFound.vue";

function resourceRoutes() {
	const routes = [];
	for (const [key, r] of Object.entries(resources)) {
		routes.push({
			path: `/${r.route}`,
			name: r.listName,
			component: ResourceList,
			meta: { resourceKey: key },
			props: { resourceKey: key },
		});
		routes.push({
			path: `/${r.route}/:docname`,
			name: r.detailName,
			component: ResourceDetail,
			meta: { resourceKey: key },
			props: { resourceKey: key },
		});
	}
	return routes;
}

const routes = [
	{ path: "/", redirect: "/dashboard" },
	{ path: "/dashboard", name: "Dashboard", component: Dashboard },
	{ path: "/help/:article?", name: "Help", component: HelpArticle },
	{ path: "/dispatch", name: "Dispatch Board", component: DispatchBoard },
	{ path: "/reports", name: "Reports", component: Reports },
	{ path: "/settings", name: "Settings", component: Settings },
	{
		path: "/data-import",
		name: "DataImportList",
		component: () => import("@/pages/DataImport.vue"),
	},
	{
		path: "/data-import/doctype/:doctype",
		name: "NewDataImport",
		component: () => import("@/pages/DataImport.vue"),
	},
	{
		path: "/data-import/:importName",
		name: "DataImport",
		component: () => import("@/pages/DataImport.vue"),
	},
	...resourceRoutes(),
	{ path: "/:pathMatch(.*)*", name: "Not Found", component: NotFound },
];

const router = createRouter({
	history: createWebHistory("/swiftservice"),
	routes,
});

router.onError((err) => {
	console.error("SwiftService router error:", err);
});

export default router;
