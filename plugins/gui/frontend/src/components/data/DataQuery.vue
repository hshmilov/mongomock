<template>
    <div class="data-query">
        <!-- Dropdown component for selecting a query --->
        <triggerable-dropdown :arrow="false">
            <!-- Trigger is an input field containing a 'freestyle' query, a logical condition on fields -->
            <input slot="trigger" class="form-control" v-model="searchValue" ref="greatInput"
                   @input="searchQuery" @keyup.enter.stop="submitFilter" :tabindex="1"
                   placeholder="Insert your query or start typing to filter recent Queries"
                   @keyup.down="incQueryMenuIndex" @keyup.up="decQueryMenuIndex">
            <!--
            Content is a list composed of 3 sections:
            1. Saved queries, filtered to whose names contain the value 'searchValue'
            2. Historical queries, filtered to whose filter contain the value 'searchValue'
            3. Option to search for 'searchValue' everywhere in data (compares to every text field)
            -->
            <div slot="content" @keyup.down="incQueryMenuIndex" @keyup.up="decQueryMenuIndex">
                <nested-menu v-if="savedQueries && savedQueries.length">
                    <div class="title">Saved Queries</div>
                    <nested-menu-item v-for="query, index in savedQueries" :key="index" :title="query.name"
                                      :selected="queryMenuIndex === index" @click="selectQuery(query)" />
                </nested-menu>
                <nested-menu v-if="historyQueries && historyQueries.length">
                    <div class="title">History</div>
                    <nested-menu-item v-for="query, index in historyQueries" :key="index" :title="query.filter"
                                      :selected="queryMenuIndex - savedQueries.length === index" @click="selectQuery(query)" />
                </nested-menu>
                <nested-menu v-if="this.searchValue && !complexSearch">
                    <nested-menu-item :title="`Search everywhere for: ${searchValue}`" @click="searchText"
                                      :selected="queryMenuIndex === queryMenuCount - 1"/>
                </nested-menu>
                <div v-if="noResults">No results</div>
            </div>
        </triggerable-dropdown>
        <triggerable-dropdown class="form-control" align="right" size="xl">
            <div slot="trigger" class="link" :tabindex="2">Query</div>
            <div slot="content" class="query-wizard">
                <x-schema-filter :schema="filterSchema" v-model="queryExpressions" @change="updateFilter"
                                 @error="filterValid = false" :rebuild="rebuild"/>
                <div class="place-right">
                    <a class="x-btn link" @click="clearFilter" @keyup.enter="clearFilter" :tabindex="3">Clear</a>
                    <a class="x-btn" @click="rebuildFilter" @keyup.enter="rebuildFilter" :tabindex="4">Search</a>
                </div>
            </div>
        </triggerable-dropdown>
        <!-- Button controlling the execution of currently filled query -->
        <a class="x-btn right" @click="submitFilter" :tabindex="5">
            <svg-icon name="action/search" :original="true" height="24"></svg-icon>
        </a>
        <a class="x-btn link" :class="{disabled: disableSaveButton}" @click="openSaveQuery" :tabindex="6">
            <svg-icon name="action/save" :original="true" height="18"></svg-icon>
        </a>
        <modal v-if="saveModal.isActive" @close="closeSaveQuery" approveText="save" @confirm="confirmSaveQuery">
            <div slot="body" class="form-group">
                <label class="form-label" for="saveName">Save as:</label>
                <input class="form-control" v-model="saveModal.name" id="saveName" @keyup.enter="confirmSaveQuery">
            </div>
        </modal>
    </div>
</template>

<script>
	import TriggerableDropdown from '../popover/TriggerableDropdown.vue'
    import NestedMenu from '../menus/NestedMenu.vue'
    import NestedMenuItem from '../menus/NestedMenuItem.vue'
    import xSchemaFilter from '../schema/SchemaFilter.vue'
	import Modal from '../../components/popover/Modal.vue'

	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
    import { GET_DATA_FIELD_LIST_TYPED } from '../../store/getters'
	import { UPDATE_DATA_VIEW } from '../../store/mutations'
    import { FETCH_DATA_QUERIES, SAVE_DATA_QUERY } from '../../store/actions'
	import { expression } from '../../mixins/filter'

	export default {
		name: 'x-data-query',
		components: { TriggerableDropdown, NestedMenu, NestedMenuItem, xSchemaFilter, Modal },
		props: {module: {required: true}, limit: {default: 5}},
		computed: {
			...mapState({
                savedQueries(state) {
                	return state[this.module].queries.saved.data.slice(0, this.limit)
                },
				historyQueries(state) {
					return state[this.module].queries.history.data.slice(0, this.limit)
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
            ...mapMutations({ updateView: UPDATE_DATA_VIEW }),
			...mapActions({
				fetchQueries: FETCH_DATA_QUERIES, saveQuery: SAVE_DATA_QUERY,
			}),
            focusInput() {
				this.$refs.greatInput.focus()
            },
			searchQuery () {
				if (this.complexSearch || this.queryMenuIndex !== -1) return
				Promise.all([this.filterQueries('saved', 'name'), this.filterQueries('history', 'filter')])
					.catch((error) => console.log(error))
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
				this.$refs.greatInput.parentElement.click()
            },
            submitFilter () {
            	if (!this.filterValid) return
                this.queryFilter = this.searchValue
            	this.executeFilter()
				this.$refs.greatInput.parentElement.click()
            },
			selectQuery ({ filter, expressions }) {
            	this.queryExpressions = expressions || [ { ...expression } ]
				this.updateFilter(filter)
				this.focusInput()
				this.$refs.greatInput.parentElement.click()
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
                if (this.searchValue === '') return
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
            }
		},
        created() {
			this.searchQuery()
            if (this.queryFilter) {
				this.searchValue = this.queryFilter
            }
        }
	}
</script>

<style lang="scss">
    .data-query {
        display: flex;
        width: 100%;
        > .dropdown {
            flex: auto;
            .dropdown-toggle {
                padding: 0;
                line-height: 20px;
                .form-control {
                    border-radius: 0;
                    border-right: 0;
                }
            }
            &.form-control {
                border-radius: 0;
                border-left: 0;
                flex: 0;
                padding-right: 36px;
            }
            .menu {
                border-bottom: 1px solid $grey-2;
                &:last-child {
                    border: 0;
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
        .query-wizard {
            padding: 12px;
            .x-btn.link {
                margin-right: 8px;
            }
        }
        .disabled {
            pointer-events: none;
            opacity: 0.4;
        }
    }
</style>