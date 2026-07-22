<template>
	<DocListPage
		title="PM Visits"
		singular="PM Visit"
		doctype="Preventive Maintenance Visit"
		:fields="['name', 'installed_base', 'customer', 'scheduled_date', 'engineer', 'status', 'modified']"
		:columns="[
			{ key: 'name', label: 'Visit', width: '10rem' },
			{ key: 'installed_base', label: 'Installed Base', width: '12rem' },
			{ key: 'customer', label: 'Customer', width: '14rem' },
			{ key: 'scheduled_date', label: 'Scheduled', width: '10rem' },
			{ key: 'engineer', label: 'Engineer', width: '12rem' },
			{ key: 'status', label: 'Status', width: '10rem' },
		]"
		:quickFilters="[
			{ fieldname: 'status', label: 'Status', type: 'Data' },
			{ fieldname: 'customer', label: 'Customer', type: 'Data' },
			{ fieldname: 'engineer', label: 'Engineer', type: 'Data' },
		]"
		:createFields="[
			{ fieldname: 'installed_base', label: 'Installed Base', fieldtype: 'Data', reqd: 1 },
			{ fieldname: 'customer', label: 'Customer', fieldtype: 'Data' },
			{ fieldname: 'scheduled_date', label: 'Scheduled Date', fieldtype: 'Data', placeholder: 'YYYY-MM-DD' },
			{ fieldname: 'engineer', label: 'Engineer', fieldtype: 'Data' },
			{
				fieldname: 'status',
				label: 'Status',
				fieldtype: 'Select',
				default: 'Planned',
				options: [
					{ label: 'Planned', value: 'Planned' },
					{ label: 'Completed', value: 'Completed' },
					{ label: 'Cancelled', value: 'Cancelled' },
				],
			},
		]"
	/>
</template>

<script setup>
import DocListPage from "@/components/DocListPage.vue";
</script>
