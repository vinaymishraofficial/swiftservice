<template>
	<div class="flex flex-col gap-4">
		<!-- Header actions -->
		<div class="flex items-center justify-between gap-2">
			<div class="text-base font-medium text-ink-gray-9">Emails</div>
			<Button
				v-if="!composing"
				variant="solid"
				label="New Email"
				iconLeft="lucide-mail"
				size="sm"
				@click="openComposer()"
			/>
		</div>

		<!-- ERPNext-style composer -->
		<div
			v-if="composing"
			class="overflow-hidden rounded-xl border border-outline-gray-2 bg-surface-white shadow-sm"
		>
			<div
				class="flex items-center justify-between border-b border-outline-gray-1 px-4 py-2.5"
			>
				<div class="text-sm font-semibold text-ink-gray-9">New Email</div>
				<button
					type="button"
					class="rounded p-1 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8"
					@click="closeComposer"
				>
					×
				</button>
			</div>

			<div class="space-y-0 divide-y divide-outline-gray-1 px-0">
				<!-- From -->
				<div v-if="fromOptions.length" class="flex items-center gap-3 px-4 py-2">
					<span class="w-14 shrink-0 text-xs font-medium uppercase tracking-wide text-ink-gray-5">
						From
					</span>
					<select
						v-model="form.sender"
						class="form-input h-8 flex-1 rounded border-0 bg-surface-gray-2 px-2 text-sm focus:bg-surface-white focus:ring-1 focus:ring-outline-gray-3"
					>
						<option v-for="a in fromOptions" :key="a.value" :value="a.value">
							{{ a.label }}
						</option>
					</select>
				</div>

				<!-- To + CC/BCC toggles -->
				<div class="flex items-start gap-3 px-4 py-2">
					<span class="mt-2 w-14 shrink-0 text-xs font-medium uppercase tracking-wide text-ink-gray-5">
						To
					</span>
					<div class="min-w-0 flex-1">
						<MultiSelectEmailInput v-model="form.to" placeholder="Recipients…" />
					</div>
					<div class="mt-1 flex shrink-0 gap-1">
						<button
							type="button"
							class="rounded px-2 py-1 text-xs font-medium"
							:class="showCc ? 'bg-surface-gray-3 text-ink-gray-9' : 'text-ink-gray-5 hover:bg-surface-gray-2'"
							@click="showCc = !showCc"
						>
							CC
						</button>
						<button
							type="button"
							class="rounded px-2 py-1 text-xs font-medium"
							:class="showBcc ? 'bg-surface-gray-3 text-ink-gray-9' : 'text-ink-gray-5 hover:bg-surface-gray-2'"
							@click="showBcc = !showBcc"
						>
							BCC
						</button>
					</div>
				</div>

				<div v-if="showCc" class="flex items-start gap-3 px-4 py-2">
					<span class="mt-2 w-14 shrink-0 text-xs font-medium uppercase tracking-wide text-ink-gray-5">
						CC
					</span>
					<div class="min-w-0 flex-1">
						<MultiSelectEmailInput v-model="form.cc" placeholder="CC…" />
					</div>
				</div>

				<div v-if="showBcc" class="flex items-start gap-3 px-4 py-2">
					<span class="mt-2 w-14 shrink-0 text-xs font-medium uppercase tracking-wide text-ink-gray-5">
						BCC
					</span>
					<div class="min-w-0 flex-1">
						<MultiSelectEmailInput v-model="form.bcc" placeholder="BCC…" />
					</div>
				</div>

				<!-- Subject -->
				<div class="flex items-center gap-3 px-4 py-2">
					<span class="w-14 shrink-0 text-xs font-medium uppercase tracking-wide text-ink-gray-5">
						Subject
					</span>
					<input
						v-model="form.subject"
						type="text"
						class="form-input h-8 flex-1 rounded border-0 bg-surface-gray-2 px-2 text-sm focus:bg-surface-white focus:ring-1 focus:ring-outline-gray-3"
						placeholder="Subject"
					/>
				</div>

				<!-- Body -->
				<div class="px-4 py-3">
					<TextEditor
						:key="editorKey"
						:content="form.content"
						placeholder="Message…"
						:fixed-menu="SAFE_TEXT_EDITOR_BUTTONS"
						:bubble-menu="false"
						:floating-menu="false"
						editor-class="prose-sm min-h-[10rem] max-w-none px-1 py-1 text-sm text-ink-gray-9"
						@change="(html) => (form.content = html)"
					/>
				</div>

				<!-- Attachments (always visible while composing) -->
				<div class="space-y-2 border-t border-outline-gray-1 px-4 py-3">
					<div class="flex items-center justify-between gap-2">
						<div class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">
							Attachments
							<span v-if="selectedAttachmentRows.length" class="normal-case text-ink-gray-7">
								· {{ selectedAttachmentRows.length }} selected
							</span>
						</div>
						<button
							type="button"
							class="inline-flex items-center gap-1.5 rounded-md border border-outline-gray-2 bg-surface-white px-2.5 py-1 text-sm font-medium text-ink-gray-8 hover:bg-surface-gray-2 disabled:opacity-50"
							:disabled="uploading"
							@click="pickFiles"
						>
							<span class="lucide-paperclip size-3.5 text-ink-gray-6" aria-hidden="true" />
							{{ uploading ? "Uploading…" : "Attach" }}
						</button>
						<input
							ref="fileInput"
							type="file"
							class="hidden"
							multiple
							@change="onUpload"
						/>
					</div>

					<div v-if="!docFiles.length && !uploading" class="text-xs text-ink-gray-5">
						No files yet — click Attach to upload, then tick files to send with the email.
					</div>

					<ul v-if="docFiles.length" class="space-y-1.5">
						<li
							v-for="f in docFiles"
							:key="f.name"
							class="flex items-center gap-2 rounded-md border border-outline-gray-1 bg-surface-gray-1 px-2.5 py-2"
						>
							<input
								:id="`att-${f.name}`"
								v-model="form.attachments"
								type="checkbox"
								class="size-4 rounded border-outline-gray-3"
								:value="f.name"
							/>
							<label
								:for="`att-${f.name}`"
								class="min-w-0 flex-1 cursor-pointer truncate text-sm text-ink-gray-8"
							>
								{{ f.file_name || f.name }}
							</label>
						</li>
					</ul>
				</div>
			</div>

			<div
				class="flex flex-wrap items-center justify-between gap-2 border-t border-outline-gray-1 bg-surface-gray-1 px-4 py-2.5"
			>
				<label class="inline-flex items-center gap-2 text-sm text-ink-gray-7">
					<input v-model="form.sendMeACopy" type="checkbox" class="rounded border-outline-gray-3" />
					Send me a copy
				</label>
				<div class="flex gap-2">
					<Button variant="outline" label="Discard" size="sm" :disabled="busy" @click="closeComposer" />
					<Button
						variant="solid"
						label="Send"
						size="sm"
						:loading="busy"
						:disabled="!canSend"
						@click="send"
					/>
				</div>
			</div>
			<ErrorMessage class="px-4 pb-3" :message="error" />
		</div>

		<!-- Thread -->
		<div class="text-sm font-medium text-ink-gray-9">Email thread</div>
		<div v-if="loading" class="text-sm text-ink-gray-5">Loading…</div>
		<div
			v-else-if="!emails.length"
			class="rounded-lg border border-dashed border-outline-gray-2 px-4 py-10 text-center text-sm text-ink-gray-5"
		>
			No emails yet. Click <strong>New Email</strong> to compose.
		</div>
		<ul v-else class="space-y-3">
			<li
				v-for="mail in emails"
				:key="mail.name"
				class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 px-4 py-3"
			>
				<div class="flex flex-wrap items-start justify-between gap-2">
					<div class="min-w-0 flex-1">
						<div class="text-sm font-medium text-ink-gray-9">
							{{ mail.subject || "(No subject)" }}
						</div>
						<div class="mt-0.5 text-xs text-ink-gray-5">
							<span class="font-medium text-ink-gray-6">{{ mail.sender || "—" }}</span>
							→ {{ mail.recipients || "—" }}
							<span v-if="mail.cc"> · CC: {{ mail.cc }}</span>
						</div>
					</div>
					<div class="flex shrink-0 items-center gap-2">
						<span class="text-xs text-ink-gray-4">{{ timeAgo(mail.creation) }}</span>
						<Button
							variant="ghost"
							label="Reply"
							size="sm"
							@click="replyTo(mail)"
						/>
					</div>
				</div>
				<div
					v-if="mail.content"
					class="prose-sm mt-2 max-w-none border-t border-outline-gray-1 pt-2 text-sm text-ink-gray-8"
					v-html="mail.content"
				/>
			</li>
		</ul>
	</div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { Button, ErrorMessage, TextEditor, call, toast } from "frappe-ui";
