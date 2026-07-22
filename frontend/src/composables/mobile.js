import { useMediaQuery } from "@vueuse/core";
import { ref } from "vue";

/** Phone-first breakpoint (matches FCRM: < 768px). */
export const isMobileView = useMediaQuery("(max-width: 767px)");

/** Mobile drawer open state */
export const mobileSidebarOpened = ref(false);
