<template>
    <div class="x-queries-table">
        <x-search v-model="searchText" placeholder="Search Query Name..."/>
        <x-table-wrapper title="Queries" :count="queries.length" :loading="loading">
            <template slot="actions">
                <x-button v-if="selected.length === 1" :disabled="!isEnforcementsWrite" link @click="createEnforcement">+ New Enforcement</x-button>
                <x-button v-if="selected && selected.length" :disabled="readOnly" link @click="removeQuery">Remove</x-button>
            </template>
            <x-table slot="table" :data="filteredQueries" :fields="fields" v-model="readOnly? undefined: selected"
                     :click-row-handler="runQuery"/>
        </x-table-wrapper>
    </div>
</template>

<script>
    import xSearch from '../../neurons/inputs/SearchInput.vue'
    import xTableWrapper from '../../axons/tables/TableWrapper.vue'
    import xTable from '../../axons/tables/Table.vue'
    import xButton from '../../axons/inputs/Button.vue'

    import {mapState, mapMutations, mapActions} from 'vuex'
    import {UPDATE_DATA_VIEW} from '../../../store/mutations'
    import {FETCH_DATA_VIEWS, REMOVE_DATA_VIEW} from '../../../store/actions'
    import {SET_ENFORCEMENT, initTrigger} from '../../../store/modules/enforcements'

    export default {
        name: 'x-queries-table',
        components: {xSearch, xTableWrapper, xTable, xButton},
        props: {
            module: {required: true}, readOnly: {default: false}
        },
        computed: {
            ...mapState({
                queries(state) {
                    return state[this.module].views.saved.data
                },
                isEnforcementsWrite(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Enforcements === 'ReadWrite' || user.admin
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
                    {name: 'timestamp', title: 'Save Time', type: 'string', format: 'date-time'}
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
                updateView: UPDATE_DATA_VIEW, setEnforcement: SET_ENFORCEMENT
            }),
            ...mapActions({
                fetchDataQueries: FETCH_DATA_VIEWS, removeDataQuery: REMOVE_DATA_VIEW
            }),
            runQuery(queryId) {
                let query = this.queries.filter(query => query.uuid === queryId)[0]
                this.updateView({module: this.module, view: query.view})

                this.$router.push({path: `/${this.module}`})
            },
            createEnforcement() {
                this.setEnforcement({
                    uuid: 'new',
                    actions: {
                        main: null,
                        success: [],
                        failure: [],
                        post: []
                    },
                    triggers: this.selected.map(name => {
                        return {...initTrigger,
                            name: 'Trigger',
                            view: {
                                name, entity: this.module
                            }
                        }
                    })
                })
                /* Navigating to new enforcement - requested queries will be selected as triggers there */
                this.$router.push({path: '/enforcements/new'})
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
    .x-queries-table {
        height: 100%;

        .x-search-input {
            margin-bottom: 12px;
        }

        .x-table-wrapper {
            height: calc(100% - 72px);
        }
    }
</style>