import { useStorage } from "@vueuse/core";

/** `full` = edge-to-edge content · `box` = centered max-width (Desk-style) */
export const contentWidth = useStorage("ss_content_width", "full");

export function setContentWidth(mode) {
	contentWidth.value = mode === "box" ? "box" : "full";
}

export function useContentWidth() {
	return { contentWidth, setContentWidth };
}
