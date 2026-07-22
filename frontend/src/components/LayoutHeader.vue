<template>
	<header
		class="flex h-10.5 shrink-0 items-center justify-between border-b border-outline-gray-2 bg-surface-white py-[7px] pl-2 pr-5 sm:pl-5"
	>
		<div class="flex min-w-0 items-center gap-2">
			<slot name="left-header" />
		</div>
		<div class="flex shrink-0 items-center gap-2">
			<slot name="right-header" />
		</div>
	</header>
</template>
