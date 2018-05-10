<template>
    <x-page title="alerts">
        <card :title="`alerts (${alert.alertList.data.length})`">
            <span slot="cardActions">
                <action-bar :actions="[{title: 'New', handler: createAlert}]"/>
            </span>
            <!-- Table containing access to all the alerts in the system and showing one page of it at a time -->
            <paginated-table slot="cardContent" :fetching="alert.alertList.fetching" :data="alert.alertList.data"
                             :error="alert.alertList.error" :fields="alert.fields" :fetchData="fetchAlerts"
                             :filter="alertFilter" :actions="alertActions"/>
        </card>
    </x-page>
</template>


<script>
	import xPage from '../../components/layout/Page.vue'
    import Card from '../../components/Card.vue'
	import ActionBar from '../../components/ActionBar.vue'
    import PaginatedTable from '../../components/tables/PaginatedTable.vue'

	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
    import { FETCH_ALERTS, SET_ALERT, ARCHIVE_ALERT, RESTART_ALERT } from '../../store/modules/alert'

    export default {
        name: 'alert-container',
        components: { xPage, Card, ActionBar, PaginatedTable },
		computed: {
            ...mapState(['alert']),
            ...mapGetters(['filterFields']),
            alertActions() {
            	/*
            	    Optional action for a specific alert in table - can be removed to configured
            	 */
            	return [
                    { handler: this.configAlert, triggerIcon: 'action/edit'},
					{ handler: this.removeAlert, triggerFont: 'icon-trash-o'}
                ]
            }
		},
        data() {
        	return {
        		alertFilter: {}
            }
        },
        methods: {
            ...mapMutations({ restartAlert: RESTART_ALERT, setAlert: SET_ALERT }),
			...mapActions({ fetchAlerts: FETCH_ALERTS, archiveAlert: ARCHIVE_ALERT }),
            executeFilter(filterData) {
				/*
				    Upon submission of the filter form, updating the controls of the filter that is passed as props to the
				    paginated table, and so it is re-rendered after fetching the controls with consideration to the new filter
				 */
                this.alertFilter = filterData
            },
            configAlert(alertId) {
				/*
                    Fetch the requested alert configuration and navigate to configuration page with the id, to load it
				 */
				if (!alertId) { return }
                this.setAlert(alertId)
				this.$router.push({path: `alert/${alertId}`})
            },
            createAlert() {
				this.restartAlert()
				this.$router.push({path: '/alert/new'});
            },
            removeAlert(alertId) {
                this.archiveAlert(alertId)
            }
        }
    }
</script>


<style lang="scss">

</style>