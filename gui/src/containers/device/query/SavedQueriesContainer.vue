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
                    {trigger: 'icon-play', handler: this.runQuery},
                    {trigger: 'icon-trash-o', handler: this.removeQuery}
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
                restartDevice: RESTART_DEVICES
            }),
			...mapActions({
				fetchQueries: FETCH_SAVED_QUERIES,
				archiveQuery: ARCHIVE_SAVED_QUERY
			}),
            runQuery(queryId) {
            	this.useQuery(queryId)
                this.restartDevice()
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