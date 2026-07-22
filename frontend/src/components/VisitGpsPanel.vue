<template>
	<div class="flex flex-col gap-3">
		<div class="flex items-start justify-between gap-2">
			<div>
				<div class="text-sm font-medium text-ink-gray-9">{{ title }}</div>
				<div class="text-p-sm text-ink-gray-5">{{ subtitle }}</div>
			</div>
			<Badge v-if="statusLabel" :label="statusLabel" :theme="statusTheme" variant="subtle" />
		</div>

		<div class="rounded-xl border border-outline-gray-2 bg-surface-white px-3 py-2.5">
			<div class="mb-1 text-[11px] font-semibold uppercase tracking-wide text-ink-gray-5">
				Visit Progress
			</div>
			<div class="grid grid-cols-3 gap-2 text-xs">
				<div class="rounded-md px-2 py-1.5 text-center" :class="stepClass(1)">1. Navigate</div>
				<div class="rounded-md px-2 py-1.5 text-center" :class="stepClass(2)">2. Check-in</div>
				<div class="rounded-md px-2 py-1.5 text-center" :class="stepClass(3)">3. Check-out</div>
			</div>
		</div>

		<!-- Destination card — where engineer must go (Blinkit / Zomato style) -->
		<div
			class="rounded-xl border border-outline-gray-2 bg-surface-white p-3 shadow-sm"
			:class="hasSitePin ? 'border-l-4 border-l-blue-500' : 'border-l-4 border-l-orange-400'"
		>
			<div class="flex items-start gap-2.5">
				<span
					class="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full bg-blue-50 text-blue-600"
					aria-hidden="true"
				>
					<span class="lucide-map-pinned size-4" />
				</span>
				<div class="min-w-0 flex-1">
					<div class="text-[11px] font-semibold uppercase tracking-wide text-ink-gray-5">
						Go to customer
					</div>
					<div class="mt-0.5 text-base font-semibold text-ink-gray-9">
						{{ customerName || "Customer site" }}
					</div>
					<div v-if="siteAddress" class="mt-1 text-sm leading-snug text-ink-gray-7">
						{{ siteAddress }}
					</div>
					<div
						v-else-if="!hasSitePin"
						class="mt-1 text-sm text-orange-700"
					>
						Site pin / address missing — set destination below before travel.
					</div>
					<div v-if="hasSitePin" class="mt-1 font-mono text-[11px] tabular-nums text-ink-gray-5">
						{{ fmt(siteLat, siteLng) }}
					</div>
					<div
						v-if="liveDistanceText"
						class="mt-2 text-sm font-medium text-ink-gray-8"
					>
						{{ liveDistanceText }}
						<span v-if="etaText" class="font-normal text-ink-gray-5"> · {{ etaText }}</span>
					</div>
				</div>
			</div>

			<div class="mt-3 flex flex-col gap-2 sm:flex-row">
				<a
					v-if="navigateUrl"
					:href="navigateUrl"
					target="_blank"
					rel="noopener"
					class="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-surface-gray-7 px-3 py-2.5 text-sm font-semibold text-ink-white no-underline transition hover:opacity-90"
				>
					<span class="lucide-navigation size-4" aria-hidden="true" />
					Start navigation
				</a>
				<a
					v-if="customerPhone"
					:href="`tel:${customerPhone}`"
					class="inline-flex items-center justify-center gap-2 rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2.5 text-sm font-medium text-ink-gray-8 no-underline"
				>
					<span class="lucide-phone size-4" aria-hidden="true" />
					Call
				</a>
			</div>
		</div>

		<!-- Set destination when office forgot pin -->
		<div
			v-if="!hasSitePin"
			class="rounded-xl border border-dashed border-orange-300 bg-orange-50/60 p-3"
		>
			<div class="text-sm font-medium text-ink-gray-9">Set exact destination pin</div>
			<div class="mt-1 text-p-sm text-ink-gray-6">
				Without this pin, maps cannot guide the engineer (like Blinkit drop pin).
			</div>
			<textarea
				v-model="pinAddressDraft"
				rows="2"
				class="mt-2 w-full rounded-lg border border-outline-gray-2 bg-surface-white px-2.5 py-2 text-sm text-ink-gray-8"
				placeholder="Full site address (building, street, area, city, pincode)"
			/>
			<div class="mt-2 flex flex-col gap-2 sm:flex-row">
				<Button
					class="flex-1"
					variant="solid"
					label="Find & set pin from address"
					iconLeft="lucide-search"
					:loading="busy === 'geocode'"
					:disabled="!!busy || !pinAddressDraft.trim()"
					@click="geocodeAndSetSite"
				/>
				<Button
					class="flex-1"
					variant="outline"
					label="I'm at site — pin here"
					iconLeft="lucide-crosshair"
					:loading="busy === 'pin'"
					:disabled="!!busy"
					@click="pinSiteHere"
				/>
			</div>
		</div>

		<LocationMap
			:points="mapPoints"
			:empty-text="mapEmpty"
			:tall="fullWidth"
			:focus-label="'Customer site'"
		/>

		<div class="grid grid-cols-1 gap-2 text-xs text-ink-gray-6 sm:grid-cols-2">
			<div class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 px-2.5 py-2">
				<div class="text-ink-gray-5">Destination</div>
				<div class="mt-0.5 font-medium tabular-nums text-ink-gray-8">
					{{ fmt(siteLat, siteLng) }}
				</div>
				<div v-if="siteAddress" class="mt-1 text-[11px] leading-snug text-ink-gray-6">
					{{ siteAddress }}
				</div>
			</div>
			<div class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 px-2.5 py-2">
				<div class="flex items-center justify-between gap-1">
					<span class="text-ink-gray-5">Your location</span>
					<span v-if="locating" class="text-[10px] text-ink-gray-5">updating…</span>
				</div>
				<div class="mt-0.5 font-medium tabular-nums text-ink-gray-8">
					{{ fmt(effectiveLiveLat, effectiveLiveLng) }}
				</div>
			</div>
			<div class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 px-2.5 py-2">
				<div class="flex items-center justify-between gap-1">
					<span class="text-ink-gray-5">Check-in</span>
					<span v-if="checkInTimeText" class="text-[10px] text-ink-gray-5">{{ checkInTimeText }}</span>
				</div>
				<div class="mt-0.5 font-medium tabular-nums text-ink-gray-8">{{ checkInText }}</div>
				<div v-if="checkInAddress" class="mt-1 text-[11px] leading-snug text-ink-gray-6">
					{{ checkInAddress }}
				</div>
			</div>
			<div class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 px-2.5 py-2">
				<div class="flex items-center justify-between gap-1">
					<span class="text-ink-gray-5">Check-out</span>
					<span v-if="props.doc?.check_out_time" class="text-[10px] text-ink-gray-5">{{
						timeAgo(props.doc.check_out_time)
					}}</span>
				</div>
				<div class="mt-0.5 font-medium tabular-nums text-ink-gray-8">{{ fmt(checkOutLat, checkOutLng) }}</div>
				<div v-if="props.doc?.check_out_address" class="mt-1 text-[11px] leading-snug text-ink-gray-6">
					{{ props.doc.check_out_address }}
				</div>
			</div>
		</div>

		<ErrorMessage :message="geoError" />

		<div class="flex flex-col gap-2 sm:flex-row">
			<Button
				class="flex-1"
				variant="solid"
				label="Arrived — GPS Check-in"
				iconLeft="lucide-map-pin"
				:loading="busy === 'in'"
				:disabled="!!busy || checkedOut"
				@click="doCheckIn"
			/>
			<Button
				class="flex-1"
				variant="outline"
				label="GPS Check-out"
				iconLeft="lucide-log-out"
				:loading="busy === 'out'"
				:disabled="!!busy || !checkedIn || checkedOut"
				@click="doCheckOut"
			/>
		</div>
		<Button
			variant="ghost"
			label="Refresh my location"
			iconLeft="lucide-locate"
			:loading="locating"
			class="w-full"
			@click="refreshLive"
		/>
	</div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from "vue";
