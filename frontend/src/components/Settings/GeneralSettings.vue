<template>
	<div class="flex h-full min-h-[420px] flex-col">
		<div class="flex-1 space-y-6 overflow-y-auto px-6 py-6 text-ink-gray-8">
			<p class="text-sm text-ink-gray-5">
				Service defaults plus ERPNext warehouse / income account for stock issue and billing.
			</p>
			<div class="grid max-w-2xl grid-cols-1 gap-4 sm:grid-cols-2">
				<FormControl
					type="password"
					label="Google Maps API Key"
					placeholder="AIza..."
					v-model="form.google_maps_api_key"
				/>
				<div class="text-xs text-ink-gray-5 sm:col-span-2">
					<span v-if="form.has_google_maps_api_key">Google key is already saved.</span>
					<span v-else>No Google key saved yet.</span>
					Leave blank to keep existing key unchanged.
				</div>
				<FormControl type="number" label="Default SLA Hours" v-model="form.default_sla_hours" />
				<FormControl
					type="select"
					label="Default Priority"
					:options="[
						{ label: 'Low', value: 'Low' },
						{ label: 'Medium', value: 'Medium' },
						{ label: 'High', value: 'High' },
						{ label: 'Urgent', value: 'Urgent' },
					]"
					v-model="form.default_priority"
				/>
				<FormControl type="checkbox" label="Auto Create Issue" v-model="form.auto_create_issue" />
				<FormControl
					type="checkbox"
					label="Notify on Assignment"
					v-model="form.notify_on_assignment"
				/>
				<FormControl
					type="checkbox"
					label="Notify on Resolution"
					v-model="form.notify_on_resolution"
				/>
			</div>

			<div class="border-t border-outline-gray-2 pt-5">
				<div class="mb-3 text-sm font-medium text-ink-gray-9">Stock & Accounts (ERPNext)</div>
				<div class="grid max-w-2xl grid-cols-1 gap-4 sm:grid-cols-2">
					<LinkField
						v-model="form.default_service_warehouse"
						doctype="Warehouse"
						label="Default Service Warehouse"
						placeholder="Issue / return warehouse"
					/>
					<LinkField
						v-model="form.default_income_account"
						doctype="Account"
						label="Default Income Account"
						placeholder="Sales income head"
						:filters="{ is_group: 0, account_type: 'Income Account' }"
					/>
					<LinkField
						v-model="form.default_cost_center"
						doctype="Cost Center"
						label="Default Cost Center"
						placeholder="Cost center"
					/>
					<FormControl
						type="checkbox"
						label="Auto Submit Stock Entry"
						v-model="form.auto_submit_stock_entry"
					/>
					<FormControl
						type="checkbox"
						label="Auto Submit Sales Invoice"
						v-model="form.auto_submit_sales_invoice"
					/>
				</div>
			</div>
		</div>
		<div
			class="flex shrink-0 items-center justify-end border-t border-outline-gray-2 bg-surface-white px-6 py-3"
		>
			<Button variant="solid" label="Update" :loading="saving" @click="save" />
		</div>
	</div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { Button, FormControl, toast } from "frappe-ui";
import LinkField from "@/components/LinkField.vue";
import { useSettings } from "@/stores/settings";

const { load, save: saveSettings } = useSettings();
const form = reactive({
	default_sla_hours: 24,
	default_priority: "Medium",
	auto_create_issue: 1,
	notify_on_assignment: 1,
	notify_on_resolution: 1,
	default_service_warehouse: "",
	default_income_account: "",
	default_cost_center: "",
	auto_submit_stock_entry: 1,
	auto_submit_sales_invoice: 1,
	google_maps_api_key: "",
	has_google_maps_api_key: 0,
});
const saving = ref(false);

async function init() {
	const data = await load(true);
	Object.assign(form, {
		default_sla_hours: data.default_sla_hours ?? 24,
		default_priority: data.default_priority || "Medium",
		auto_create_issue: data.auto_create_issue ?? 1,
		notify_on_assignment: data.notify_on_assignment ?? 1,
		notify_on_resolution: data.notify_on_resolution ?? 1,
		default_service_warehouse: data.default_service_warehouse || "",
		default_income_account: data.default_income_account || "",
		default_cost_center: data.default_cost_center || "",
		auto_submit_stock_entry: data.auto_submit_stock_entry ?? 1,
		auto_submit_sales_invoice: data.auto_submit_sales_invoice ?? 1,
		google_maps_api_key: data.google_maps_api_key || "",
		has_google_maps_api_key: data.has_google_maps_api_key ?? 0,
		brand_name: data.brand_name,
		brand_logo: data.brand_logo,
		favicon: data.favicon,
	});
}

async function save() {
	saving.value = true;
	try {
		const current = await load();
		await saveSettings({ ...current, ...form });
		toast.success("Settings saved");
	} catch (e) {
		toast.error(e?.messages?.[0] || e?.message || "Save failed");
	} finally {
		saving.value = false;
	}
}

onMounted(init);
</script>
