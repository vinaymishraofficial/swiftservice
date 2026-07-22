<template>
	<div
		v-if="avatars?.length"
		class="flex items-center"
		:class="avatars.length > 1 ? 'flex-row-reverse justify-end' : 'gap-2'"
	>
		<template v-if="avatars.length === 1">
			<Tooltip :text="avatars[0].name">
				<div class="flex min-w-0 items-center gap-2">
					<Avatar
						shape="circle"
						size="sm"
						:image="avatars[0].image"
						:label="avatars[0].label || avatars[0].name"
					/>
					<span v-if="showLabel" class="truncate text-sm text-ink-gray-8">
						{{ avatars[0].label || avatars[0].name }}
					</span>
				</div>
			</Tooltip>
		</template>
		<template v-else>
			<Tooltip v-for="avatar in reverseAvatars" :key="avatar.name" :text="avatar.label || avatar.name">
				<Avatar
					class="-mr-1.5 ring-2 ring-surface-white transition hover:z-10 hover:scale-110"
					shape="circle"
					size="sm"
					:image="avatar.image"
					:label="avatar.label || avatar.name"
				/>
			</Tooltip>
			<span
				v-if="avatars.length > maxVisible"
				class="ml-1 text-xs text-ink-gray-5"
			>
				+{{ avatars.length - maxVisible }}
			</span>
		</template>
	</div>
	<span v-else class="text-ink-gray-4">—</span>
</template>

<script setup>
import { computed } from "vue";
import { Avatar, Tooltip } from "frappe-ui";

const props = defineProps({
	avatars: { type: Array, default: () => [] },
	showLabel: { type: Boolean, default: false },
	maxVisible: { type: Number, default: 4 },
});

const visible = computed(() => (props.avatars || []).slice(0, props.maxVisible));
const reverseAvatars = computed(() => [...visible.value].reverse());
</script>
