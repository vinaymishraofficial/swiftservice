<template>
	<DocListPage
		title="RMA Cases"
		singular="RMA Case"
		doctype="RMA Case"
		:fields="['name', 'service_request', 'pickup_date', 'repair_status', 'dispatch_date', 'modified']"
		:columns="[
			{ key: 'name', label: 'RMA', width: '10rem' },
			{ key: 'service_request', label: 'Service Request', width: '14rem' },
			{ key: 'pickup_date', label: 'Pickup', width: '10rem' },
			{ key: 'repair_status', label: 'Status', width: '10rem' },
			{ key: 'dispatch_date', label: 'Dispatch', width: '10rem' },
		]"
		:quickFilters="[
			{ fieldname: 'repair_status', label: 'Status', type: 'Data' },
			{ fieldname: 'service_request', label: 'Service Request', type: 'Data' },
		]"
		:createFields="[
			{ fieldname: 'service_request', label: 'Service Request', fieldtype: 'Data', reqd: 1 },
			{ fieldname: 'pickup_date', label: 'Pickup Date', fieldtype: 'Data', placeholder: 'YYYY-MM-DD' },
			{
				fieldname: 'repair_status',
				label: 'Status',
				fieldtype: 'Select',
				default: 'Open',
				options: [
					{ label: 'Open', value: 'Open' },
					{ label: 'Received', value: 'Received' },
					{ label: 'Under Repair', value: 'Under Repair' },
					{ label: 'Dispatched', value: 'Dispatched' },
				],
			},
			{ fieldname: 'remarks', label: 'Remarks', fieldtype: 'Text', col: 'sm:col-span-2 lg:col-span-3' },
		]"
	/>
</template>

<script setup>
import DocListPage from "@/components/DocListPage.vue";
</script>
