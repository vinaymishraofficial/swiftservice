import { markRaw, reactive } from "vue";
import LucidePackage from "~icons/lucide/package";
import LucideClipboardList from "~icons/lucide/clipboard-list";
import LucideUserPlus from "~icons/lucide/user-plus";
import LucideMapPin from "~icons/lucide/map-pin";
import LucideStethoscope from "~icons/lucide/stethoscope";
import LucideWrench from "~icons/lucide/wrench";
import LucideFileText from "~icons/lucide/file-text";
import LucideMessageSquare from "~icons/lucide/message-square";
import LucideSparkles from "~icons/lucide/sparkles";
import { minimize } from "frappe-ui/frappe";
import { openSettings } from "@/composables/settings";

export const ONBOARDING_APP = "swiftservice";

/**
 * Build process steps for Getting started (right panel).
 * Mirrors CRM: click → navigate / open UI; Skip / Skip all supported by frappe-ui.
 */
export function createOnboardingSteps(router) {
	return reactive([
		{
			name: "add_installed_base",
			title: "Add an installed base unit",
			icon: markRaw(LucidePackage),
			completed: false,
			onClick: () => {
				minimize.value = true;
				router.push("/installed-base/new");
			},
		},
		{
			name: "create_service_request",
			title: "Create a service request",
			icon: markRaw(LucideClipboardList),
			completed: false,
			dependsOn: "add_installed_base",
			onClick: () => {
				minimize.value = true;
				router.push("/service-requests/new");
			},
		},
		{
			name: "assign_engineer",
			title: "Assign engineer & plan visit",
			icon: markRaw(LucideUserPlus),
			completed: false,
			dependsOn: "create_service_request",
			onClick: () => {
				minimize.value = true;
				router.push("/service-requests");
			},
		},
		{
			name: "check_in_visit",
			title: "Check in on a field visit",
			icon: markRaw(LucideMapPin),
			completed: false,
			dependsOn: "assign_engineer",
			onClick: () => {
				minimize.value = true;
				router.push("/engineer-visits");
			},
		},
		{
			name: "apply_diagnosis",
			title: "Capture diagnosis outcome",
			icon: markRaw(LucideStethoscope),
			completed: false,
			dependsOn: "check_in_visit",
			onClick: () => {
				minimize.value = true;
				router.push("/service-requests");
			},
		},
		{
			name: "start_resolution",
			title: "Start a resolution path",
			icon: markRaw(LucideWrench),
			completed: false,
			dependsOn: "apply_diagnosis",
			onClick: () => {
				minimize.value = true;
				router.push("/spare-requests");
			},
		},
		{
			name: "create_service_report",
			title: "Generate a service report",
			icon: markRaw(LucideFileText),
			completed: false,
			dependsOn: "start_resolution",
			onClick: () => {
				minimize.value = true;
				router.push("/service-reports");
			},
		},
		{
			name: "collect_feedback",
			title: "Collect feedback & close",
			icon: markRaw(LucideMessageSquare),
			completed: false,
			dependsOn: "create_service_report",
			onClick: () => {
				minimize.value = true;
				router.push("/feedback");
			},
		},
		{
			name: "service_closure",
			title: "Approve Service Closure",
			icon: markRaw(LucideFileText),
			completed: false,
			dependsOn: "collect_feedback",
			onClick: () => {
				minimize.value = true;
				router.push("/service-closures");
			},
		},
		{
			name: "configure_brand",
			title: "Configure brand settings",
			icon: markRaw(LucideSparkles),
			completed: false,
			onClick: () => {
				minimize.value = true;
				openSettings("Brand");
			},
		},
	]);
}

/** Map resource route keys → onboarding step names */
export const resourceOnboardingMap = {
	"installed-base": "add_installed_base",
	"service-requests": "create_service_request",
	"engineer-visits": "check_in_visit",
	"spare-requests": "start_resolution",
	rma: "start_resolution",
	replacements: "start_resolution",
	"service-reports": "create_service_report",
	feedback: "collect_feedback",
	"service-closures": "service_closure",
};
