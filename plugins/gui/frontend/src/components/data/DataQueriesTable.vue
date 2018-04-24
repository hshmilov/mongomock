<template>
    <card :title="`Queries (${queries.data.length})`">
        <paginated-table slot="cardContent" :fetching="queries.fetching" :data="queries.data" :error="queries.error"
                         :fields="fields" :fetchData="fetchQueries" :actions="queryActions" id-field="uuid"/>
    </card>
</template>

<script>
	import Card from '../../components/Card.vue'
	import PaginatedTable from '../../components/tables/PaginatedTable.vue'

    import { mapState, mapMutations, mapActions } from 'vuex'
	import { UPDATE_DATA_VIEW } from '../../store/mutations'
	import { FETCH_DATA_QUERIES, REMOVE_DATA_QUERY } from '../../store/actions'

	export default {
		name: 'data-queries-table',
        components: {Card, PaginatedTable},
        props: {module: {required: true}, actions: {default: () => []}},
        computed: {
            ...mapState({
                queries(state) {
                	return state[this.module].queries.saved
                }
            }),
			queryActions() {
				return [
					{triggerFont: 'icon-play2', handler: this.runQuery},
					{triggerFont: 'icon-trash-o', handler: this.removeQuery},
                    ...this.actions
				]
			},
            fields() {
            	return [
					{path: 'name', name: 'Name', default: true},
					{path: 'filter', name: 'Filter', default: true},
					{path: 'timestamp', name: 'Save Time', type: 'timestamp', default: true},
				]
            }
        },
        methods: {
			...mapMutations({
				updateDataView: UPDATE_DATA_VIEW
			}),
            ...mapActions({ fetchDataQueries: FETCH_DATA_QUERIES, removeDataQuery: REMOVE_DATA_QUERY }),
            fetchQueries() {
            	this.fetchDataQueries({module: this.module, type: 'saved'})
            },
			runQuery(queryId) {
				let query = this.queries.data.filter(query => query.uuid === queryId)[0]
				this.updateDataView({module: this.module, view: {
						query: {filter: query.filter, expressions: query.expressions}, page: 0
					}})
				this.$router.push({ path: `/${this.module}` })
			},
            removeQuery(queryId) {
				this.removeDataQuery({module: this.module, id: queryId})
            }
        }
	}
</script>

<style scoped>

</style>