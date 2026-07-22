<template>
	<Popover placement="bottom-end">
		<template #target="{ togglePopover, isOpen }">
			<button
				type="button"
				class="inline-flex h-8 items-center gap-1.5 rounded-md border border-outline-gray-2 bg-surface-white px-2 text-sm text-ink-gray-8 transition hover:bg-surface-gray-1"
				:class="isOpen ? 'border-outline-gray-3 bg-surface-gray-1' : ''"
				@click="togglePopover()"
			>
				<template v-if="assignees.length">
					<MultipleAvatar :avatars="assignees" />
				</template>
				<template v-else>
					<span class="lucide-user-plus size-3.5 text-ink-gray-6" aria-hidden="true" />
					<span class="pr-0.5">Assign</span>
				</template>
			</button>
		</template>
		<template #body>
			<div
				class="my-1 w-[min(340px,90vw)] rounded-lg border border-outline-gray-2 bg-surface-modal p-3 shadow-xl"
			>
				<div class="mb-2 text-sm font-medium text-ink-gray-9">Members</div>

				<div v-if="assignees.length" class="mb-3 space-y-1">
					<div
						v-for="a in assignees"
						:key="a.name"
						class="flex items-center gap-2 rounded-md px-1 py-1 hover:bg-surface-gray-2"
					>
						<Avatar shape="circle" size="sm" :image="a.image" :label="a.label || a.name" />
						<div class="min-w-0 flex-1 truncate text-sm text-ink-gray-8">
							{{ a.label || a.name }}
						</div>
						<button
							type="button"
							class="rounded p-1 text-ink-gray-4 hover:bg-surface-gray-3 hover:text-ink-gray-8"
							:disabled="busy"
							title="Remove"
							@click="removeUser(a.name)"
						>
							<span class="lucide-x size-3.5" aria-hidden="true" />
						</button>
					</div>
				</div>
				<div v-else class="mb-3 text-xs text-ink-gray-5">No one assigned yet</div>

				<Combobox
					v-model="picked"
					:options="userOptions"
					placeholder="Search users…"
					open-on-focus
					class="w-full"
					@update:modelValue="onPick"
				>
					<template #item-prefix="{ item }">
						<Avatar
							v-if="item.type !== 'custom'"
							:image="item.image"
							:label="item.label"
							size="sm"
						/>
					</template>
					<template #item-label="{ item }">
						<div class="min-w-0">
							<div class="truncate text-sm text-ink-gray-9">{{ item.label }}</div>
							<div v-if="item.email" class="truncate text-xs text-ink-gray-5">
								{{ item.email }}
							</div>
						</div>
					</template>
				</Combobox>

				<div class="mt-2 flex justify-between">
					<Button
						variant="ghost"
						label="Assign to me"
						size="sm"
						:disabled="busy"
						@click="assignMe"
					/>
				</div>
				<ErrorMessage class="mt-2" :message="error" />
			</div>
		</template>
	</Popover>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Avatar, Button, Combobox, ErrorMessage, Popover, call, toast } from "frappe-ui";
import MultipleAvatar from "@/components/MultipleAvatar.vue";
import { sessionStore } from "@/stores/session";

const props = defineProps({
	doctype: { type: String, required: true },
	docname: { type: String, required: true },
});

const emit = defineEmits(["updated"]);
const session = sessionStore();
const assignees = ref([]);
const picked = ref("");
const busy = ref(false);
const error = ref("");
const users = ref([]);

const userOptions = computed(() =>
	users.value
		.filter((u) => !assignees.value.some((a) => a.name === u.value))
		.map((u) => ({
			label: u.label,
			value: u.value,
			email: u.email,
			image: u.image,
		})),
);

async function loadUsers(txt = "") {
	try {
		const rows = await call("swiftservice.api.search_link", {
			doctype: "User",
			txt,
			filters: { enabled: 1 },
			limit: 20,
		});
		users.value = (rows || []).map((r) => ({
			value: r.value,
			label: r.label || r.value,
			email: r.value,
			image: r.image || "",
		}));
	} catch (e) {
		users.value = [];
	}
}

async function load() {
	if (!props.doctype || !props.docname) return;
	try {
		assignees.value =
			(await call("swiftservice.api.get_assignments", {
				doctype: props.doctype,
				name: props.docname,
			})) || [];
	} catch (e) {
		assignees.value = [];
	}
}

async function addUsers(list) {
	if (!list?.length) return;
	busy.value = true;
	error.value = "";
	try {
		assignees.value = await call("swiftservice.api.assign_to", {
			doctype: props.doctype,
			name: props.docname,
			users: list,
		});
		emit("updated", assignees.value);
		toast.success("Assigned");
	} catch (e) {
		error.value = e?.messages?.[0] || e?.message || "Assignment failed";
		toast.error(error.value);
	} finally {
		busy.value = false;
	}
}

async function removeUser(user) {
	busy.value = true;
	error.value = "";
	try {
		assignees.value = await call("swiftservice.api.remove_assignment", {
			doctype: props.doctype,
			name: props.docname,
			user,
		});
		emit("updated", assignees.value);
		toast.success("Removed");
	} catch (e) {
		error.value = e?.messages?.[0] || e?.message || "Remove failed";
		toast.error(error.value);
	} finally {
		busy.value = false;
	}
}

async function onPick(user) {
	if (!user) return;
	await addUsers([user]);
	picked.value = "";
}

async function assignMe() {
	const me = session.user;
	if (!me || me === "Guest") return;
	if (assignees.value.some((a) => a.name === me)) return;
	await addUsers([me]);
}

watch(
	() => [props.doctype, props.docname],
	() => {
		load();
		loadUsers();
	},
	{ immediate: true },
);
</script>
