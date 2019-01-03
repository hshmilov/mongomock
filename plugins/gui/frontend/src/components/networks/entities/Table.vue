<template>
    <div class="x-entity-table">
        <x-historical-date v-model="historical" :module="module" @error="$emit('error', $event)"/>
        <x-query :module="module" :read-only="isReadOnly"/>
        <x-table :module="module" id-field="internal_axon_id" ref="table" @click-row="configEntity"
                 v-model="isReadOnly? undefined: selection" @data="$emit('data', $event)">
            <template slot="actions">
                <x-action-menu v-show="hasSelection" :module="module" :entities="selection" @done="updateEntities"/>
                <!-- Modal for selecting fields to be presented in table, including adapters hierarchy -->
                <x-field-config :module="module"/>
                <div class="x-btn link" @click="exportCSV">Export CSV</div>
                <button class="x-btn link" @click="navigateSavedQueries">Saved Queries</button>
            </template>
        </x-table>
    </div>
</template>

<script>
    import xHistoricalDate from '../../neurons/inputs/HistoricalDate.vue'
    import xQuery from '../../neurons/data/Query.vue'
    import xTable from '../../neurons/data/Table.vue'
    import xActionMenu from './ActionMenu.vue'
    import xFieldConfig from './FieldConfig.vue'

    import {mapState, mapMutations, mapActions} from 'vuex'
    import {UPDATE_DATA_VIEW} from '../../../store/mutations'
    import {FETCH_DATA_CONTENT_CSV, FETCH_DATA_FIELDS} from '../../../store/actions'

    export default {
        name: 'x-entity-table',
        components: {xHistoricalDate, xQuery, xTable, xActionMenu, xFieldConfig},
        props: {module: {required: true}},
        computed: {
            ...mapState({
                isReadOnly(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions[this.module.charAt(0).toUpperCase() + this.module.slice(1)] === 'ReadOnly'
                },
                historicalState(state) {
                    return state[this.module].view.historical
                },
                allowedDates(state) {
                    return state.constants.allowedDates[this.module]
                }
            }),
            historical: {
                get() {
                    if (!this.historicalState) return ''
                    return this.historicalState.substring(0, 10)
                },
                set(newDate) {
                    this.updateView({
                        module: this.module, view: {
                            historical: this.allowedDates[newDate]
                        }
                    })
                }
            },
            hasSelection() {
                return (this.selection.ids && this.selection.ids.length) || this.selection.include === false
            }
        },
        data() {
            return {
                selection: {ids: []}
            }
        },
        methods: {
            ...mapMutations({updateView: UPDATE_DATA_VIEW}),
            ...mapActions({
                fetchContentCSV: FETCH_DATA_CONTENT_CSV, fetchDataFields: FETCH_DATA_FIELDS,
            }),
            configEntity(entityId) {
                if (this.hasSelection) return

                let path = `${this.module}/${entityId}`
                if (this.historicalState) {
                    path += `?history=${encodeURIComponent(this.historicalState)}`
                }
                this.$router.push({path: path})
            },
            updateEntities() {
                this.$refs.table.fetchContentPages(true)
                this.fetchDataFields({module: this.module})
                this.selection = {ids: []}
            },
            exportCSV() {
                this.fetchContentCSV({module: this.module})
            },
            navigateSavedQueries() {
                this.$router.push({path: `/${this.module}/query/saved`})
            }
        }
    }
</script>

<style lang="scss">
    .x-entity-table {
        height: calc(100% - 36px);
    }
</style>