import { Badge, Button, ErrorMessage, call, toast } from "frappe-ui";
import LocationMap from "@/components/LocationMap.vue";
import { timeAgo } from "@/utils/format";

const props = defineProps({
	doc: { type: Object, required: true },
	title: { type: String, default: "GPS Tracking" },
	fullWidth: { type: Boolean, default: false },
});

const emit = defineEmits(["updated"]);

const busy = ref("");
const locating = ref(false);
const geoError = ref("");
const liveLat = ref(null);
const liveLng = ref(null);
const liveAccuracy = ref(null);
const serverLive = ref(null);
const pinAddressDraft = ref("");
let watchId = null;
let trackingTimer = null;
let lastPushMs = 0;

const checkedIn = computed(
	() =>
		!!(
			props.doc?.check_in_time ||
			props.doc?.gps_check_in ||
			isValidCoord(props.doc?.check_in_latitude, props.doc?.check_in_longitude)
		),
);

const checkedOut = computed(
	() =>
		!!(
			props.doc?.check_out_time ||
			props.doc?.gps_check_out ||
			isValidCoord(props.doc?.check_out_latitude, props.doc?.check_out_longitude)
		),
);

const statusLabel = computed(() => {
	if (checkedOut.value) return "Checked out";
	if (checkedIn.value) return "At site";
	if (hasSitePin.value && liveDistanceM.value != null && liveDistanceM.value <= 150) {
		return "Near site";
	}
	if (hasSitePin.value) return "Navigate";
	return "No destination";
});

