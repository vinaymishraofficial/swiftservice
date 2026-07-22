<template>
	<div class="rounded-xl border border-outline-gray-2 bg-surface-gray-2">
		<div
			class="relative w-full overflow-hidden rounded-t-xl"
			:class="tall ? 'h-[min(70vh,32rem)] sm:h-[min(75vh,36rem)]' : 'h-64 sm:h-80'"
		>
			<!-- Keep map DOM always mounted — Leaflet breaks with v-if/v-else remounts -->
			<div ref="mapEl" class="ss-map absolute inset-0 z-0 h-full w-full" />
			<div
				v-if="!hasAnyPoint"
				class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-1 bg-surface-gray-2 px-4 text-center text-p-sm text-ink-gray-5"
			>
				<span class="lucide-map-pin size-6 opacity-40" aria-hidden="true" />
				{{ emptyText }}
			</div>

			<!-- Basemap switcher (Street / Satellite / Hybrid) -->
			<div
				v-if="hasAnyPoint"
				class="absolute bottom-3 left-3 z-[500] flex overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white/95 shadow-md backdrop-blur"
			>
				<button
					v-for="opt in basemapOptions"
					:key="opt.id"
					type="button"
					class="px-2.5 py-1.5 text-[11px] font-medium transition"
					:class="
						basemap === opt.id
							? 'bg-surface-gray-7 text-ink-white'
							: 'text-ink-gray-7 hover:bg-surface-gray-2'
					"
					@click="setBasemap(opt.id)"
				>
					{{ opt.label }}
				</button>
			</div>
		</div>

		<!-- Location list with names -->
		<div
			v-if="validPoints.length"
			class="space-y-2 border-t border-outline-gray-2 bg-surface-white px-3 py-3"
		>
			<div class="text-[11px] font-semibold uppercase tracking-wide text-ink-gray-5">
				Pins
			</div>
			<div
				v-for="(p, i) in validPoints"
				:key="`${p.label}-${p.lat}-${p.lng}-${i}`"
				class="flex items-start gap-2.5"
			>
				<span
					class="mt-1 size-2.5 shrink-0 rounded-full"
					:style="{ background: p.color || '#c04070' }"
				/>
				<div class="min-w-0 flex-1">
					<div class="text-sm font-medium text-ink-gray-9">{{ p.label || "Location" }}</div>
					<div v-if="displayName(p)" class="text-[12px] leading-snug text-ink-gray-7">
						{{ displayName(p) }}
					</div>
					<div class="mt-0.5 font-mono text-[11px] tabular-nums text-ink-gray-5">
						{{ Number(p.lat).toFixed(5) }}, {{ Number(p.lng).toFixed(5) }}
					</div>
				</div>
			</div>
			<div class="flex flex-wrap items-center justify-end gap-2 pt-1">
				<a
					v-if="mapsUrl"
					:href="mapsUrl"
					target="_blank"
					rel="noopener"
					class="shrink-0 text-xs font-medium text-ink-gray-8 underline"
				>
					Open navigation
				</a>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useStorage } from "@vueuse/core";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const props = defineProps({
	/** [{ lat, lng, label, name?, address?, color?, primary? }] */
	points: { type: Array, default: () => [] },
	emptyText: { type: String, default: "No GPS coordinates yet" },
	/** Larger map for full-width GPS tab */
	tall: { type: Boolean, default: false },
	/** Prefer this label when fitting the map (e.g. Customer site) */
	focusLabel: { type: String, default: "" },
});

const mapEl = ref(null);
const resolvedNames = ref({}); // key -> place name from reverse geocode
let map = null;
let layerGroup = null;
let baseLayer = null;
let overlayLayer = null;

const basemap = useStorage("ss_map_basemap", "street");
const basemapOptions = [
	{ id: "street", label: "Street" },
	{ id: "satellite", label: "Satellite" },
	{ id: "hybrid", label: "Hybrid" },
];

const TILES = {
	street: {
		url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
		options: {
			maxZoom: 19,
			attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
		},
	},
	satellite: {
		url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
		options: {
			maxZoom: 19,
			attribution: "Tiles &copy; Esri",
		},
	},
	hybrid: {
		url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
		options: {
			maxZoom: 19,
			attribution: "Tiles &copy; Esri",
		},
		overlayUrl:
			"https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
	},
};

const validPoints = computed(() =>
	(props.points || [])
		.filter((p) => isValidCoord(p?.lat, p?.lng))
		.map((p) => ({
			...p,
			_key: pointKey(p),
		})),
);

const hasAnyPoint = computed(() => validPoints.value.length > 0);

