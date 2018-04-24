<template>
    <x-page title="saved queries">
        <x-data-queries-table module="user" />
    </x-page>
</template>

<script>
    import xPage from '../../components/layout/Page.vue'
    import xDataQueriesTable from '../../components/data/DataQueriesTable.vue'

	export default {
		name: 'user-queries-container',
        components: { xPage, xDataQueriesTable }
	}
</script>

<style lang="scss">

</style>