const statusTheme = computed(() => {
	if (checkedOut.value) return "gray";
	if (checkedIn.value) return "green";
	if (!hasSitePin.value) return "orange";
	return "blue";
});

const trackingPhase = computed(() => {
	if (checkedOut.value) return 3;
	if (checkedIn.value) return 2;
	return 1;
});

const customerName = computed(
	() => props.doc?.customer || props.doc?._customer_name || "",
);
const customerPhone = computed(
	() => props.doc?.mobile_no || props.doc?._customer_mobile || "",
);

const siteLat = computed(() => num(props.doc?._site_latitude));
const siteLng = computed(() => num(props.doc?._site_longitude));
const hasSitePin = computed(() => isValidCoord(siteLat.value, siteLng.value));

const siteAddress = computed(
	() => props.doc?.site_address || props.doc?._site_address || "",
);

const subtitle = computed(() => {
	if (!hasSitePin.value) {
		return "Set customer pin first, then start navigation.";
	}
	if (liveDistanceText.value) {
		return `Drive to pin · ${liveDistanceText.value}${etaText.value ? ` · ${etaText.value}` : ""}`;
	}
	return "Navigate to customer pin, then do GPS check-in on arrival.";
});

const checkInLat = computed(() => num(props.doc?.check_in_latitude));
const checkInLng = computed(() => num(props.doc?.check_in_longitude));
const checkOutLat = computed(() => num(props.doc?.check_out_latitude));
const checkOutLng = computed(() => num(props.doc?.check_out_longitude));
const checkInText = computed(() => fmt(checkInLat.value, checkInLng.value));
const checkInAddress = computed(() => props.doc?.check_in_address || "");
const checkInTimeText = computed(() =>
	props.doc?.check_in_time ? timeAgo(props.doc.check_in_time) : "",
);

const liveDistanceM = computed(() => {
	const lat = effectiveLiveLat.value;
	const lng = effectiveLiveLng.value;
	if (!hasSitePin.value || !isValidCoord(lat, lng)) return null;
	return haversineM(lat, lng, siteLat.value, siteLng.value);
});

const liveDistanceText = computed(() => {
	const d = liveDistanceM.value;
	if (d == null) return "";
	if (d < 1000) return `${Math.round(d)} m away`;
	return `${(d / 1000).toFixed(1)} km away`;
});

