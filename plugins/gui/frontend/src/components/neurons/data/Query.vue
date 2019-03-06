<template>
    <div class="x-query">
        <!-- Dropdown component for selecting a query --->
        <x-dropdown class="flex-expand" @activated="tour('querySelect')">
            <!-- Trigger is an input field containing a 'freestyle' query, a logical condition on fields -->
            <x-search-input slot="trigger" v-model="searchValue" ref="greatInput" id="query_list" @input="searchQuery"
                            @keyup.enter.native.stop="submitFilter"
                            @keyup.down.native="incQueryMenuIndex" @keyup.up.native="decQueryMenuIndex"
                            placeholder="Insert your query or start typing to filter recent Queries" :tabindex="-1"/>
            <!--
            Content is a list composed of 3 sections:
            1. Saved queries, filtered to whose names contain the value 'searchValue'
            2. Historical queries, filtered to whose filter contain the value 'searchValue'
            3. Option to search for 'searchValue' everywhere in data (compares to every text field)
            -->
            <div slot="content" @keyup.down="incQueryMenuIndex" @keyup.up="decQueryMenuIndex" class="query-quick">
                <x-menu v-if="savedViews && savedViews.length" id="query_select">
                    <div class="title">Saved Queries</div>
                    <div class="menu-content">
                        <x-menu-item v-for="query, index in savedViews" :key="index" :title="query.name"
                                     :selected="isSelectedSaved(index)" @click="selectQuery(query)"/>
                    </div>
                </x-menu>
                <x-menu v-if="historyViews && historyViews.length">
                    <div class="title">History</div>
                    <div class="menu-content">
                        <x-menu-item v-for="query, index in historyViews" :key="index" :title="query.view.query.filter"
                                     :selected="isSelectedHistory(index)" @click="selectQuery(query)"/>
                    </div>
                </x-menu>
                <x-menu v-if="this.searchValue && isSearchSimple">
                    <x-menu-item :title="`Search in table: ${searchValue}`" @click="searchText"
                                 :selected="isSelectedSearch"/>
                </x-menu>
                <div v-if="noResults">No results</div>
            </div>
        </x-dropdown>
        <x-button link :disabled="disableSaveQuery" @click="openSaveView" id="query_save">Save Query</x-button>
        <!-- Triggerable menu containing a wizard for building a query filter -->
        <x-dropdown class="query-wizard" align="right" :align-space="4" :align-agile="false" size="xl" :arrow="false"
                    ref="wizard" @activated="tour('queryField')">
            <x-button slot="trigger" link id="query_wizard">+ Query Wizard</x-button>
            <div slot="content">
                <x-filter :module="module" v-model="queryExpressions" ref="filter" @change="updateFilter"
                          @error="filterValid = false"/>
                <md-switch v-model="isUniqueAdapters" :disabled="!queryFilter">Include outdated Adapter {{prettyModule}}
                    in query
                </md-switch>
                <div class="place-right">
                    <x-button link @click="clearFilter" @keyup.enter.native="clearFilter">Clear</x-button>
                    <x-button @click="compileFilter" @keyup.enter.native="compileFilter">Search</x-button>
                </div>
            </div>
        </x-dropdown>
        <x-modal v-show="saveModal.isActive" approveText="Save" approveId="query_save_confirm" size="md"
                 @close="closeSaveView" @confirm="confirmSaveView" @enter="tour('querySaveConfirm')"
                 @leave="tour('queryList')">
            <div slot="body" class="query-save">
                <label for="saveName">Save as:</label>
                <input class="flex-expand" v-model="saveModal.name" id="saveName" @keyup.enter="confirmSaveView">
            </div>
        </x-modal>
    </div>
</template>

