<template>
    <x-page title="saved queries">
        <x-data-queries-table module="devices" />
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
    import xDataQueriesTable from '../../components/data/DataQueriesTable.vue'

	export default {
		name: 'device-queries-container',
		components: {
			xPage, xDataQueriesTable
		}
	}
</script>


<style lang="scss">

</style>