const mapsUrl = computed(() => {
	const preferred =
		validPoints.value.find((p) => p.primary) ||
		(props.focusLabel
			? validPoints.value.find((p) => p.label === props.focusLabel)
			: null) ||
		validPoints.value[0];
	if (!preferred) return "";
	return `https://www.google.com/maps/dir/?api=1&destination=${preferred.lat},${preferred.lng}&travelmode=driving`;
});

function pointKey(p) {
	return `${Number(p.lat).toFixed(5)},${Number(p.lng).toFixed(5)}`;
}

function isValidCoord(lat, lng) {
	const a = Number(lat);
	const b = Number(lng);
	if (!Number.isFinite(a) || !Number.isFinite(b)) return false;
	if (Math.abs(a) < 0.00001 && Math.abs(b) < 0.00001) return false;
	if (a < -90 || a > 90 || b < -180 || b > 180) return false;
	return true;
}

function displayName(p) {
	return (
		p.address ||
		p.name ||
		resolvedNames.value[p._key || pointKey(p)] ||
		""
	);
}

function escapeHtml(s) {
	return String(s || "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;");
}

function shortName(text, max = 36) {
	const t = String(text || "").trim();
	if (!t) return "";
	if (t.length <= max) return t;
	return `${t.slice(0, max - 1)}…`;
}

function labeledIcon(p) {
	const color = p.color || "#c04070";
	const title = escapeHtml(p.label || "Location");
	const place = shortName(displayName(p), 34);
	const placeHtml = place
		? `<div class="ss-pin-place">${escapeHtml(place)}</div>`
		: `<div class="ss-pin-place ss-pin-place-muted">Resolving…</div>`;

	return L.divIcon({
		className: "ss-pin-wrap",
		iconSize: [160, 54],
		iconAnchor: [14, 40],
		popupAnchor: [0, -40],
		html: `<div class="ss-pin">
			<svg width="28" height="40" viewBox="0 0 28 40" aria-hidden="true">
				<path fill="${color}" stroke="#fff" stroke-width="1.5" d="M14 0C6.3 0 0 6.3 0 14c0 10.5 14 26 14 26s14-15.5 14-26C28 6.3 21.7 0 14 0z"/>
				<circle cx="14" cy="14" r="5" fill="#fff"/>
			</svg>
			<div class="ss-pin-bubble">
				<div class="ss-pin-title">${title}</div>
				${placeHtml}
			</div>
		</div>`,
	});
}

function popupHtml(p) {
	const title = escapeHtml(p.label || "Location");
	const place = escapeHtml(displayName(p));
	const coords = `${Number(p.lat).toFixed(5)}, ${Number(p.lng).toFixed(5)}`;
	return `<div class="ss-map-popup">
		<div class="ss-map-popup-title">${title}</div>
		${place ? `<div class="ss-map-popup-addr">${place}</div>` : ""}
		<div class="ss-map-popup-coords">${coords}</div>
	</div>`;
}

async function reverseGeocode(lat, lng) {
	const key = `${Number(lat).toFixed(5)},${Number(lng).toFixed(5)}`;
	if (resolvedNames.value[key]) return resolvedNames.value[key];
	try {
		const url = new URL("https://nominatim.openstreetmap.org/reverse");
		url.searchParams.set("lat", String(lat));
		url.searchParams.set("lon", String(lng));
		url.searchParams.set("format", "json");
		url.searchParams.set("zoom", "18");
		url.searchParams.set("addressdetails", "1");
		const res = await fetch(url.toString(), {
			headers: { Accept: "application/json" },
		});
		if (!res.ok) return "";
		const data = await res.json();
		const addr = data?.address || {};
		const parts = [
			addr.road || addr.pedestrian || addr.neighbourhood,
			addr.suburb || addr.village || addr.town || addr.city_district || addr.city,
			addr.state,
		].filter(Boolean);
		const line = parts.join(", ") || data?.display_name || "";
		if (line) {
			resolvedNames.value = { ...resolvedNames.value, [key]: line };
		}
		return line;
	} catch {
		return "";
	}
}

async function resolveMissingNames() {
	const jobs = [];
	for (const p of validPoints.value) {
		if (p.address || p.name) continue;
		const key = pointKey(p);
		if (resolvedNames.value[key]) continue;
		jobs.push(
			reverseGeocode(p.lat, p.lng).then(() => {
				/* names reactive → re-render */
			}),
		);
	}
	if (jobs.length) {
		await Promise.all(jobs);
		renderMap();
	}
}

