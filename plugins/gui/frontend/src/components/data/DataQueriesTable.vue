<template>
    <x-actionable-table title="Queries" :count="queries.length" :loading="loading">
        <template slot="actions">
            <div v-if="selected.length === 1" class="link" @click="createAlert">+ New Alert</div>
            <div class="link" @click="removeQuery">Remove</div>
        </template>
        <x-table slot="table" id-field="uuid" :data="queries" :fields="fields" v-model="selected"
                 :click-row-handler="runQuery"/>
    </x-actionable-table>
</template>

<script>
    import xActionableTable from '../tables/TableActionable.vue'
    import xTable from '../tables/Table.vue'

    import { mapState, mapMutations, mapActions } from 'vuex'
	import { CLEAR_DATA_CONTENT, UPDATE_DATA_VIEW } from '../../store/mutations'
    import {FETCH_DATA_VIEWS, REMOVE_DATA_VIEW} from '../../store/actions'
	import { UPDATE_ALERT_VIEW } from '../../store/modules/alert'

	export default {
		name: 'data-queries-table',
        components: { xActionableTable, xTable },
        props: {module: {required: true}},
        data() {
			return {
				selected: [],
                loading: false
            }
        },
        computed: {
            ...mapState({
                queries(state) {
                	return state[this.module].views.saved.data
                }
            }),
            fields() {
            	return [
					{name: 'name', title: 'Name', type: 'string'},
					{name: 'view->query->filter', title: 'Filter', type: 'string'},
					{name: 'timestamp', title: 'Save Time', type: 'string', format: 'date-time'},
				]
            }
        },
        methods: {
			...mapMutations({
				updateView: UPDATE_DATA_VIEW, updateAlertQuery: UPDATE_ALERT_VIEW,
                clearDataContent: CLEAR_DATA_CONTENT
	        }),
            ...mapActions({
                fetchDataQueries: FETCH_DATA_VIEWS, removeDataQuery: REMOVE_DATA_VIEW
            }),
			runQuery(queryId) {
				let query = this.queries.filter(query => query.uuid === queryId)[0]
                this.updateView({ module: this.module, view: query.view })

				this.clearDataContent({module: this.module})
				this.$router.push({ path: `/${this.module}` })
			},
			createAlert() {
				if (!this.selected.length) return

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
			if (!this.queries || !this.queries.length) {
				this.loading = true
				this.fetchDataQueries({module: this.module, type: 'saved'}).then(() => this.loading = false)
            }
        }
	}
</script>

<style lang="scss">

</style>