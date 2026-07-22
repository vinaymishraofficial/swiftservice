<template>
	<DocListPage
		title="Installed Base"
		singular="Installed Base"
		doctype="Installed Base"
		:fields="['name', 'customer', 'item_code', 'serial_no', 'warranty_end_date', 'status', 'modified']"
		:columns="[
			{ key: 'name', label: 'ID', width: '10rem' },
			{ key: 'customer', label: 'Customer', width: '14rem' },
			{ key: 'item_code', label: 'Item', width: '12rem' },
			{ key: 'serial_no', label: 'Serial', width: '12rem' },
			{ key: 'warranty_end_date', label: 'Warranty End', width: '10rem' },
			{ key: 'status', label: 'Status', width: '10rem' },
		]"
		:quickFilters="[
			{ fieldname: 'customer', label: 'Customer', type: 'Data' },
			{ fieldname: 'serial_no', label: 'Serial No', type: 'Data' },
			{ fieldname: 'status', label: 'Status', type: 'Data' },
		]"
		:createFields="[
			{ fieldname: 'customer', label: 'Customer', fieldtype: 'Data', reqd: 1 },
			{ fieldname: 'item_code', label: 'Item Code', fieldtype: 'Data', reqd: 1 },
			{ fieldname: 'serial_no', label: 'Serial No', fieldtype: 'Data' },
			{ fieldname: 'model_no', label: 'Model No', fieldtype: 'Data' },
			{ fieldname: 'warranty_end_date', label: 'Warranty End', fieldtype: 'Data', placeholder: 'YYYY-MM-DD' },
			{
				fieldname: 'status',
				label: 'Status',
				fieldtype: 'Select',
				default: 'Active',
				options: [
					{ label: 'Active', value: 'Active' },
					{ label: 'Inactive', value: 'Inactive' },
				],
			},
		]"
	/>
</template>

<script setup>
import DocListPage from "@/components/DocListPage.vue";
</script>
