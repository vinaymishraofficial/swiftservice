<template>
	<div class="flex h-full min-h-[420px] flex-col">
		<div class="flex-1 space-y-6 overflow-y-auto px-6 py-6 text-ink-gray-8">
			<div>
				<p class="text-sm text-ink-gray-5">Manage your profile & login information.</p>
			</div>

			<div class="flex items-center gap-4">
				<Avatar
					shape="circle"
					size="3xl"
					:image="form.user_image"
					:label="form.full_name || form.email || '?'"
				/>
				<div>
					<div class="mb-2 text-sm font-medium text-ink-gray-8">
						{{ form.full_name || "Your name" }}
					</div>
					<ImageUploader
						:image-url="form.user_image"
						@upload="(url) => (form.user_image = url)"
						@remove="() => (form.user_image = '')"
					/>
				</div>
			</div>

			<div class="grid max-w-xl grid-cols-1 gap-4 sm:grid-cols-2">
				<FormControl label="Full Name" v-model="form.full_name" />
				<FormControl label="Email" :model-value="form.email" disabled />
				<FormControl label="Phone" v-model="form.phone" />
				<FormControl label="Mobile No" v-model="form.mobile_no" />
			</div>
			<ErrorMessage :message="error" />
		</div>
		<div
			class="flex shrink-0 items-center justify-end gap-2 border-t border-outline-gray-2 bg-surface-white px-6 py-3"
		>
			<Button variant="solid" label="Update" :loading="saving" @click="save" />
		</div>
	</div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { Avatar, Button, ErrorMessage, FormControl, call, toast } from "frappe-ui";
import ImageUploader from "./ImageUploader.vue";
import { sessionStore } from "@/stores/session";

const session = sessionStore();
const form = reactive({
	full_name: "",
	email: "",
	phone: "",
	mobile_no: "",
	user_image: "",
});
const saving = ref(false);
const error = ref("");

async function load() {
	error.value = "";
	try {
		const data = await call("swiftservice.api.get_user_profile");
		Object.assign(form, data || {});
	} catch (e) {
		error.value = e?.messages?.[0] || e?.message || "Could not load profile";
		toast.error(error.value);
	}
}

async function save() {
	saving.value = true;
	error.value = "";
	try {
		const data = await call("swiftservice.api.save_user_profile", { doc: form });
		Object.assign(form, data);
		session.fullName = data.full_name || session.fullName;
		session.userImage = data.user_image || "";
		toast.success("Profile updated");
	} catch (e) {
		error.value = e?.messages?.[0] || e?.message || "Save failed";
		toast.error(error.value);
	} finally {
		saving.value = false;
	}
}

onMounted(load);
</script>
