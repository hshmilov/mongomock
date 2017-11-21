<template>
    <scrollable-page title="alerts">
        <card title="filter">
            <!-- Form containing the fields that alert table can be filtered by -->
            <generic-form slot="cardContent" :schema="alert.fields" submitLabel="go" @submit="executeFilter"></generic-form>
        </card>
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

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_ALERTS, FETCH_ALERT, ARCHIVE_ALERT } from '../../store/modules/alert'

    export default {
        name: 'alert-container',
        components: { ScrollablePage, Card, GenericForm, ActionBar, PaginatedTable },
		computed: {
            ...mapState(['alert']),
            alertActions() {
            	/*
            	    Optional actions for a specific alert in table - can be removed to configured
            	 */
            	return [
                    { handler: this.configAlert, trigger: 'icon-cog'},
					{ handler: this.removeAlert, trigger: 'icon-trash-o'}
                ]
            }
		},
        data() {
        	return {
        		alertFilter: {}
            }
        },
        methods: {
			...mapActions({ fetchAlerts: FETCH_ALERTS, fetchAlert: FETCH_ALERT, archiveAlert: ARCHIVE_ALERT }),
            executeFilter(filterData) {
				/*
				    Upon submittion of the filter form, updating the data of the filter that is passed as props to the
				    paginated table, and so it is re-rendered after fetching the data with consideration to the new filter
				 */
                this.alertFilter = filterData
            },
            configAlert(alertId) {
				/*
                    Fetch the requested alert configuration and navigate to configuration page with the id, to load it
				 */
				if (!alertId) { return }
                this.fetchAlert(alertId)
				this.$router.push({path: `alert/${alertId}`});
            },
            createAlert() {
				this.$router.push({path: 'alert/new'});
            },
            removeAlert(alertId) {
                this.archiveAlert(alertId)
            }
        }
    }
</script>


<style lang="scss">

</style>