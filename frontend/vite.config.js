import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";
import Icons from "unplugin-icons/vite";

export default defineConfig({
	plugins: [vue(), Icons({ compiler: "vue3" })],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
			vue: path.resolve(__dirname, "node_modules/vue"),
		},
		dedupe: ["vue"],
	},
	build: {
		outDir: "../swiftservice/public/frontend",
		// Keep previous assets until new files are written — emptyOutDir caused
		// intermittent white screens when the SPA was loaded mid-build.
		emptyOutDir: false,
		cssCodeSplit: false,
		commonjsOptions: {
			include: [/tailwind.config.js/, /node_modules/],
		},
		rollupOptions: {
			output: {
				entryFileNames: "assets/swiftservice.js",
				chunkFileNames: "assets/[name].js",
				assetFileNames: "assets/swiftservice.[ext]",
			},
		},
	},
	optimizeDeps: {
		include: ["feather-icons", "showdown", "engine.io-client"],
	},
});
