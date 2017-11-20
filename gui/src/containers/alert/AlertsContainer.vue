<template>
    <scrollable-page title="alerts">
        <card>

        </card>
        <card :title="`alerts (${alert.alertList.data.length})`">
            <paginated-table slot="cardContent" :fetching="alert.alertList.fetching" :data="alert.alertList.data"
                             :error="alert.alertList.error" :fields="deviceFields" :fetchData="fetchAlerts"
                             :filter="alertFilter" :actions="alertActions"></paginated-table>
        </card>
    </scrollable-page>
</template>


<script>
	import ScrollablePage from '../../components/ScrollablePage.vue'
    import Card from '../../components/Card.vue'
    import PaginatedTable from '../../components/PaginatedTable.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_ALERTS } from '../../store/modules/alert'

    export default {
        name: 'alert',
        components: { ScrollablePage, PaginatedTable },
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
			...mapActions({ fetchAlerts: [ FETCH_ALERTS ] }),
            configAlert(alertId) {
				this.$router.push({path: `alert/${alertId}`});
            },
            removeAlert(alertId) {
                
            }
        }
    }
</script>


<style lang="scss">

</style>