<template>
    <x-page title="saved queries">
        <x-data-queries-table module="users" :actions="[{triggerIcon: 'navigation/alert', handler: createAlert}]" />
    </x-page>
</template>

<script>
    import xPage from '../../components/layout/Page.vue'
    import xDataQueriesTable from '../../components/data/DataQueriesTable.vue'

    import { UPDATE_ALERT_VIEW } from '../../store/modules/alert'
    import { mapMutations } from 'vuex'

	export default {
		name: 'user-queries-container',
        components: {
            xPage, xDataQueriesTable
        },
        methods: {
            ...mapMutations({updateAlertQuery: UPDATE_ALERT_VIEW}),
            createAlert(queryId) {
                this.updateAlertQuery(queryId)

                /* Navigating to new alert - requested query will be selected there */
                this.$router.push({ path: '/alert/new'})
            },
        }
	}
</script>

<style lang="scss">

</style>