<template>
    <div class="devices-filter">
        <!-- Dropdown component for selecting a query --->
        <triggerable-dropdown :arrow="false">
            <!-- Trigger is an input field containing a 'freestyle' query, a logical condition on fields -->
            <input slot="dropdownTrigger" class="form-control" v-model="searchValue" ref="greatInput"
                   @input="searchQuery" @keyup.enter.stop="$emit('submit')"
                   placeholder="Insert your query or start typing to filter recent Queries">
            <!--
            Content is a list composed of 3 sections:
            1. Saved queries, filtered to whose names contain the value 'deviceFilter'
            2. Historical queries, filtered to whose filter contain the value 'deviceFilter'
            3. Option to search for 'deviceFilter' everywhere in devices (compares to every text field)
            -->
            <div slot="dropdownContent">
                <nested-menu v-if="saved && saved.length">
                    <div class="title">Saved Queries</div>
                    <nested-menu-item v-for="query, index in saved" :key="index" :title="query.name"
                                      @click="selectQuery(query.filter)"/>
                </nested-menu>
                <nested-menu v-if="executed && executed.length">
                    <div class="title">History</div>
                    <nested-menu-item v-for="query, index in executed" :key="index" :title="query.filter"
                                      @click="selectQuery(query.filter)"/>
                </nested-menu>
                <nested-menu v-if="this.searchValue && !complexSearch">
                    <nested-menu-item :title="`Search everywhere for: ${searchValue}`" @click="searchText"/>
                </nested-menu>
                <div v-if="noResults">No results</div>
            </div>
        </triggerable-dropdown>
        <triggerable-dropdown class="form-control" align="right" size="xl">
            <div slot="dropdownTrigger" class="link" @click="recompile = true">Query</div>
            <div slot="dropdownContent">
                <x-schema-filter :schema="schema" v-model="filterExpressions" @change="updateQuery"
                                 @error="filterValid = false" :recompile="recompile" @recompiled="recompile = false"/>
                <div class="row">
                    <div class="form-group place-right">
                        <a class="btn btn-inverse" @click="emptyFilter">Clear</a>
                        <a class="btn" @click="submitFilter">Search</a>
                    </div>
                </div>
            </div>
        </triggerable-dropdown>
        <!-- Button controlling the execution of currently filled query -->
        <a class="btn btn-adjoined" @click="$emit('submit')">go</a>
    </div>
</template>

<script>
	import TriggerableDropdown from '../../components/popover/TriggerableDropdown.vue'
    import NestedMenu from '../../components/menus/NestedMenu.vue'
    import NestedMenuItem from '../../components/menus/NestedMenuItem.vue'
    import xSchemaFilter from '../../components/data/SchemaFilter.vue'

	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
	import {
		UPDATE_NEW_QUERY,
		FETCH_SAVED_QUERIES,
		FETCH_EXECUTED_QUERIES,
		UPDATE_QUICK_EXECUTED,
		UPDATE_QUICK_SAVED
	} from '../../store/modules/query'

	export default {
		name: 'devices-filter-container',
		components: {TriggerableDropdown, NestedMenu, NestedMenuItem, xSchemaFilter},
		props: ['value', 'schema', 'selected'],
		computed: {
			...mapState(['query']),
			saved () {
				return this.query.quickQuery.savedQueries.data
			},
			executed () {
				let used = new Set()
                return this.query.quickQuery.executedQueries.data.filter((query) => {
					let existed = used.has(query.filter)
                    used.add(query.filter)
                    return !existed
                })
			},
            filterExpressions: {
				get() {
					return this.query.newQuery.filterExpressions
                },
                set(filterExpressions) {
					this.updateNewQuery({ filterExpressions })
                }
            },
            complexSearch() {
				if (!this.searchValue) return false
                let simpleMatch = this.searchValue.match('[a-zA-Z0-9 ]*')
                return !simpleMatch || simpleMatch.length !== 1 || simpleMatch[0] !== this.searchValue
            },
            noResults() {
				return (!this.searchValue || this.complexSearch) && (!this.saved || !this.saved.length)
                    && (!this.executed || !this.executed.length)
            },
            textSearchPattern() {
				let patternParts = []
                this.schema.forEach((field) => {
					if (field.type === 'string' && this.selected.includes(field.name)) {
						patternParts.push(field.name + ' == regex("{val}", "i")')
					}
                })
                return patternParts.join(' or ')
            }
		},
		data () {
			return {
				searchValue: this.value,
                filterValid: true,
                recompile: false
			}
		},
        watch: {
			value(newValue) {
				this.searchValue = newValue
            }
        },
		methods: {
            ...mapMutations({ updateNewQuery: UPDATE_NEW_QUERY }),
			...mapActions({
				fetchSavedQueries: FETCH_SAVED_QUERIES,
				fetchExecutedQueries: FETCH_EXECUTED_QUERIES
			}),
			selectQuery (filter) {
				this.updateQuery(filter)
                this.filterExpressions = []
				this.$refs.greatInput.focus()
			},
            updateQuery (filter) {
				this.searchValue = filter
				this.$emit('input', this.searchValue)
                this.filterValid = true
            },
			filterSavedQueries () {
				return this.fetchSavedQueries({
					type: UPDATE_QUICK_SAVED,
					filter: `name == regex("${this.searchValue}")`,
					limit: this.query.quickQuery.limit
				})
			},
			filterExecutedQueries () {
				return this.fetchExecutedQueries({
					type: UPDATE_QUICK_EXECUTED,
					filter: `filter == regex("${this.searchValue}")`,
					limit: this.query.quickQuery.limit
				})
			},
			searchQuery () {
                this.$emit('input', this.searchValue)
            	if (this.complexSearch) return
				Promise.all([this.filterSavedQueries(), this.filterExecutedQueries()])
                    .catch((error) => console.log(error))
			},
            searchText() {
                this.searchValue = this.textSearchPattern.replace(/{val}/g, this.searchValue)
				this.$emit('input', this.searchValue)
				this.$emit('submit')
            },
            submitFilter() {
            	if (!this.filterValid) return

                this.$emit('submit')
            },
            emptyFilter() {
				this.filterExpressions = []
                this.searchValue = ''
                this.$emit('input', '')
            }
		},
        created() {
			this.searchQuery()
        }
	}
</script>

<style lang="scss">

    .devices-filter {
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