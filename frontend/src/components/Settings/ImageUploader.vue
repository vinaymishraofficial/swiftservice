<template>
	<FileUploader :file-types="imageType" @success="(file) => emit('upload', file.file_url)">
		<template #default="{ progress, uploading, openFileSelector }">
			<div class="flex items-center gap-1">
				<Button
					:label="uploading ? `Uploading ${progress}%` : imageUrl ? 'Change' : 'Upload'"
					@click="openFileSelector"
				/>
				<Button v-if="imageUrl" label="Remove" @click="emit('remove')" />
			</div>
		</template>
	</FileUploader>
</template>

<script setup>
import { Button, FileUploader } from "frappe-ui";

defineProps({
	imageUrl: { type: String, default: "" },
	imageType: { type: String, default: "image/*" },
});
const emit = defineEmits(["upload", "remove"]);
</script>
