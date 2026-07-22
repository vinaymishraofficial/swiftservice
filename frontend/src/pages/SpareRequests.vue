<template>
	<DocListPage
		title="Spare Requests"
		singular="Spare Request"
		doctype="Spare Request"
		:fields="['name', 'service_request', 'item_code', 'qty', 'stock_status', 'status', 'modified']"
		:columns="[
			{ key: 'name', label: 'ID', width: '10rem' },
			{ key: 'service_request', label: 'Service Request', width: '14rem' },
			{ key: 'item_code', label: 'Item', width: '12rem' },
			{ key: 'qty', label: 'Qty', width: '6rem' },
			{ key: 'stock_status', label: 'Stock', width: '10rem' },
			{ key: 'status', label: 'Status', width: '10rem' },
		]"
		:quickFilters="[
			{ fieldname: 'status', label: 'Status', type: 'Data' },
			{ fieldname: 'item_code', label: 'Item', type: 'Data' },
		]"
		:createFields="[
			{ fieldname: 'service_request', label: 'Service Request', fieldtype: 'Data', reqd: 1 },
			{ fieldname: 'item_code', label: 'Item Code', fieldtype: 'Data', reqd: 1 },
			{ fieldname: 'qty', label: 'Qty', fieldtype: 'Float', default: 1 },
			{
				fieldname: 'status',
				label: 'Status',
				fieldtype: 'Select',
				default: 'Draft',
				options: [
					{ label: 'Draft', value: 'Draft' },
					{ label: 'Requested', value: 'Requested' },
					{ label: 'Issued', value: 'Issued' },
				],
			},
		]"
	/>
</template>

<script setup>
import DocListPage from "@/components/DocListPage.vue";
</script>
