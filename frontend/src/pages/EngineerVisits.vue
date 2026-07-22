<template>
	<DocListPage
		title="Service Visits"
		singular="Service Visit"
		doctype="Engineer Visit"
		:fields="['name', 'service_request', 'engineer', 'visit_date', 'visit_type', 'status', 'modified']"
		:columns="[
			{ key: 'name', label: 'Visit', width: '10rem' },
			{ key: 'service_request', label: 'Service Request', width: '14rem' },
			{ key: 'engineer', label: 'Engineer', width: '12rem' },
			{ key: 'visit_date', label: 'Date', width: '8rem' },
			{ key: 'status', label: 'Status', width: '10rem' },
		]"
		:quickFilters="[
			{
				fieldname: 'status',
				label: 'Status',
				type: 'Select',
				options: [
					{ label: 'Scheduled', value: 'Scheduled' },
					{ label: 'GPS Check-In', value: 'GPS Check-In' },
					{ label: 'Diagnosis', value: 'Diagnosis' },
					{ label: 'Completed', value: 'Completed' },
				],
			},
			{ fieldname: 'engineer', label: 'Engineer', type: 'Data' },
		]"
		:createFields="[
			{ fieldname: 'service_request', label: 'Service Request', fieldtype: 'Data', reqd: 1 },
			{ fieldname: 'engineer', label: 'Engineer', fieldtype: 'Data', reqd: 1 },
			{ fieldname: 'visit_date', label: 'Visit Date', fieldtype: 'Data', placeholder: 'YYYY-MM-DD' },
			{
				fieldname: 'status',
				label: 'Status',
				fieldtype: 'Select',
				default: 'Scheduled',
				options: [
					{ label: 'Draft', value: 'Draft' },
					{ label: 'Scheduled', value: 'Scheduled' },
					{ label: 'Travel Started', value: 'Travel Started' },
					{ label: 'Completed', value: 'Completed' },
				],
			},
		]"
	/>
</template>

<script setup>
import DocListPage from "@/components/DocListPage.vue";
</script>
