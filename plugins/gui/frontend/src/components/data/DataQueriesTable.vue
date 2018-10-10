<template>
    <div class="x-data-queries">
        <x-search v-model="searchText" placeholder="Search Query Name..." />
        <x-actionable-table title="Queries" :count="queries.length" :loading="loading">
            <template slot="actions">
                <div v-if="selected.length === 1" class="x-btn link" :class="{disabled: !isAlertsWrite}"
                     @click="createAlert">+ New Alert</div>
                <div v-if="selected && selected.length" @click="removeQuery"
                     class="x-btn link" :class="{ disabled: readOnly }">Remove</div>
            </template>
            <x-table slot="table" id-field="uuid" :data="filteredQueries" :fields="fields"
                     v-model="readOnly? undefined: selected" :click-row-handler="runQuery" />
        </x-actionable-table>
    </div>
</template>

<script>
    import xSearch from '../inputs/SearchInput.vue'
    import xActionableTable from '../tables/ActionableTable.vue'
    import xTable from '../schema/SchemaTable.vue'

    import { mapState, mapMutations, mapActions } from 'vuex'
	import { UPDATE_DATA_VIEW } from '../../store/mutations'
    import { FETCH_DATA_VIEWS, REMOVE_DATA_VIEW } from '../../store/actions'
	import { UPDATE_ALERT_VIEW } from '../../store/modules/alert'

	export default {
		name: 'data-queries-table',
        components: { xSearch, xActionableTable, xTable },
        props: {
		    module: { required: true }, readOnly: { default: false }
        },
        computed: {
            ...mapState({
                queries(state) {
                	return state[this.module].views.saved.data
                },
                isAlertsWrite(state) {
                    if (!state.auth.data || !state.auth.data.permissions) return true
                    return state.auth.data.permissions.Alerts === 'ReadWrite' || state.auth.data.admin
                }
            }),
            filteredQueries() {
            	// Filter by query's name, according to user's input to the search input field
            	return this.queries.filter(
            		(query) => query.name.toLowerCase().includes(this.searchText.toLowerCase())
                )
            },
            fields() {
            	return [
					{name: 'name', title: 'Name', type: 'string'},
					{name: 'view->query->filter', title: 'Filter', type: 'string'},
					{name: 'timestamp', title: 'Save Time', type: 'string', format: 'date-time'},
				]
            }
        },
        data() {
            return {
                selected: [],
                loading: true,
                searchText: ''
            }
        },
        methods: {
			...mapMutations({
				updateView: UPDATE_DATA_VIEW, updateAlertQuery: UPDATE_ALERT_VIEW
	        }),
            ...mapActions({
                fetchDataQueries: FETCH_DATA_VIEWS, removeDataQuery: REMOVE_DATA_VIEW
            }),
			runQuery(queryId) {
				let query = this.queries.filter(query => query.uuid === queryId)[0]
                this.updateView({ module: this.module, view: query.view })

				this.$router.push({ path: `/${this.module}` })
			},
			createAlert() {
				if (!this.selected.length || !this.isAlertsWrite) return

				this.updateAlertQuery(this.selected[0])
				/* Navigating to new alert - requested query will be selected there */
				this.$router.push({ path: '/alert/new'})
			},
            removeQuery() {
				this.removeDataQuery({module: this.module, ids: this.selected})
                this.selected = []
            }
        },
        created() {
            this.fetchDataQueries({module: this.module, type: 'saved'}).then(() => this.loading = false)
        }
	}
</script>

<style lang="scss">
    .x-data-queries {
        height: 100%;
        .search-input {
            margin-bottom: 12px;
        }
        .x-table-actionable {
            height: calc(100% - 72px);
        }
    }
</style>