const etaText = computed(() => {
	if (serverLive.value?.eta?.eta_sec) {
		const mins = Math.max(1, Math.round(Number(serverLive.value.eta.eta_sec) / 60));
		if (mins < 60) return `~${mins} min drive`;
		return `~${(mins / 60).toFixed(1)} hr drive`;
	}
	const d = liveDistanceM.value;
	if (d == null) return "";
	// Rough city drive ~22 km/h avg incl. traffic
	const mins = Math.max(1, Math.round((d / 1000 / 22) * 60));
	if (mins < 60) return `~${mins} min drive`;
	return `~${(mins / 60).toFixed(1)} hr drive`;
});

const navigateUrl = computed(() => {
	if (hasSitePin.value) {
		const dest = `${siteLat.value},${siteLng.value}`;
		let url = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(dest)}&travelmode=driving`;
		if (isValidCoord(effectiveLiveLat.value, effectiveLiveLng.value)) {
			url += `&origin=${encodeURIComponent(`${effectiveLiveLat.value},${effectiveLiveLng.value}`)}`;
		}
		return url;
	}
	if (siteAddress.value) {
		return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(siteAddress.value)}&travelmode=driving`;
	}
	return "";
});

const effectiveLiveLat = computed(() => {
	if (isValidCoord(liveLat.value, liveLng.value)) return liveLat.value;
	if (isValidCoord(serverLive.value?.live_location?.lat, serverLive.value?.live_location?.lng)) {
		return Number(serverLive.value.live_location.lat);
	}
	return null;
});

const effectiveLiveLng = computed(() => {
	if (isValidCoord(liveLat.value, liveLng.value)) return liveLng.value;
	if (isValidCoord(serverLive.value?.live_location?.lat, serverLive.value?.live_location?.lng)) {
		return Number(serverLive.value.live_location.lng);
	}
	return null;
});

const mapEmpty = computed(() => {
	if (geoError.value) return "Enable location permission";
	if (!hasSitePin.value) return "No customer pin yet — set destination above";
	return "Refreshing your location…";
});

const mapPoints = computed(() => {
	const pts = [];
	if (hasSitePin.value) {
		pts.push({
			lat: siteLat.value,
			lng: siteLng.value,
			label: "Customer site",
			name: siteAddress.value || customerName.value || "",
			address: siteAddress.value,
			color: "#2563eb",
			primary: true,
		});
	}
	if (isValidCoord(checkInLat.value, checkInLng.value)) {
		pts.push({
			lat: checkInLat.value,
			lng: checkInLng.value,
			label: "Check-in",
			address: checkInAddress.value,
			color: "#16a34a",
		});
	}
	if (isValidCoord(checkOutLat.value, checkOutLng.value)) {
		pts.push({
			lat: checkOutLat.value,
			lng: checkOutLng.value,
			label: "Check-out",
			address: props.doc?.check_out_address || "",
			color: "#ca8a04",
		});
	}
	if (isValidCoord(liveLat.value, liveLng.value)) {
		const nearCheckIn =
			isValidCoord(checkInLat.value, checkInLng.value) &&
			Math.abs(checkInLat.value - liveLat.value) < 0.00008 &&
			Math.abs(checkInLng.value - liveLng.value) < 0.00008;
		if (!nearCheckIn) {
			pts.push({
				lat: liveLat.value,
				lng: liveLng.value,
				label: "You",
				color: "#c04070",
			});
		}
	}
	if (
		!isValidCoord(liveLat.value, liveLng.value) &&
		isValidCoord(serverLive.value?.live_location?.lat, serverLive.value?.live_location?.lng)
	) {
		pts.push({
			lat: Number(serverLive.value.live_location.lat),
			lng: Number(serverLive.value.live_location.lng),
			label: "Engineer (live)",
			color: "#c04070",
		});
	}
	return pts;
});

