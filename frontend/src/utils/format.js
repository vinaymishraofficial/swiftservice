export function parseStatusColor(status) {
	const v = (status || "").toLowerCase();
	if (["open", "new", "draft", "scheduled", "planned"].includes(v)) return "!text-ink-gray-9";
	if (
		[
			"in progress",
			"working",
			"nurture",
			"assigned",
			"travel started",
			"gps check-in",
			"inspection",
			"diagnosis",
			"repair",
			"testing",
			"analysis",
		].includes(v)
	)
		return "!text-blue-600";
	if (
		[
			"contacted",
			"pending",
			"pending approval",
			"pending purchase",
			"waiting spare",
			"on hold",
			"reserved",
			"in transit",
		].includes(v)
	)
		return "!text-orange-500";
	if (
		[
			"completed",
			"closed",
			"resolved",
			"approved",
			"issued",
			"dispatched",
			"active",
			"consumed",
			"received by engineer",
			"fixed",
		].includes(v)
	)
		return "!text-green-600";
	if (["cancelled", "rejected", "failed", "overdue", "breached"].includes(v)) return "!text-red-600";
	return "!text-ink-gray-5";
}

export function timeAgo(dateStr) {
	if (!dateStr) return "—";
	const d = new Date(dateStr);
	if (Number.isNaN(d.getTime())) return String(dateStr);
	const sec = Math.floor((Date.now() - d.getTime()) / 1000);
	if (sec < 60) return "just now";
	const min = Math.floor(sec / 60);
	if (min < 60) return `${min}m ago`;
	const hr = Math.floor(min / 60);
	if (hr < 24) return `${hr}h ago`;
	const day = Math.floor(hr / 24);
	if (day < 30) return `${day}d ago`;
	const mo = Math.floor(day / 30);
	if (mo < 12) return `${mo} month${mo > 1 ? "s" : ""} ago`;
	const yr = Math.floor(mo / 12);
	return `${yr} year${yr > 1 ? "s" : ""} ago`;
}

export function formatExact(dateStr) {
	if (!dateStr) return "";
	try {
		return new Date(dateStr).toLocaleString();
	} catch (e) {
		return String(dateStr);
	}
}