<script>
    import xDropdown from '../../axons/popover/Dropdown.vue'
    import xSearchInput from '../inputs/SearchInput.vue'
    import xMenu from '../../axons/menus/Menu.vue'
    import xMenuItem from '../../axons/menus/MenuItem.vue'
    import xFilter from '../schema/Filter.vue'
    import xModal from '../../axons/popover/Modal.vue'
    import xButton from '../../axons/inputs/Button.vue'


    import {mapState, mapGetters, mapMutations, mapActions} from 'vuex'
    import {GET_DATA_FIELDS_BY_PLUGIN} from '../../../store/getters'
    import {UPDATE_DATA_VIEW} from '../../../store/mutations'
    import {FETCH_DATA_VIEWS, SAVE_DATA_VIEW} from '../../../store/actions'
    import {CHANGE_TOUR_STATE} from '../../../store/modules/onboarding'
    import {expression, nestedExpression} from '../../../constants/filter'

    const INCLUDE_OUDATED_MAGIC = 'INCLUDE OUTDATED: '

    export default {
        name: 'x-query',
        components: {
            xDropdown, xSearchInput, xMenu, xMenuItem, xFilter, xModal, xButton
        },
        props: {
            module: {required: true}, limit: {default: 5}, readOnly: {default: false}
        },
        computed: {
            ...mapState({
                savedViews(state) {
                    return state[this.module].views.saved.data
                },
                historyViews(state) {
                    return state[this.module].views.history.data
                },
                query(state) {
                    return state[this.module].view.query
                },
                selected(state) {
                    return state[this.module].view.fields
                },
                ecFilter(state) {
                    return state[this.module].view.ecFilter
                },
            }),
            ...mapGetters({
                getDataFieldsByPlugin: GET_DATA_FIELDS_BY_PLUGIN
            }),
            prettyModule() {
                return this.module[0].toUpperCase() + this.module.slice(1)
            },
            queryExpressions: {
                get() {
                    return this.query.expressions
                },
                set(expressions) {
                    this.updateView({
                        module: this.module, view: {
                            query: {filter: this.queryFilter, expressions}, page: 0
                        }
                    })
                }
            },
            queryFilter: {
                get() {
                    return this.query.filter
                },
                set(filter) {
                    this.updateView({
                        module: this.module, view: {
                            query: {filter, expressions: this.queryExpressions}, page: 0
                        }
                    })
                }
            },
            isUniqueAdapters: {
                get() {
                    return this.queryFilter.includes(INCLUDE_OUDATED_MAGIC)
                },
                set(isUniqueAdapters) {
                    this.queryFilter = isUniqueAdapters ? `${INCLUDE_OUDATED_MAGIC}${this.queryFilter}`
                        : this.queryFilter.replace(INCLUDE_OUDATED_MAGIC, '')
                }
            },
            disableSaveQuery() {
                /* Determine whether query cannot be saved right now or it can */
                return this.readOnly || this.queryFilter === '' || !this.filterValid
            },
            isSearchSimple() {
                /* Determine whether current search input value is an AQL filter, or just text */
                if (!this.searchValue) return true
                if (this.searchValue.indexOf('exists_in') !== -1) return false
                let simpleMatch = this.searchValue.match('[a-zA-Z0-9 -\._:]*')
                return simpleMatch && simpleMatch.length === 1 && simpleMatch[0] === this.searchValue
            },
            noResults() {
                /* Determine whether there are no results to show in the search input dropdown */
                return (!this.searchValue || !this.isSearchSimple) && (!this.savedViews || !this.savedViews.length)
                    && (!this.historyViews || !this.historyViews.length)
            },
            textSearchPattern() {
                /* Create a template for the search everywhere filter, from all currently selected fields */
                if (!this.selected || !this.selected.length) return ''
                let patternParts = []
                this.selected.forEach((field) => {
                    // Filter fields containing image data, since it is not relevant for searching
                    if (field === 'image') return
                    patternParts.push(field + ' == regex("{val}", "i")')
                })
                return patternParts.join(' or ')
            },
            queryMenuCount() {
                /* Total items to appear in the search input dropdown */
                return this.savedViews.length + this.historyViews.length + (this.searchValue && this.isSearchSimple)
            },
            isSelectedSearch() {
                /* Determine whether the search in table option of the search input dropdown is selected  */
                return this.queryMenuIndex === this.queryMenuCount - 1
            }
        },
        data() {
            return {
                searchValue: '',
                inTextSearch: false,
                filterValid: true,
                saveModal: {
                    isActive: false,
                    name: ''
                },
                queryMenuIndex: -1
            }
        },
        watch: {
            queryFilter(newFilter) {
                if (!this.inTextSearch) {
                    this.searchValue = newFilter
                }
            },
            ecFilter() {
                this.updateFilter(this.queryFilter)
            }
        },
        methods: {
            ...mapMutations({updateView: UPDATE_DATA_VIEW, changeState: CHANGE_TOUR_STATE}),
            ...mapActions({
                fetchViews: FETCH_DATA_VIEWS, saveView: SAVE_DATA_VIEW
            }),
            focusInput() {
                this.$refs.greatInput.focus()
            },
            closeInput() {
                this.$refs.greatInput.$parent.close()
            },
            searchQuery() {
                this.inTextSearch = false
                if (!this.isSearchSimple) return
                /* Filter the saved and history queries in the dropdown, by the string user inserted */
                return Promise.all([
                    this.filterQueries('saved', 'name'), this.filterQueries('history', 'view.query.filter')
                ])
            },
            filterQueries(type, filterField) {
                return this.fetchViews({
                    module: this.module,
                    type: type,
                    filter: this.searchValue.length > 0 ? `${filterField} == regex("${this.searchValue}", "i")` : ``
                }).catch((error) => this.$emit('error', error))
            },
            selectQuery({view}) {
                /* Load given view by settings current filter and expressions to it */
                this.inTextSearch = false
                this.updateView({module: this.module, view})
                this.filterValid = true
                this.focusInput()
                this.closeInput()
            },
            searchText() {
                /* Plug the search value in the template for filtering by any of currently selected fields */
                this.queryFilter = this.wrapFilterOptions(this.textSearchPattern.replace(/{val}/g, this.searchValue))
                this.inTextSearch = true
                this.closeInput()
            },
            submitFilter() {
                if (!this.filterValid) return
                if (this.isSearchSimple) {
                    // Search for value in all selected fields
                    this.searchText()
                } else {
                    // Use the search value as a filter
                    this.queryFilter = this.wrapFilterOptions(this.searchValue)
                }
                this.closeInput()
            },
            clearFilter() {
                // Restart the expressions, search input and filter
                this.queryExpressions = [{
                    ...expression,
                    i: 0, nested: [{...nestedExpression, i: 0}]
                }]
                this.searchValue = ''
                this.queryFilter = ''
            },
            compileFilter() {
                // Instruct the filter to re-compile, in case filter was edited
                this.$refs.filter.compile()
                this.$refs.wizard.close()
            },
            updateFilter(filter) {
                filter = this.wrapFilterOptions(filter)
                if (this.queryFilter === filter) return
                this.queryFilter = filter
                this.filterValid = true
            },
            openSaveView() {
                if (this.searchValue === '') return
                this.saveModal.isActive = true
            },
            closeSaveView() {
                this.saveModal.isActive = false
            },
            confirmSaveView() {
                if (!this.saveModal.name) return

                this.saveView({
                    module: this.module,
                    name: this.saveModal.name
                }).then(() => this.saveModal.isActive = false)
            },
            incQueryMenuIndex() {
                this.queryMenuIndex++
                if (this.queryMenuIndex >= this.queryMenuCount) {
                    this.queryMenuIndex = -1
                    this.focusInput()
                }
            },
            decQueryMenuIndex() {
                this.queryMenuIndex--
                if (this.queryMenuIndex < -1) {
                    this.queryMenuIndex = this.queryMenuCount - 1
                } else if (this.queryMenuIndex === -1) {
                    this.focusInput()
                }
            },
            isSelectedSaved(index) {
                return this.queryMenuIndex === index
            },
            isSelectedHistory(index) {
                return this.queryMenuIndex === index + this.savedViews.length
            },
            tour(stateName) {
                this.changeState({name: stateName})
            },
            wrapFilterOptions(filter) {
                if (!filter) filter = ''
                filter = filter.replace(INCLUDE_OUDATED_MAGIC, '')
                if (this.isUniqueAdapters && filter) {
                    filter = `${INCLUDE_OUDATED_MAGIC}${filter}`
                }

                if (this.ecFilter) {
                    let ec = this.ecFilter
                    // the only flow when the ecFilter can change is on creation
                    if (filter.indexOf('exists_in(') != -1) {
                        filter = filter.slice(0, filter.indexOf('exists_in(')) + filter.slice(filter.indexOf(')') + 1).trim()
                    }
                    filter = `exists_in(${ec.pretty_id}, ${ec.condition}, ${ec.i}, ${ec.success}) ${filter}`
                }
                else if (!this.ecFilter && filter.indexOf('exists_in(') !== -1) {
                    filter = filter.slice(0, filter.indexOf('exists_in(')) + filter.slice(filter.indexOf(')') + 1).trim()
                }

                return filter
            }
        },
        created() {
            this.updateFilter(this.queryFilter)
            this.searchQuery().then(() => {
                if (this.$route.query.view) {
                    let requestedView = this.savedViews.find(view => view.name === this.$route.query.view)
                    if (requestedView) {
                        this.updateView({module: this.module, view: requestedView.view})
                    }
                }
            })
            if (this.queryFilter) {
                this.searchValue = this.queryFilter
            }
        }
    }
</script>

<style lang="scss">
    .x-query {
        display: flex;
        width: 100%;

        > .x-dropdown {
            .x-search-input {
                padding: 0 12px 0 0;

                .input-icon {
                    padding: 0 8px;
                }

                .input-value {
                    padding-left: 36px;
                    width: calc(100% - 12px);
                }
            }

            .query-quick {
                .x-menu {
                    border-bottom: 1px solid $grey-2;

                    &:last-child {
                        border: 0;
                    }

                    .menu-content {
                        max-height: 150px;
                        overflow: auto;
                    }

                    .x-menu-item .item-content {
                        text-overflow: ellipsis;
                        white-space: nowrap;
                        overflow: hidden;
                    }

                    .title {
                        font-size: 12px;
                        font-weight: 400;
                        text-transform: uppercase;
                        padding-left: 6px;
                        margin-top: 6px;
                        color: $grey-4;
                    }

                    &:first-child {
                        .title {
                            margin-top: 0;
                        }
                    }
                }
            }
        }

        .query-wizard {
            .content {
                padding: 12px;
            }
        }

        .query-save {
            display: flex;
            align-items: center;

        }
    }
</style>