function isValidCoord(lat, lng) {
	const a = Number(lat);
	const b = Number(lng);
	if (!Number.isFinite(a) || !Number.isFinite(b)) return false;
	if (Math.abs(a) < 0.00001 && Math.abs(b) < 0.00001) return false;
	return true;
}

function num(v) {
	if (v === null || v === undefined || v === "") return null;
	const n = Number(v);
	return Number.isFinite(n) ? n : null;
}

function fmt(lat, lng) {
	if (!isValidCoord(lat, lng)) return "—";
	return `${Number(lat).toFixed(5)}, ${Number(lng).toFixed(5)}`;
}

function stepClass(step) {
	if (trackingPhase.value === step) return "bg-surface-gray-7 text-ink-white";
	if (trackingPhase.value > step) return "bg-green-100 text-green-800";
	return "bg-surface-gray-2 text-ink-gray-6";
}

function haversineM(lat1, lng1, lat2, lng2) {
	const R = 6371000;
	const toRad = (d) => (d * Math.PI) / 180;
	const dLat = toRad(lat2 - lat1);
	const dLng = toRad(lng2 - lng1);
	const a =
		Math.sin(dLat / 2) ** 2 +
		Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
	return 2 * R * Math.asin(Math.sqrt(a));
}

function applyGeo(pos) {
	liveLat.value = pos.coords.latitude;
	liveLng.value = pos.coords.longitude;
	if (Number.isFinite(pos.coords.accuracy)) {
		liveAccuracy.value = pos.coords.accuracy;
	}
	pushLiveLocationThrottled();
}

function getGeo() {
	return new Promise((resolve, reject) => {
		if (!navigator.geolocation) {
			reject(new Error("GPS not supported on this device"));
			return;
		}
		const opts = { enableHighAccuracy: true, timeout: 25000, maximumAge: 0 };
		let best = null;
		let settled = false;
		let wid = null;
		const finish = (err) => {
			if (settled) return;
			settled = true;
			if (wid != null) navigator.geolocation.clearWatch(wid);
			clearTimeout(timer);
			if (best) {
				applyGeo(best);
				resolve({
					gps_lat: best.coords.latitude,
					gps_lng: best.coords.longitude,
					gps_accuracy: best.coords.accuracy,
				});
			} else {
				const msg =
					err?.code === 1
						? "Location permission denied. Enable GPS for this site."
						: err?.code === 3
							? "GPS timed out. Try again outdoors."
							: "Could not read GPS location";
				reject(new Error(msg));
			}
		};
		const onPos = (pos) => {
			const acc = pos?.coords?.accuracy;
			if (!best || (Number.isFinite(acc) && acc < (best.coords.accuracy || Infinity))) {
				best = pos;
				applyGeo(pos);
			}
			if (Number.isFinite(acc) && acc <= 30) finish();
		};
		const timer = setTimeout(() => finish(best ? null : { code: 3 }), 10000);
		navigator.geolocation.getCurrentPosition(onPos, (err) => {
			if (!best) finish(err);
		}, opts);
		try {
			wid = navigator.geolocation.watchPosition(onPos, () => {}, opts);
		} catch {
			/* ignore */
		}
	});
}

function startLiveWatch() {
	stopLiveWatch();
	if (!navigator.geolocation) return;
	watchId = navigator.geolocation.watchPosition(
		(pos) => applyGeo(pos),
		() => {},
		{ enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 },
	);
}

function stopLiveWatch() {
	if (watchId != null && navigator.geolocation) {
		navigator.geolocation.clearWatch(watchId);
		watchId = null;
	}
}

async function refreshLive() {
	locating.value = true;
	geoError.value = "";
	try {
		await getGeo();
	} catch (e) {
		geoError.value = e?.message || "GPS failed";
	} finally {
		locating.value = false;
	}
}

function pushLiveLocationThrottled() {
	if (!props.doc?.name || !isValidCoord(liveLat.value, liveLng.value)) return;
	const now = Date.now();
	if (now - lastPushMs < 5000) return;
	lastPushMs = now;
	call("swiftservice.api.update_live_location", {
		name: props.doc.name,
		gps_lat: liveLat.value,
		gps_lng: liveLng.value,
		gps_accuracy: liveAccuracy.value,
	}).catch(() => {
		/* best effort; do not block UI */
	});
}

