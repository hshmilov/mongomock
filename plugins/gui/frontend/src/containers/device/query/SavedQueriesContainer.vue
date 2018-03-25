<template>
    <x-page title="saved queries" class="query">
        <div>Queries ({{query.savedQueries.data.length}})</div>
        <paginated-table :fetching="query.savedQueries.fetching" :data="query.savedQueries.data"
                         :error="query.savedQueries.error" :fields="query.savedFields" :fetchData="fetchQueries"
                         :actions="queryActions"/>
    </x-page>
</template>


<script>
	import xPage from '../../../components/layout/Page.vue'
	import Card from '../../../components/Card.vue'
	import ActionBar from '../../../components/ActionBar.vue'
	import GenericForm from '../../../components/GenericForm.vue'
	import PaginatedTable from '../../../components/tables/PaginatedTable.vue'
	import SearchInput from '../../../components/SearchInput.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
	import { FETCH_SAVED_QUERIES, ARCHIVE_SAVED_QUERY } from '../../../store/modules/query'
    import { UPDATE_ALERT_QUERY } from '../../../store/modules/alert'
    import { UPDATE_DATA_VIEW } from '../../../store/mutations'

	export default {
		name: 'saved-queries-container',
		components: {
			SearchInput,
			xPage, Card, ActionBar, GenericForm, PaginatedTable
		},
		computed: {
			...mapState(['query']),
            queryActions() {
                return [
                    {triggerIcon: 'navigation/alert', handler: this.createAlert},
                    {triggerFont: 'icon-play2', handler: this.runQuery},
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
				updateDataView: UPDATE_DATA_VIEW,
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
            	let query = this.query.savedQueries.data.filter(query => query.id === queryId)[0]
            	this.updateDataView({module: 'device', view: {
            		query: {filter: query.filter, expressions: query.expressions}, page: 0
            	}})
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