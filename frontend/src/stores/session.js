import { defineStore } from "pinia";
import { call } from "frappe-ui";
import { computed, ref } from "vue";

export const sessionStore = defineStore("session", () => {
	const user = ref(null);
	const fullName = ref("");
	const userImage = ref("");

	const isLoggedIn = computed(() => Boolean(user.value && user.value !== "Guest"));

	async function fetchUser() {
		try {
			const bootUser = window.boot?.user;
			if (bootUser?.name && bootUser.name !== "Guest") {
				user.value = bootUser.name;
				fullName.value = bootUser.full_name || bootUser.name;
				userImage.value = bootUser.user_image || "";
				return;
			}
			const data = await call("frappe.auth.get_logged_user");
			user.value = data;
			if (data && data !== "Guest") {
				const info = await call("frappe.client.get_value", {
					doctype: "User",
					filters: { name: data },
					fieldname: ["full_name", "user_image"],
				});
				fullName.value = info?.full_name || data;
				userImage.value = info?.user_image || "";
			}
		} catch (e) {
			user.value = "Guest";
		}
	}

	function logout() {
		window.location.href = "/api/method/logout?redirect-to=/login";
	}

	return {
		user,
		fullName,
		userImage,
		isLoggedIn,
		fetchUser,
		logout,
	};
});
