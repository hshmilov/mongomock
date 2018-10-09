<template>
    <x-page title="users">
        <x-data-entities-table module="users" />
    </x-page>
</template>

<script>
    import xPage from '../../components/layout/Page.vue'
    import xDataEntitiesTable from '../../components/data/DataEntitiesTable.vue'

	export default {
		name: 'users-container',
        components: { xPage, xDataEntitiesTable }
    }
</script>

<style lang="scss">

</style>