async function fetchLiveTracking() {
	if (!props.doc?.name) return;
	try {
		const data = await call("swiftservice.api.get_live_tracking", { name: props.doc.name });
		serverLive.value = data || null;
	} catch {
		/* ignore transient tracking fetch errors */
	}
}

async function geocodeAndSetSite() {
	busy.value = "geocode";
	geoError.value = "";
	try {
		const updated = await call("swiftservice.api.set_visit_site_location", {
			name: props.doc.name,
			address: pinAddressDraft.value.trim(),
		});
		toast.success("Customer pin set from address");
		emit("updated", updated);
	} catch (e) {
		geoError.value = e?.messages?.[0] || e?.message || "Could not find address";
		toast.error(geoError.value);
	} finally {
		busy.value = "";
	}
}

async function pinSiteHere() {
	busy.value = "pin";
	geoError.value = "";
	try {
		const geo = await getGeo();
		if (!isValidCoord(geo.gps_lat, geo.gps_lng)) {
			throw new Error("Invalid GPS — try outdoors");
		}
		const updated = await call("swiftservice.api.set_visit_site_location", {
			name: props.doc.name,
			gps_lat: geo.gps_lat,
			gps_lng: geo.gps_lng,
			address: pinAddressDraft.value.trim() || undefined,
		});
		toast.success("Customer pin set to your location");
		emit("updated", updated);
	} catch (e) {
		geoError.value = e?.messages?.[0] || e?.message || "Could not set pin";
		toast.error(geoError.value);
	} finally {
		busy.value = "";
	}
}

async function doCheckIn() {
	busy.value = "in";
	geoError.value = "";
	try {
		const geo = await getGeo();
		if (!isValidCoord(geo.gps_lat, geo.gps_lng)) {
			throw new Error("Invalid GPS reading. Try again outdoors.");
		}
		const updated = await call("swiftservice.api.check_in_visit", {
			name: props.doc.name,
			gps_lat: geo.gps_lat,
			gps_lng: geo.gps_lng,
			gps_accuracy: geo.gps_accuracy,
			force: 1,
		});
		toast.success("Checked in at site");
		emit("updated", updated);
	} catch (e) {
		geoError.value = e?.messages?.[0] || e?.message || "Check-in failed";
		toast.error(geoError.value);
	} finally {
		busy.value = "";
	}
}

async function doCheckOut() {
	busy.value = "out";
	geoError.value = "";
	try {
		const geo = await getGeo();
		if (!isValidCoord(geo.gps_lat, geo.gps_lng)) {
			throw new Error("Invalid GPS reading. Try again outdoors.");
		}
		const updated = await call("swiftservice.api.check_out_visit", {
			name: props.doc.name,
			diagnosis_notes: props.doc.diagnosis_notes || props.doc.work_done,
			gps_lat: geo.gps_lat,
			gps_lng: geo.gps_lng,
		});
		toast.success("Checked out");
		emit("updated", updated);
	} catch (e) {
		geoError.value = e?.messages?.[0] || e?.message || "Check-out failed";
		toast.error(geoError.value);
	} finally {
		busy.value = "";
	}
}

onMounted(() => {
	pinAddressDraft.value = siteAddress.value || "";
	refreshLive();
	startLiveWatch();
	fetchLiveTracking();
	trackingTimer = setInterval(fetchLiveTracking, 8000);
});

onBeforeUnmount(() => {
	stopLiveWatch();
	if (trackingTimer) {
		clearInterval(trackingTimer);
		trackingTimer = null;
	}
});

watch(
	() => props.doc?.name,
	() => {
		pinAddressDraft.value = siteAddress.value || "";
		refreshLive();
	},
);

watch(siteAddress, (v) => {
	if (!pinAddressDraft.value && v) pinAddressDraft.value = v;
});
</script>
