<template>
	<div class="flex min-w-0 items-center">
		<Breadcrumbs v-if="items?.length" :items="items">
			<template v-if="$slots.prefix" #prefix="slotProps">
				<slot name="prefix" v-bind="slotProps" />
			</template>
			<template v-if="$slots.suffix" #suffix="slotProps">
				<slot name="suffix" v-bind="slotProps" />
			</template>
		</Breadcrumbs>

		<template v-else>
			<router-link
				v-if="parentRoute"
				:to="parentRoute"
				class="rounded px-0.5 py-1 text-lg font-medium text-ink-gray-5 hover:text-ink-gray-7 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
			>
				{{ parent }}
			</router-link>
			<span v-else class="px-0.5 py-1 text-lg font-medium text-ink-gray-5">
				{{ parent }}
			</span>

			<template v-if="current">
				<span class="mx-0.5 text-base text-ink-gray-4" aria-hidden="true">/</span>
				<Dropdown v-if="viewOptions?.length" :options="viewOptions">
					<template #default="{ open }">
						<Button
							variant="ghost"
							class="text-lg font-medium text-ink-gray-9"
							:label="current"
							:iconRight="open ? 'chevron-up' : 'chevron-down'"
						>
							<template #prefix>
								<component :is="currentIcon" class="size-4 text-ink-gray-7" />
							</template>
						</Button>
					</template>
				</Dropdown>
				<span
					v-else
					class="flex items-center gap-1.5 truncate rounded px-0.5 py-1 text-lg font-medium text-ink-gray-9"
				>
					<component
						v-if="currentIcon"
						:is="currentIcon"
						class="size-4 shrink-0 text-ink-gray-7"
					/>
					<span class="truncate">{{ current }}</span>
				</span>
			</template>
		</template>

		<slot />
	</div>
</template>

<script setup>
import { Breadcrumbs, Button, Dropdown } from "frappe-ui";
import LucideList from "~icons/lucide/list";

defineProps({
	/** Full Breadcrumbs items — if set, used instead of parent/current */
	items: { type: Array, default: null },
	parent: { type: String, default: "" },
	parentRoute: { type: [String, Object], default: null },
	current: { type: String, default: "" },
	currentIcon: { type: [Object, Function], default: () => LucideList },
	viewOptions: { type: Array, default: () => [] },
});
</script>