function applyBasemap() {
	if (!map) return;
	const cfg = TILES[basemap.value] || TILES.street;
	if (baseLayer) {
		map.removeLayer(baseLayer);
		baseLayer = null;
	}
	if (overlayLayer) {
		map.removeLayer(overlayLayer);
		overlayLayer = null;
	}
	baseLayer = L.tileLayer(cfg.url, cfg.options).addTo(map);
	if (cfg.overlayUrl) {
		overlayLayer = L.tileLayer(cfg.overlayUrl, {
			maxZoom: 19,
			attribution: "",
		}).addTo(map);
	}
}

function setBasemap(id) {
	basemap.value = id;
	applyBasemap();
}

function ensureMap() {
	if (!mapEl.value) return false;
	if (map) return true;
	map = L.map(mapEl.value, {
		zoomControl: true,
		attributionControl: true,
	});
	applyBasemap();
	layerGroup = L.layerGroup().addTo(map);
	return true;
}

function renderMap() {
	if (!hasAnyPoint.value) return;
	if (!ensureMap()) return;

	const pts = validPoints.value.map((p) => [Number(p.lat), Number(p.lng)]);
	layerGroup.clearLayers();
	validPoints.value.forEach((p) => {
		const marker = L.marker([Number(p.lat), Number(p.lng)], {
			icon: labeledIcon(p),
			title: `${p.label || "Location"}${displayName(p) ? ` — ${displayName(p)}` : ""}`,
		});
		marker.bindPopup(popupHtml(p), { maxWidth: 280 });
		marker.addTo(layerGroup);
	});

	// Prefer destination pin for view when focusing a customer site
	const focus =
		validPoints.value.find((p) => p.primary) ||
		(props.focusLabel
			? validPoints.value.find((p) => p.label === props.focusLabel)
			: null);

	if (focus && pts.length === 1) {
		map.setView([Number(focus.lat), Number(focus.lng)], 17);
	} else if (pts.length === 1) {
		map.setView(pts[0], 17);
	} else {
		map.fitBounds(L.latLngBounds(pts), { padding: [48, 48], maxZoom: 16 });
	}

	requestAnimationFrame(() => {
		map?.invalidateSize();
		setTimeout(() => map?.invalidateSize(), 120);
	});
}

function destroyMap() {
	if (map) {
		map.remove();
		map = null;
		layerGroup = null;
		baseLayer = null;
		overlayLayer = null;
	}
}

async function syncMap() {
	await nextTick();
	if (!hasAnyPoint.value) return;
	renderMap();
	resolveMissingNames();
}

onMounted(syncMap);

watch(
	() => [hasAnyPoint.value, JSON.stringify(validPoints.value), props.tall],
	() => {
		syncMap();
	},
);

watch(resolvedNames, () => {
	if (hasAnyPoint.value) renderMap();
});

onBeforeUnmount(destroyMap);
</script>

<style scoped>
.ss-map :deep(.leaflet-container),
.ss-map.leaflet-container {
	width: 100%;
	height: 100%;
	font: inherit;
	background: rgb(var(--surface-gray-2));
}

.ss-map :deep(.ss-pin-wrap) {
	background: transparent;
	border: none;
}

.ss-map :deep(.ss-pin) {
	display: flex;
	align-items: flex-start;
	gap: 4px;
	pointer-events: none;
}

.ss-map :deep(.ss-pin svg) {
	flex-shrink: 0;
	filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.35));
}

.ss-map :deep(.ss-pin-bubble) {
	margin-top: 2px;
	max-width: 11.5rem;
	border-radius: 8px;
	border: 1px solid rgba(0, 0, 0, 0.08);
	background: #fff;
	padding: 4px 8px;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
	line-height: 1.25;
}

.ss-map :deep(.ss-pin-title) {
	font-size: 11px;
	font-weight: 700;
	color: #111827;
}

.ss-map :deep(.ss-pin-place) {
	margin-top: 1px;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	font-size: 10px;
	color: #4b5563;
}

.ss-map :deep(.ss-pin-place-muted) {
	color: #9ca3af;
	font-style: italic;
}

.ss-map :deep(.ss-map-popup-title) {
	font-size: 13px;
	font-weight: 600;
	color: #1f2937;
}

.ss-map :deep(.ss-map-popup-addr) {
	margin-top: 4px;
	font-size: 12px;
	line-height: 1.35;
	color: #4b5563;
}

.ss-map :deep(.ss-map-popup-coords) {
	margin-top: 6px;
	font-size: 11px;
	font-variant-numeric: tabular-nums;
	color: #9ca3af;
}
</style>
