<template>
    <div class="x-data-query">
        <!-- Dropdown component for selecting a query --->
        <x-dropdown :arrow="false" class="flex-expand">
            <!-- Trigger is an input field containing a 'freestyle' query, a logical condition on fields -->
            <search-input slot="trigger" v-model="searchValue" ref="greatInput" id="query_list" @input="searchQuery"
                          @keyup.enter.native="submitFilter" @click="tour('querySelect')"
                          @keyup.down="incQueryMenuIndex" @keyup.up="decQueryMenuIndex"
                          placeholder="Insert your query or start typing to filter recent Queries" />
            <!--
            Content is a list composed of 3 sections:
            1. Saved queries, filtered to whose names contain the value 'searchValue'
            2. Historical queries, filtered to whose filter contain the value 'searchValue'
            3. Option to search for 'searchValue' everywhere in data (compares to every text field)
            -->
            <div slot="content" @keyup.down="incQueryMenuIndex" @keyup.up="decQueryMenuIndex" class="query-quick">
                <nested-menu v-if="savedQueries && savedQueries.length">
                    <div class="title">Saved Queries</div>
                    <div class="menu-content">
                        <nested-menu-item v-for="query, index in savedQueries" :key="index" :title="query.name"
                                          :selected="queryMenuIndex === index" @click="selectQuery(query)"
                                          :id="(query.name === 'AD Enabled Critical Assets')? 'query_select': undefined" />
                    </div>
                </nested-menu>
                <nested-menu v-if="historyQueries && historyQueries.length">
                    <div class="title">History</div>
                    <div class="menu-content">
                        <nested-menu-item v-for="query, index in historyQueries" :key="index" :title="query.filter"
                                          :selected="queryMenuIndex - savedQueries.length === index" @click="selectQuery(query)" />
                    </div>
                </nested-menu>
                <nested-menu v-if="this.searchValue && !complexSearch">
                    <nested-menu-item :title="`Search everywhere for: ${searchValue}`" @click="searchText"
                                      :selected="queryMenuIndex === queryMenuCount - 1"/>
                </nested-menu>
                <div v-if="noResults">No results</div>
            </div>
        </x-dropdown>
        <a class="x-btn link" :class="{disabled: disableSaveButton}" @click="openSaveQuery" id="query_save">Save Query</a>
        <x-dropdown class="query-wizard" align="right" :alignSpace="4" size="xl" :arrow="false" ref="wizard">
            <div slot="trigger" class="x-btn link" id="query_wizard" @click="tour('queryField')">+ Query Wizard</div>
            <div slot="content">
                <x-schema-filter :schema="filterSchema" v-model="queryExpressions" @change="updateFilter"
                                 @error="filterValid = false" :rebuild="rebuild"/>
                <div class="place-right">
                    <a class="x-btn link" @click="clearFilter" @keyup.enter="clearFilter">Clear</a>
                    <a class="x-btn" @click="rebuildFilter" @keyup.enter="rebuildFilter">Search</a>
                </div>
            </div>
        </x-dropdown>
        <modal v-show="saveModal.isActive" approveText="Save" approveId="query_save_confirm" size="md"
               @close="closeSaveQuery" @confirm="confirmSaveQuery" @enter="tour('querySave')" @leave="tour('queryList')">
            <div slot="body" class="query-save">
                <label for="saveName">Save as:</label>
                <input class="flex-expand" v-model="saveModal.name" id="saveName" @keyup.enter="confirmSaveQuery">
            </div>
        </modal>
    </div>
</template>