import MultiSelectEmailInput from "@/components/MultiSelectEmailInput.vue";
import { timeAgo } from "@/utils/format";
import { SAFE_TEXT_EDITOR_BUTTONS } from "@/utils/textEditor";
import { uploadDocFile } from "@/utils/upload";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
	defaultSubject: { type: String, default: "" },
});

const loading = ref(false);
const busy = ref(false);
const uploading = ref(false);
const error = ref("");
const emails = ref([]);
const docFiles = ref([]);
const fromOptions = ref([]);
const composing = ref(false);
const showCc = ref(false);
const showBcc = ref(false);
const editorKey = ref(0);
const replyToName = ref(null);
const fileInput = ref(null);

const form = reactive({
	sender: "",
	to: [],
	cc: [],
	bcc: [],
	subject: "",
	content: "",
	attachments: [],
	sendMeACopy: false,
});

const canSend = computed(() => {
	const body = (form.content || "").replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").trim();
	const hasRecipients = form.to.length || form.cc.length || form.bcc.length;
	return hasRecipients && !!(form.subject || "").trim() && !!body;
});

const selectedAttachmentRows = computed(() =>
	docFiles.value.filter((f) => form.attachments.includes(f.name)),
);

function joinEmails(list) {
	return (list || []).filter(Boolean).join(", ");
}

