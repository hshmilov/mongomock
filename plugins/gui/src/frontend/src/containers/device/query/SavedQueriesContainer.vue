<template>
    <scrollable-page title="saved queries" class="query">
        <card :title="`queries (${query.savedQueries.data.length})`">
            <paginated-table slot="cardContent" :fetching="query.savedQueries.fetching"
                             :data="query.savedQueries.data" :error="query.savedQueries.error"
                             :fields="query.savedFields" :fetchData="fetchQueries"
                             :actions="queryActions"></paginated-table>
        </card>
    </scrollable-page>
</template>


<script>
	import ScrollablePage from '../../../components/ScrollablePage.vue'
	import Card from '../../../components/Card.vue'
	import ActionBar from '../../../components/ActionBar.vue'
	import GenericForm from '../../../components/GenericForm.vue'
	import PaginatedTable from '../../../components/PaginatedTable.vue'
	import SearchInput from '../../../components/SearchInput.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
	import { FETCH_SAVED_QUERIES, USE_SAVED_QUERY, ARCHIVE_SAVED_QUERY } from '../../../store/modules/query'
    import { RESTART_DEVICES } from '../../../store/modules/device'
    import { UPDATE_ALERT_QUERY } from '../../../store/modules/alert'

	export default {
		name: 'saved-queries-container',
		components: {
			SearchInput,
			ScrollablePage, Card, ActionBar, GenericForm, PaginatedTable
		},
		computed: {
			...mapState(['query']),
            queryActions() {
                return [
                    {triggerIcon: 'alert', handler: this.createAlert},
                    {triggerFont: 'icon-play', handler: this.runQuery},
                    {triggerFont: 'icon-trash-o', handler: this.removeQuery}
                ]
            }
		},
		data () {
			return {
				querySearchValue: ''
			}
		},
		methods: {
            ...mapMutations({
				useQuery: USE_SAVED_QUERY,
                restartDevices: RESTART_DEVICES,
                updateAlertQuery: UPDATE_ALERT_QUERY
            }),
			...mapActions({
				fetchQueries: FETCH_SAVED_QUERIES,
				archiveQuery: ARCHIVE_SAVED_QUERY
			}),
            createAlert(queryId) {
            	/* Find requested query object in order to pass its query to the new alert */
            	this.query.savedQueries.data.forEach((query) => {
            		 if (query.id === queryId) {
            		 	this.updateAlertQuery(query.id)
                     }
                })
                /* Navigating to new alert - requested query will be selected there */
                this.$router.push({ path: '/alert/new'})
            },
            runQuery(queryId) {
            	this.useQuery(queryId)
                this.restartDevices()
                this.$router.push({name: 'Devices'})
            },
			removeQuery (queryId) {
                this.archiveQuery(queryId)
			}
		}
	}
</script>


<style lang="scss">
    .query {
        .form-label {
            font-size: 80%;
        }
        .search-input {
            width: 40%;
            margin-top: 12px;
            margin-left: 8px;
        }
    }
</style>