<script>
	import xDropdown from '../popover/Dropdown.vue'
    import SearchInput from '../../components/inputs/SearchInput.vue'
    import NestedMenu from '../menus/NestedMenu.vue'
    import NestedMenuItem from '../menus/NestedMenuItem.vue'
    import xSchemaFilter from '../schema/SchemaFilter.vue'
	import Modal from '../../components/popover/Modal.vue'

	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
    import { GET_DATA_FIELD_LIST_TYPED } from '../../store/getters'
	import { UPDATE_DATA_VIEW } from '../../store/mutations'
    import { FETCH_DATA_QUERIES, SAVE_DATA_QUERY } from '../../store/actions'
	import { CHANGE_TOUR_STATE } from '../../store/modules/onboarding'
	import { expression } from '../../mixins/filter'

	export default {
		name: 'x-data-query',
		components: {
			xDropdown, SearchInput, NestedMenu, NestedMenuItem, xSchemaFilter, Modal
        },
		props: {module: {required: true}, limit: {default: 5}},
		computed: {
			...mapState({
                savedQueries(state) {
                	return state[this.module].queries.saved.data
                },
				historyQueries(state) {
					return state[this.module].queries.history.data
				},
                query(state) {
                	return state[this.module].view.query
                },
                selected(state) {
                	return state[this.module].view.fields
                }
            }),
            ...mapGetters({getDataFieldsListTyped: GET_DATA_FIELD_LIST_TYPED}),
            schema() {
				return this.getDataFieldsListTyped(this.module)
            },
            queryExpressions: {
				get() {
					return this.query.expressions
                },
                set(expressions) {
					this.updateView({ module: this.module, view: {
						query: { filter: this.queryFilter, expressions }
					}})
                }
            },
			queryFilter: {
				get() {
					return this.query.filter
				},
				set(filter) {
					this.updateView({ module: this.module, view: {
                        query: { filter, expressions: this.queryExpressions }
                    }})
				}
			},
            complexSearch() {
				if (!this.searchValue) return false
                let simpleMatch = this.searchValue.match('[a-zA-Z0-9 -\._]*')
                return !simpleMatch || simpleMatch.length !== 1 || simpleMatch[0] !== this.searchValue
            },
            noResults() {
				return (!this.searchValue || this.complexSearch) && (!this.savedQueries || !this.savedQueries.length)
                    && (!this.historyQueries || !this.historyQueries.length)
            },
            textSearchPattern() {
				if (!this.schema || !this.schema.length) return ''
				let patternParts = []
                this.schema[0].fields.forEach((field) => {
					if (field.type === 'string' && this.selected.includes(field.name)) {
						patternParts.push(field.name + ' == regex("{val}", "i")')
					}
                })
                return patternParts.join(' or ')
            },
            filterSchema () {
				if (!this.schema || !this.schema.length) return []

                return [ { ...this.schema[0], fields: [ {
						name: 'saved_query', title: 'Saved Query', type: 'string', format: 'predefined',
						enum: this.savedQueries.map((query) => {
							return {name: query.filter, title: query.name}
						})
					}, ...this.schema[0].fields]}, ...this.schema.slice(1)]
            },
            queryMenuCount() {
                return this.savedQueries.length + this.historyQueries.length + (this.searchValue && !this.complexSearch)
            }
		},
		data () {
			return {
				searchValue: '',
                disableSaveButton: true,
                filterValid: true,
                rebuild: false,
                saveModal: {
					isActive: false,
                    name: ''
                },
                queryMenuIndex: -1
			}
		},
        watch: {
			queryFilter(newFilter) {
				this.searchValue = newFilter
            },
            searchValue(newSearchValue) {
                this.disableSaveButton = newSearchValue === ''
            }
        },
		methods: {
            ...mapMutations({ updateView: UPDATE_DATA_VIEW, changeState: CHANGE_TOUR_STATE }),
			...mapActions({
				fetchQueries: FETCH_DATA_QUERIES, saveQuery: SAVE_DATA_QUERY,
			}),
            focusInput () {
				this.$refs.greatInput.focus()
            },
			searchQuery () {
				if (this.complexSearch || this.queryMenuIndex !== -1) return
				return Promise.all([this.filterQueries('saved', 'name'), this.filterQueries('history', 'filter')])
			},
			filterQueries (type, filterField) {
				return this.fetchQueries({
					module: this.module,
					type: type,
					filter: `${filterField} == regex("${this.searchValue}")`
				})
			},
            searchText() {
                this.searchValue = this.textSearchPattern.replace(/{val}/g, this.searchValue)
                this.submitFilter()
            },
            clearFilter() {
				this.queryExpressions = [ {...expression} ]
                this.searchValue = ''
                this.queryFilter = ''
				this.executeFilter()
            },
			rebuildFilter() {
                this.rebuild = true
				this.$refs.wizard.close()
            },
            submitFilter () {
            	if (!this.filterValid) return
                this.queryFilter = this.searchValue
            	this.executeFilter()
				this.$refs.greatInput.$parent.close()
            },
			selectQuery ({ filter, expressions }) {
            	this.queryExpressions = expressions || [ { ...expression } ]
				this.updateFilter(filter)
				this.focusInput()
				this.$refs.greatInput.$parent.close()
			},
            updateFilter (filter) {
            	this.rebuild = false
            	if (this.queryFilter === filter) return
				this.queryFilter = filter
                this.filterValid = true
                this.executeFilter()
            },
            executeFilter () {
				this.updateView({ module: this.module, view: { page: 0 } })
            },
            openSaveQuery() {
                if (this.disableSaveButton || this.searchValue === '') return
            	this.saveModal.isActive = true
            },
            closeSaveQuery() {
            	this.saveModal.isActive = false
            },
            confirmSaveQuery() {
				if (!this.saveModal.name) return

				this.saveQuery({
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
            tour(stateName) {
				this.changeState({ name: stateName })
            }
		},
        created() {
			this.searchQuery().then(() => {
                if (this.$route.query.query) {
                    let requestedQuery = this.savedQueries.filter(query => query.name === this.$route.query.query)
                    if (requestedQuery && requestedQuery.length) {
                        this.queryFilter = requestedQuery[0].filter
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
    .x-data-query {
        display: flex;
        width: 100%;
        > .x-dropdown {
            .search-input {
                padding: 0 12px 0 0;
            }
            .query-quick {
                .x-nested-menu {
                    border-bottom: 1px solid $grey-2;
                    &:last-child {
                        border: 0;
                    }
                    .menu-content {
                        max-height: 150px;
                        overflow: auto;
                    }
                    .menu-item .item-content {
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
                .x-btn.link {
                    margin-right: 8px;
                }
            }
        }
        .query-save {
            display: flex;
            align-items: center;

        }
    }
</style>