function pickFiles() {
	fileInput.value?.click();
}

function resetForm() {
	form.to = [];
	form.cc = [];
	form.bcc = [];
	form.subject = props.defaultSubject || "";
	form.content = "";
	form.attachments = [];
	form.sendMeACopy = false;
	replyToName.value = null;
	showCc.value = false;
	showBcc.value = false;
	editorKey.value += 1;
	error.value = "";
	const def = fromOptions.value.find((a) => a.default) || fromOptions.value[0];
	form.sender = def?.value || form.sender || "";
}

function openComposer() {
	resetForm();
	composing.value = true;
	loadFiles();
}

function closeComposer() {
	composing.value = false;
	resetForm();
}

function replyTo(mail) {
	resetForm();
	composing.value = true;
	showCc.value = false;
	const to = (mail.sender || "").split(/[,;]/).map((s) => s.trim()).filter(Boolean);
	form.to = to;
	const sub = mail.subject || "";
	form.subject = sub.toLowerCase().startsWith("re:") ? sub : `Re: ${sub}`;
	form.content = `<p></p><blockquote class="reply-to-content">${mail.content || ""}</blockquote>`;
	replyToName.value = mail.name || null;
	editorKey.value += 1;
	loadFiles();
}

async function loadAccounts() {
	try {
		fromOptions.value = (await call("swiftservice.api.get_email_accounts")) || [];
		const def = fromOptions.value.find((a) => a.default) || fromOptions.value[0];
		if (def) form.sender = def.value;
	} catch {
		fromOptions.value = [];
	}
}

async function loadFiles() {
	if (!props.doctype || !props.name || props.name === "new") {
		docFiles.value = [];
		return;
	}
	try {
		docFiles.value =
			(await call("swiftservice.api.get_attachments", {
				doctype: props.doctype,
				name: props.name,
			})) || [];
	} catch {
		docFiles.value = [];
	}
}

async function load() {
	if (!props.doctype || !props.name || props.name === "new") {
		emails.value = [];
		return;
	}
	loading.value = true;
	try {
		emails.value =
			(await call("swiftservice.api.get_emails", {
				doctype: props.doctype,
				name: props.name,
			})) || [];
	} catch {
		emails.value = [];
	} finally {
		loading.value = false;
	}
}

async function onUpload(e) {
	const files = [...(e.target.files || [])];
	e.target.value = "";
	if (!files.length) return;
	uploading.value = true;
	error.value = "";
	try {
		for (const file of files) {
			const uploaded = await uploadDocFile(file, {
				doctype: props.doctype,
				docname: props.name,
				isPrivate: false,
			});
			const name = uploaded?.name;
			const fileName = uploaded?.file_name || file.name;
			if (name) {
				// Show immediately even before reload
				if (!docFiles.value.some((f) => f.name === name)) {
					docFiles.value = [
						{ name, file_name: fileName, file_url: uploaded.file_url || "" },
						...docFiles.value,
					];
				}
				if (!form.attachments.includes(name)) {
					form.attachments.push(name);
				}
			}
		}
		await loadFiles();
		toast.success(files.length > 1 ? "Files attached" : "File attached");
	} catch (err) {
		error.value = err?.message || err?.messages?.[0] || "Upload failed";
		toast.error(error.value);
		console.error("Email attachment upload failed:", err);
	} finally {
		uploading.value = false;
	}
}

async function send() {
	if (!canSend.value) return;
	busy.value = true;
	error.value = "";
	try {
		await call("swiftservice.api.send_email", {
			doctype: props.doctype,
			name: props.name,
			recipients: joinEmails(form.to),
			cc: joinEmails(form.cc),
			bcc: joinEmails(form.bcc),
			subject: form.subject,
			content: form.content,
			attachments: form.attachments,
			sender: form.sender || null,
			send_me_a_copy: form.sendMeACopy ? 1 : 0,
			in_reply_to: replyToName.value || null,
		});
		toast.success("Email sent");
		closeComposer();
		await load();
	} catch (e) {
		error.value = e?.messages?.[0] || e?.message || "Could not send email";
		toast.error(error.value);
	} finally {
		busy.value = false;
	}
}

watch(
	() => [props.doctype, props.name, props.defaultSubject],
	() => {
		if (!composing.value) form.subject = props.defaultSubject || "";
		load();
		loadFiles();
	},
);

onMounted(() => {
	form.subject = props.defaultSubject || "";
	loadAccounts();
	load();
	loadFiles();
});
</script>
