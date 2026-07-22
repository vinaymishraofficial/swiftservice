/**
 * Process-wise modules (Frappe HR style).
 * Each module is a complete process with its OWN sidebar — never merged.
 * Sidebar shape: flat steps (overview) → Reports → Setup.
 */
import { markRaw } from "vue";
import LucideLayoutDashboard from "~icons/lucide/layout-dashboard";
import LucideClipboardList from "~icons/lucide/clipboard-list";
import LucideUserCog from "~icons/lucide/user-cog";
import LucidePackage from "~icons/lucide/package";
import LucideWrench from "~icons/lucide/wrench";
import LucideFactory from "~icons/lucide/factory";
import LucideReplace from "~icons/lucide/repeat-2";
import LucideCalendarCheck from "~icons/lucide/calendar-check";
import LucideFileBarChart from "~icons/lucide/file-bar-chart";
import LucideMap from "~icons/lucide/map";
import LucideFileText from "~icons/lucide/file-text";
import LucideShield from "~icons/lucide/shield";
import LucideGauge from "~icons/lucide/gauge";
import LucideUsers from "~icons/lucide/users";
import LucideTruck from "~icons/lucide/truck";
import LucideBookOpen from "~icons/lucide/book-open";
import LucideReceipt from "~icons/lucide/receipt";
import LucideMessageSquare from "~icons/lucide/message-square";
import LucideHammer from "~icons/lucide/hammer";
import LucideSearch from "~icons/lucide/search";
import LucideBadgeCheck from "~icons/lucide/badge-check";
import LucideHome from "~icons/lucide/home";
import LucideBoxes from "~icons/lucide/boxes";
import LucideHardHat from "~icons/lucide/hard-hat";
import LucideBuilding2 from "~icons/lucide/building-2";
import LucideCircleCheck from "~icons/lucide/circle-check-big";
import LucideFileSignature from "~icons/lucide/file-signature";

const STORAGE_KEY = "ss_active_module";

function link(label, icon, to) {
	return { label, icon: markRaw(icon), to };
}

function reportLink(label, moduleId, reportKey = null) {
	const q = reportKey
		? `module=${moduleId}&report=${reportKey}`
		: `module=${moduleId}`;
	return link(label, LucideFileBarChart, `/reports?${q}`);
}

/**
 * Module definitions for Home grid + sidebar switcher.
 * `routes` = path prefixes owned by THIS module only.
 */
export const modules = [
	{
		id: "home",
		label: "Home",
		description: "Dashboard, dispatch board, knowledge",
		icon: markRaw(LucideHome),
		homeRoute: "/dashboard",
		routes: ["/dashboard", "/dispatch", "/knowledge-base", "/help"],
		showInGrid: true,
	},
	{
		id: "installed-base",
		label: "Installed Base",
		description: "Installed products and asset history",
		icon: markRaw(LucidePackage),
		homeRoute: "/installed-base",
		routes: ["/installed-base"],
		showInGrid: true,
	},
	{
		id: "service-requests",
		label: "Service Requests",
		description: "Complaints and service tickets",
		icon: markRaw(LucideClipboardList),
		homeRoute: "/service-requests",
		routes: ["/service-requests"],
		showInGrid: true,
	},
	{
		id: "field",
		label: "Field Operations",
		description: "Assignments, visits, diagnosis",
		icon: markRaw(LucideHardHat),
		homeRoute: "/engineer-assignments",
		routes: ["/engineer-assignments", "/engineer-visits", "/diagnoses", "/engineer-profiles"],
		showInGrid: true,
	},
	{
		id: "spares",
		label: "Spares",
		description: "Spare requests and van stock",
		icon: markRaw(LucideBoxes),
		homeRoute: "/spare-requests",
		routes: ["/spare-requests", "/van-inventory"],
		showInGrid: true,
	},
	{
		id: "factory",
		label: "Factory & RMA",
		description: "RMA, repair, replacements",
		icon: markRaw(LucideBuilding2),
		homeRoute: "/rma",
		routes: ["/rma", "/repair-orders", "/replacements"],
		showInGrid: true,
	},
	{
		id: "closure",
		label: "Closure & Billing",
		description: "Reports, feedback, billing, closure",
		icon: markRaw(LucideCircleCheck),
		homeRoute: "/service-reports",
		routes: [
			"/service-reports",
			"/feedback",
			"/service-closures",
			"/billing",
			"/estimates",
		],
		showInGrid: true,
	},
	{
		id: "contracts",
		label: "Contracts & PM",
		description: "AMC, PM visits, calibration",
		icon: markRaw(LucideFileSignature),
		homeRoute: "/amc-contracts",
		routes: ["/amc-contracts", "/pm-visits", "/calibrations"],
		showInGrid: true,
	},
];

/**
 * Each module = one complete process (like Frappe HR Recruitment).
 * Steps stay inside that module — not shared across modules.
 */
