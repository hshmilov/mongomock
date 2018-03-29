<template>
    <div class="data-query">
        <!-- Dropdown component for selecting a query --->
        <triggerable-dropdown :arrow="false">
            <!-- Trigger is an input field containing a 'freestyle' query, a logical condition on fields -->
            <input slot="dropdownTrigger" class="form-control" v-model="searchValue" ref="greatInput"
                   @input="searchQuery" @keyup.enter.stop="submitFilter"
                   placeholder="Insert your query or start typing to filter recent Queries">
            <!--
            Content is a list composed of 3 sections:
            1. Saved queries, filtered to whose names contain the value 'searchValue'
            2. Historical queries, filtered to whose filter contain the value 'searchValue'
            3. Option to search for 'searchValue' everywhere in data (compares to every text field)
            -->
            <div slot="dropdownContent">
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
            <div slot="dropdownTrigger" class="link">Query</div>
            <div slot="dropdownContent">
                <x-schema-filter :schema="filterSchema" v-model="queryExpressions" @change="updateFilter"
                                 @error="filterValid = false" :rebuild="rebuild"/>
                <div class="row">
                    <div class="form-group place-right">
                        <a class="btn btn-inverse" @click="clearFilter">Clear</a>
                        <a class="btn" @click="rebuildFilter">Search</a>
                    </div>
                </div>
            </div>
        </triggerable-dropdown>
        <!-- Button controlling the execution of currently filled query -->
        <a class="btn btn-adjoined" @click="submitFilter(searchValue)">go</a>
    </div>
</template>

<script>
	import TriggerableDropdown from '../popover/TriggerableDropdown.vue'
    import NestedMenu from '../menus/NestedMenu.vue'
    import NestedMenuItem from '../menus/NestedMenuItem.vue'
    import xSchemaFilter from '../schema/SchemaFilter.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { UPDATE_DATA_VIEW } from '../../store/mutations'
    import { FETCH_DATA_QUERIES } from '../../store/actions'
	import { expression } from '../../mixins/filter'

	export default {
		name: 'x-data-query',
		components: {TriggerableDropdown, NestedMenu, NestedMenuItem, xSchemaFilter},
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
				if (!this.schema) return []

                return [
					{
						name: 'saved_query', title: 'Saved Query', type: 'string', format: 'predefined',
						enum: this.savedQueries.map((query) => {
							return {name: query.filter, title: query.name}
						})
					},
					...this.schema
				]
            }
		},
		data () {
			return {
				searchValue: '',
                filterValid: true,
                rebuild: false
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
				fetchQueries: FETCH_DATA_QUERIES,
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
                this.submitFilter()
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
        .dropdown {
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
                border-bottom: 1px solid #EEE;
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
        .btn.btn-adjoined {
            vertical-align: middle;
            line-height: 30px;
        }
    }
</style>