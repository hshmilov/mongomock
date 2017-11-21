<template>
    <scrollable-page title="alerts">
        <card title="filter">
            <generic-form slot="cardContent" :schema="alert.fields" submitLabel="go"
                          @submit="executeFilter"></generic-form>
        </card>
        <card :title="`alerts (${alert.alertList.data.length})`">
            <span slot="cardActions">
                <action-bar :actions="[{title: 'New', handler: configAlert}]"></action-bar>
            </span>
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
                this.alertFilter = filterData
            },
            configAlert(event, alertId) {
				if (alertId) {
					this.fetchAlert(alertId)
				} else {
					alertId = 'new'
                }
				this.$router.push({path: `alert/${alertId}`});
            },
            removeAlert(alertId) {
                this.archiveAlert(alertId)
            }
        }
    }
</script>


<style lang="scss">

</style>