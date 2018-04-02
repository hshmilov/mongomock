<template>
    <div class="data-query">
        <!-- Dropdown component for selecting a query --->
        <triggerable-dropdown :arrow="false">
            <!-- Trigger is an input field containing a 'freestyle' query, a logical condition on fields -->
            <input slot="trigger" class="form-control" v-model="searchValue" ref="greatInput"
                   @input="searchQuery" @keyup.enter.stop="submitFilter" :tabindex="1"
                   placeholder="Insert your query or start typing to filter recent Queries">
            <!--
            Content is a list composed of 3 sections:
            1. Saved queries, filtered to whose names contain the value 'searchValue'
            2. Historical queries, filtered to whose filter contain the value 'searchValue'
            3. Option to search for 'searchValue' everywhere in data (compares to every text field)
            -->
            <div slot="content">
                <nested-menu v-if="savedQueries && savedQueries.length">
                    <div class="title">Saved Queries</div>
                    <nested-menu-item v-for="query, index in savedQueries.slice(0, limit)" :key="index"
                                      :title="query.name" @click="selectQuery(query.filter, query.expressions)"/>
                </nested-menu>
                <nested-menu v-if="historyQueries && historyQueries.length">
                    <div class="title">History</div>
                    <nested-menu-item v-for="query, index in historyQueries.slice(0, limit)" :key="index"
                                      :title="query.filter" @click="selectQuery(query.filter, [])"/>
                </nested-menu>
                <nested-menu v-if="this.searchValue && !complexSearch">
                    <nested-menu-item :title="`Search everywhere for: ${searchValue}`" @click="searchText"/>
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
                    <a class="x-btn link" @click="clearFilter" :tabindex="3">Clear</a>
                    <a class="x-btn" @click="rebuildFilter" :tabindex="4">Search</a>
                </div>
            </div>
        </triggerable-dropdown>
        <!-- Button controlling the execution of currently filled query -->
        <a class="x-btn right" @click="submitFilter" :tabindex="5">
            <svg-icon name="action/search" :original="true" height="24"></svg-icon>
        </a>
        <a class="x-btn link" @click="openSaveQuery" :tabindex="6">
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

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { UPDATE_DATA_VIEW } from '../../store/mutations'
    import { FETCH_DATA_QUERIES, SAVE_DATA_QUERY } from '../../store/actions'
	import { expression } from '../../mixins/filter'

	export default {
		name: 'x-data-query',
		components: { TriggerableDropdown, NestedMenu, NestedMenuItem, xSchemaFilter, Modal },
		props: {module: {required: true}, schema: {}, selected: {}, limit: {default: 5}},
		computed: {
			...mapState({
                savedQueries(state) {
                	return state[this.module].data.queries.saved.data
                },
				historyQueries(state) {
					return state[this.module].data.queries.history.data
				},
                query(state) {
                	return state[this.module].data.view.query
                }
            }),
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

                let filterSchema = [ ...this.schema ]
                filterSchema[0].fields = [{
					name: 'saved_query', title: 'Saved Query', type: 'string', format: 'predefined',
					enum: this.savedQueries.map((query) => {
						return {name: query.filter, title: query.name}
					})
				}, ...filterSchema[0].fields ]
                return filterSchema
            }
		},
		data () {
			return {
				searchValue: '',
                filterValid: true,
                rebuild: false,
                saveModal: {
					isActive: false,
                    name: ''
                }
			}
		},
        watch: {
			queryFilter(newFilter) {
				this.searchValue = newFilter
            }
        },
		methods: {
            ...mapMutations({ updateView: UPDATE_DATA_VIEW }),
			...mapActions({
				fetchQueries: FETCH_DATA_QUERIES, saveQuery: SAVE_DATA_QUERY,
			}),
			searchQuery () {
				if (this.complexSearch) return
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
			selectQuery (filter, expressions) {
            	this.queryExpressions = expressions
				this.updateFilter(filter)
				this.$refs.greatInput.focus()
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
        }
    }
</style>