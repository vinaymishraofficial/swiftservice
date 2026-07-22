<template>
	<div class="flex h-full flex-col items-center justify-center gap-3 p-8">
		<div class="text-lg font-medium text-ink-gray-9">Page not found</div>
		<div class="text-sm text-ink-gray-5">{{ $route.fullPath }}</div>
		<Button label="Go to Dashboard" variant="solid" @click="$router.push('/dashboard')" />
	</div>
</template>

<script setup>
import { Button } from "frappe-ui";
</script>