const SIDEBARS = {
	home: {
		overview: [
			link("Dashboard", LucideLayoutDashboard, "/dashboard"),
			link("Dispatch Board", LucideMap, "/dispatch"),
			link("Knowledge Base", LucideBookOpen, "/knowledge-base"),
		],
		reports: [
			reportLink("All Reports", "home"),
			reportLink("Open Tickets", "home", "open_tickets"),
			reportLink("Pending Visits", "home", "pending_visits"),
			reportLink("SLA Breach", "home", "sla_breach"),
		],
		setup: [],
	},
	"installed-base": {
		overview: [link("Installed Base", LucidePackage, "/installed-base")],
		reports: [
			reportLink("Installed Base Reports", "installed-base"),
			reportLink("Open Tickets", "installed-base", "open_tickets"),
		],
		setup: [],
	},
	"service-requests": {
		overview: [link("Service Request", LucideClipboardList, "/service-requests")],
		reports: [
			reportLink("All Reports", "service-requests"),
			reportLink("Open Tickets", "service-requests", "open_tickets"),
			reportLink("SLA Breach", "service-requests", "sla_breach"),
		],
		setup: [],
	},
	field: {
		overview: [
			link("Assignment", LucideUserCog, "/engineer-assignments"),
			link("Service Visit", LucideHardHat, "/engineer-visits"),
			link("Diagnosis / RCA", LucideSearch, "/diagnoses"),
		],
		reports: [
			reportLink("Field Reports", "field"),
			reportLink("Pending Visits", "field", "pending_visits"),
		],
		setup: [link("Engineers", LucideUsers, "/engineer-profiles")],
	},
	spares: {
		overview: [link("Spare Request", LucideWrench, "/spare-requests")],
		reports: [
			reportLink("Spares Reports", "spares"),
			reportLink("Pending Spares", "spares", "spare_pending"),
		],
		setup: [link("Van Inventory", LucideTruck, "/van-inventory")],
	},
	factory: {
		overview: [
			link("RMA / Factory", LucideFactory, "/rma"),
			link("Repair Order", LucideHammer, "/repair-orders"),
			link("Replacement", LucideReplace, "/replacements"),
		],
		reports: [reportLink("Factory Reports", "factory")],
		setup: [],
	},
	closure: {
		overview: [
			link("Service Report", LucideFileText, "/service-reports"),
			link("Feedback", LucideMessageSquare, "/feedback"),
			link("Closure", LucideBadgeCheck, "/service-closures"),
			link("Billing", LucideReceipt, "/billing"),
		],
		reports: [reportLink("Closure & Billing Reports", "closure")],
		setup: [link("Estimates", LucideReceipt, "/estimates")],
	},
	contracts: {
		overview: [
			link("AMC Contract", LucideShield, "/amc-contracts"),
			link("PM Visit", LucideCalendarCheck, "/pm-visits"),
			link("Calibration", LucideGauge, "/calibrations"),
		],
		reports: [
			reportLink("Contract Reports", "contracts"),
			reportLink("Active AMC", "contracts", "amc_active"),
		],
		setup: [],
	},
};

export function getModuleById(id) {
	return modules.find((m) => m.id === id) || modules[0];
}

export function getModuleForPath(path, queryModule = "", preferredId = "") {
	const clean = (path || "/").split("?")[0];
	if (clean === "/reports" || clean.startsWith("/reports")) {
		if (queryModule) return getModuleById(queryModule);
		if (preferredId) return getModuleById(preferredId);
		return getModuleById("home");
	}

	const owns = (mod, p) =>
		(mod?.routes || []).some((route) => p === route || p.startsWith(`${route}/`));

	// Stay on the module the user picked while they walk its own steps
	if (preferredId) {
		const pref = getModuleById(preferredId);
		if (pref && owns(pref, clean)) return pref;
	}

	let best = null;
	let bestLen = -1;
	for (const m of modules) {
		for (const route of m.routes || []) {
			if (clean === route || clean.startsWith(`${route}/`)) {
				if (route.length > bestLen) {
					best = m;
					bestLen = route.length;
				}
			}
		}
	}
	return best || getModuleById("home");
}

export function getStoredModuleId() {
	try {
		return localStorage.getItem(STORAGE_KEY) || "";
	} catch {
		return "";
	}
}

export function setStoredModuleId(id) {
	try {
		if (id) localStorage.setItem(STORAGE_KEY, id);
	} catch {
		/* ignore */
	}
}

/**
 * Build frappe-ui Sidebar sections for a module.
 * Flat steps first (HR style), then Reports / Setup collapsible.
 */
export function getModuleSidebar(moduleId, isActiveFn = () => false) {
	const def = SIDEBARS[moduleId] || SIDEBARS.home;
	const withActive = (items) =>
		(items || []).map((item) => ({
			...item,
			isActive: isActiveFn(item.to),
		}));

	const sections = [];
	if (def.overview?.length) {
		sections.push({
			label: "",
			collapsible: false,
			items: withActive(def.overview),
		});
	}
	if (def.process?.length) {
		sections.push({
			label: "Process",
			collapsible: true,
			items: withActive(def.process),
		});
	}
	if (def.reports?.length) {
		sections.push({
			label: "Reports",
			collapsible: true,
			items: withActive(def.reports),
		});
	}
	if (def.setup?.length) {
		sections.push({
			label: "Setup",
			collapsible: true,
			items: withActive(def.setup),
		});
	} else if (def.masters?.length) {
		sections.push({
			label: "Masters",
			collapsible: true,
			items: withActive(def.masters),
		});
	}
	return sections;
}

export const MODULE_REPORTS = {
	home: ["open_tickets", "pending_visits", "spare_pending", "sla_breach", "amc_active"],
	"installed-base": ["open_tickets"],
	"service-requests": ["open_tickets", "sla_breach"],
	field: ["pending_visits"],
	spares: ["spare_pending"],
	factory: ["spare_pending"],
	closure: ["open_tickets"],
	contracts: ["amc_active"],
};

export const ALL_REPORTS = [
	{
		key: "open_tickets",
		label: "Open Tickets",
		modules: ["home", "service-requests", "installed-base", "closure"],
	},
	{ key: "pending_visits", label: "Pending Visits", modules: ["home", "field"] },
	{ key: "spare_pending", label: "Pending Spares", modules: ["home", "spares", "factory"] },
	{ key: "sla_breach", label: "SLA Breach", modules: ["home", "service-requests"] },
	{ key: "amc_active", label: "Active AMC", modules: ["home", "contracts"] },
];
