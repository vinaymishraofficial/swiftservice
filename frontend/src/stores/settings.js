import { call } from "frappe-ui";
import { computed, reactive, ref } from "vue";

const DEFAULT_LOGO = "/assets/swiftservice/logo-white.png";
const DEFAULT_FAVICON = "/assets/swiftservice/favicon.png";

const settings = ref(null);
const brand = reactive({
	name: "SwiftService",
	logo: DEFAULT_LOGO,
	favicon: DEFAULT_FAVICON,
});
const loading = ref(false);
let loaded = false;

function withCacheBust(url) {
	if (!url) return url;
	const sep = url.includes("?") ? "&" : "?";
	return `${url}${sep}v=${Date.now()}`;
}

function setFavicon(url) {
	try {
		const href = withCacheBust(url || DEFAULT_FAVICON);
		let link = document.querySelector('link[rel="icon"][type="image/png"]');
		if (!link) {
			link = document.createElement("link");
			link.rel = "icon";
			link.type = "image/png";
			document.head.appendChild(link);
		}
		link.href = href;
	} catch (e) {
		/* ignore favicon errors */
	}
}

function applyBrand(doc) {
	brand.name = doc?.brand_name || "SwiftService";
	brand.logo = doc?.brand_logo || DEFAULT_LOGO;
	brand.favicon = doc?.favicon || DEFAULT_FAVICON;
	setFavicon(brand.favicon);
	document.title = brand.name;
}

export function useSettings() {
	async function load(force = false) {
		if (loaded && !force) return settings.value;
		loading.value = true;
		try {
			const data = await call("swiftservice.api.get_settings");
			settings.value = data || {};
			applyBrand(settings.value);
			loaded = true;
		} catch (e) {
			settings.value = {};
			applyBrand({});
		} finally {
			loading.value = false;
		}
		return settings.value;
	}

	async function save(doc) {
		loading.value = true;
		try {
			const data = await call("swiftservice.api.save_settings", { doc });
			settings.value = data;
			applyBrand(data);
			return data;
		} finally {
			loading.value = false;
		}
	}

	return {
		settings,
		brand,
		loading,
		load,
		save,
		isLoaded: computed(() => loaded),
	};
}
