<template>
	<DocListPage
		title="Replacements"
		singular="Replacement Case"
		doctype="Replacement Case"
		:fields="['name', 'service_request', 'approval_status', 'new_serial_no', 'old_serial_no', 'modified']"
		:columns="[
			{ key: 'name', label: 'ID', width: '10rem' },
			{ key: 'service_request', label: 'Service Request', width: '14rem' },
			{ key: 'approval_status', label: 'Approval', width: '10rem' },
			{ key: 'new_serial_no', label: 'New Serial', width: '12rem' },
			{ key: 'old_serial_no', label: 'Old Serial', width: '12rem' },
		]"
		:quickFilters="[
			{ fieldname: 'approval_status', label: 'Approval', type: 'Data' },
			{ fieldname: 'service_request', label: 'Service Request', type: 'Data' },
		]"
		:createFields="[
			{ fieldname: 'service_request', label: 'Service Request', fieldtype: 'Data', reqd: 1 },
			{
				fieldname: 'approval_status',
				label: 'Approval',
				fieldtype: 'Select',
				default: 'Pending',
				options: [
					{ label: 'Pending', value: 'Pending' },
					{ label: 'Approved', value: 'Approved' },
					{ label: 'Rejected', value: 'Rejected' },
				],
			},
			{ fieldname: 'old_serial_no', label: 'Old Serial', fieldtype: 'Data' },
			{ fieldname: 'new_serial_no', label: 'New Serial', fieldtype: 'Data' },
		]"
	/>
</template>

<script setup>
import DocListPage from "@/components/DocListPage.vue";
</script>
