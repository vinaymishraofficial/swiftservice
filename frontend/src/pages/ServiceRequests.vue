<template>
	<DocListPage
		title="Service Requests"
		singular="Service Request"
		doctype="Swift Service Request"
		:fields="[
			'name',
			'subject',
			'customer',
			'status',
			'priority',
			'assigned_engineer',
			'modified',
		]"
		:columns="[
			{ key: 'name', label: 'ID', width: '10rem' },
			{ key: 'subject', label: 'Subject', width: '18rem' },
			{ key: 'customer', label: 'Customer', width: '14rem' },
			{ key: 'status', label: 'Status', width: '10rem' },
			{ key: 'priority', label: 'Priority', width: '8rem' },
			{ key: 'assigned_engineer', label: 'Engineer', width: '12rem' },
		]"
		:quickFilters="[
			{
				fieldname: 'status',
				label: 'Status',
				type: 'Select',
				options: [
					{ label: 'Open', value: 'Open' },
					{ label: 'Assigned', value: 'Assigned' },
					{ label: 'In Progress', value: 'In Progress' },
					{ label: 'Completed', value: 'Completed' },
					{ label: 'Closed', value: 'Closed' },
				],
			},
			{ fieldname: 'customer', label: 'Customer', type: 'Data' },
			{ fieldname: 'priority', label: 'Priority', type: 'Data' },
		]"
		:createFields="[
			{ fieldname: 'customer', label: 'Customer', fieldtype: 'Data', reqd: 1 },
			{ fieldname: 'subject', label: 'Subject', fieldtype: 'Data', reqd: 1, col: 'sm:col-span-2' },
			{
				fieldname: 'priority',
				label: 'Priority',
				fieldtype: 'Select',
				default: 'Medium',
				options: [
					{ label: 'Low', value: 'Low' },
					{ label: 'Medium', value: 'Medium' },
					{ label: 'High', value: 'High' },
					{ label: 'Urgent', value: 'Urgent' },
				],
			},
			{
				fieldname: 'complaint_type',
				label: 'Category',
				fieldtype: 'Select',
				default: 'Warranty',
				options: [
					{ label: 'Warranty', value: 'Warranty' },
					{ label: 'AMC', value: 'AMC' },
					{ label: 'Chargeable', value: 'Chargeable' },
				],
			},
			{ fieldname: 'serial_no', label: 'Serial No', fieldtype: 'Data' },
		]"
		createMethod="swiftservice.api.create_service_request"
	/>
</template>

<script setup>
import DocListPage from "@/components/DocListPage.vue";
</script>
