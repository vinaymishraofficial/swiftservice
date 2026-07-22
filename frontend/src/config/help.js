/** Help centre articles — opened via HelpModal → /swiftservice/help/:slug */
export const helpArticles = [
	{
		title: "Introduction",
		opened: true,
		subArticles: [
			{ name: "introduction", title: "What is SwiftService?" },
			{ name: "lifecycle", title: "Service lifecycle" },
			{ name: "getting-started", title: "Getting started checklist" },
		],
	},
	{
		title: "Install & Complaint",
		opened: false,
		subArticles: [
			{ name: "installed-base", title: "Installed Base" },
			{ name: "service-request", title: "Service Request" },
			{ name: "sla-warranty", title: "SLA, Warranty & AMC" },
		],
	},
	{
		title: "Field Visit",
		opened: false,
		subArticles: [
			{ name: "assign-engineer", title: "Assign engineer" },
			{ name: "engineer-visit", title: "Engineer Visit" },
			{ name: "diagnosis", title: "Diagnosis outcomes" },
		],
	},
	{
		title: "Resolution Paths",
		opened: false,
		subArticles: [
			{ name: "spare-path", title: "Spare path" },
			{ name: "rma-path", title: "Factory RMA path" },
			{ name: "replacement-path", title: "Replacement path" },
			{ name: "onsite-fix", title: "On-site fix / NFF" },
		],
	},
	{
		title: "Closure & PM",
		opened: false,
		subArticles: [
			{ name: "service-report", title: "Service Report" },
			{ name: "feedback-close", title: "Feedback & close" },
			{ name: "amc-pm", title: "AMC & PM" },
		],
	},
	{
		title: "Settings",
		opened: false,
		subArticles: [
			{ name: "profile", title: "Profile" },
			{ name: "branding", title: "Brand & logo" },
			{ name: "preferences", title: "Preferences & theme" },
		],
	},
];

export const helpContent = {
	introduction: {
		title: "What is SwiftService?",
		body: [
			"SwiftService is an after-sales field-service workspace built on Frappe.",
			"Run the full loop without bouncing to Desk: Install Base → Complaint → Visit → Resolve → Close, plus AMC/PM.",
			"Use Getting started (right panel) to walk the process step by step. Skip any step, or Skip all anytime.",
		],
	},
	lifecycle: {
		title: "Service lifecycle",
		body: [
			"1 · Install Base — register customer asset / serial.",
			"2 · Complaint — open a Service Request, validate warranty/AMC/SLA.",
			"3 · Field Visit — assign engineer, plan visit, check-in, diagnose.",
			"4 · Resolution — spare, factory RMA, replacement, or on-site fix.",
			"5 · Closure — service report, estimate/invoice if chargeable, feedback, close.",
			"6 · Contracts & PM — AMC schedules, PM visits, calibration.",
		],
	},
	"getting-started": {
		title: "Getting started checklist",
		body: [
			"Open Getting started from the sidebar banner (or Help after you finish).",
			"Each step navigates you to the right screen. Complete the action — the step marks done.",
			"Hover a step to Skip it. Use Skip all to dismiss the whole checklist.",
			"Help centre stays available for reference articles anytime.",
		],
	},
	"installed-base": {
		title: "Installed Base",
		body: [
			"Create an Installed Base record linking Customer + Item + Serial No.",
			"This is the asset the field team will service. Warranty and AMC attach here.",
			"Sidebar → 1 · Install Base → Installed Base → Create.",
		],
	},
	"service-request": {
		title: "Service Request",
		body: [
			"A Service Request is the complaint ticket — subject, customer, priority, SLA.",
			"Link the Installed Base so history and warranty are visible.",
			"Save as Draft, then Submit when ready. Assign members with the Members control.",
		],
	},
	"sla-warranty": {
		title: "SLA, Warranty & AMC",
		body: [
			"Priority and SLA hours drive response expectations.",
			"Warranty / AMC on the installed unit decide if work is chargeable.",
			"Set defaults under Settings → General.",
		],
	},
	"assign-engineer": {
		title: "Assign engineer",
		body: [
			"From an open Service Request, use Assign Engineer & Plan Visit.",
			"This creates an Engineer Visit and moves the request forward.",
			"You can also use Members to assign coordinators / watchers.",
		],
	},
	"engineer-visit": {
		title: "Engineer Visit",
		body: [
			"Plan the visit date, confirm with the customer, then Check in on site.",
			"Capture diagnosis notes in the Text editor fields.",
			"Check out when the on-site work for that visit is done.",
		],
	},
	diagnosis: {
		title: "Diagnosis outcomes",
		body: [
			"Set Diagnosis on the Service Request, Save, then Apply Diagnosis.",
			"Outcomes branch the process: Spare required, Factory RMA, Replacement, Fixed on site, or No fault found.",
		],
	},
	"spare-path": {
		title: "Spare path",
		body: [
			"Create a Spare Request from the Service Request sidebar actions.",
			"Approve → Issue from store (or purchase) → engineer fits the part → continue to report.",
		],
	},
	"rma-path": {
		title: "Factory RMA path",
		body: [
			"Create an RMA case when the unit must return to factory.",
			"Advance status: Pickup → QI → Repair → Test → Dispatch.",
		],
	},
	"replacement-path": {
		title: "Replacement path",
		body: [
			"Create a Replacement case, get approvals, issue challan, map new serial, transfer warranty.",
		],
	},
	"onsite-fix": {
		title: "On-site fix / NFF",
		body: [
			"If fixed without spare/RMA, or no fault found, skip resolution docs and go to Service Report → Feedback → Close.",
		],
	},
	"service-report": {
		title: "Service Report",
		body: [
			"Record work done, parts used, and customer verification.",
			"Chargeable jobs can raise an estimate / invoice from the estimate document.",
		],
	},
	"feedback-close": {
		title: "Feedback & Service Closure",
		body: [
			"Collect CSAT/NPS on Customer Feedback, then generate Service Closure.",
			"Service Closure validates ops/inventory/billing/compliance before permanently closing the Service Request.",
		],
	},
	"amc-pm": {
		title: "AMC & PM",
		body: [
			"AMC Contracts schedule preventive maintenance.",
			"PM Visits and Calibrations keep the install base healthy between complaints.",
		],
	},
	profile: {
		title: "Profile",
		body: ["Open Settings from the brand menu → Profile. Update name, phone, and avatar."],
	},
	branding: {
		title: "Brand & logo",
		body: ["Settings → Brand. Set brand name, logo, and favicon shown in the sidebar."],
	},
	preferences: {
		title: "Preferences & theme",
		body: [
			"Settings → Preferences for theme (Light / Dark / System) and collapsed sidebar rail.",
		],
	},
};
