<template>
    <scrollable-page title="alerts">
        <card :title="`alerts (${alert.alertList.data.length})`">
            <span slot="cardActions">
                <action-bar :actions="[{title: 'New', handler: createAlert}]"></action-bar>
            </span>
            <!-- Table containing access to all the alerts in the system and showing one page of it at a time -->
            <paginated-table slot="cardContent" :fetching="alert.alertList.fetching" :data="alert.alertList.data"
                             :error="alert.alertList.error" :fields="alert.fields" :fetchData="fetchAlerts"
                             :filter="alertFilter" :actions="alertActions"></paginated-table>
        </card>
    </scrollable-page>
</template>


<script>
	import ScrollablePage from '../../components/ScrollablePage.vue'
    import Card from '../../components/Card.vue'
    import GenericForm from '../../components/GenericForm.vue'
	import ActionBar from '../../components/ActionBar.vue'
    import PaginatedTable from '../../components/PaginatedTable.vue'

	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
    import { FETCH_ALERTS, SET_ALERT, ARCHIVE_ALERT, RESTART_ALERT } from '../../store/modules/alert'

    export default {
        name: 'alert-container',
        components: { ScrollablePage, Card, GenericForm, ActionBar, PaginatedTable },
		computed: {
            ...mapState(['alert']),
            ...mapGetters(['filterFields']),
            alertActions() {
            	/*
            	    Optional actions for a specific alert in table - can be removed to configured
            	 */
            	return [
                    { handler: this.configAlert, triggerFont: 'icon-pencil2'},
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
				    Upon submission of the filter form, updating the data of the filter that is passed as props to the
				    paginated table, and so it is re-rendered after fetching the data with consideration to the new filter
				 */
                this.alertFilter = filterData
            },
            configAlert(alertId) {
				/*
                    Fetch the requested alert configuration and navigate to configuration page with the id, to load it
				 */
				if (!alertId) { return }
                this.setAlert(alertId)
				this.$router.replace({path: `alert/${alertId}`})
            },
            createAlert() {
				this.restartAlert()
				this.$router.replace({path: '/alert/new'});
            },
            removeAlert(alertId) {
                this.archiveAlert(alertId)
            }
        }
    }
</script>


<style lang="scss">

</style>