<template>
    <div class="devices-filter">
        <!-- Dropdown component for selecting a query --->
        <triggerable-dropdown :arrow="false">
            <!-- Trigger is an input field containing a 'freestyle' query, a logical condition on fields -->
            <input slot="dropdownTrigger" class="form-control" v-model="searchValue" @input="searchQuery"
                   @keyup.enter.stop="$emit('submit')" ref="greatInput">
            <!--
            Content is a list composed of 3 sections:
            1. Saved queries, filtered to whose names contain the value 'deviceFilter'
            2. Historical queries, filtered to whose filter contain the value 'deviceFilter'
            3. Option to search for 'deviceFilter' everywhere in devices (compares to every text field)
            -->
            <div slot="dropdownContent">
                <nested-menu v-if="saved">
                    <div class="title">Saved Queries</div>
                    <nested-menu-item v-for="query, index in saved" :key="index" :title="query.name"
                                      @click="selectQuery(query.filter)"></nested-menu-item>
                </nested-menu>
                <nested-menu v-if="executed">
                    <div class="title">History</div>
                    <nested-menu-item v-for="query, index in executed" :key="index" :title="query.filter"
                                      @click="selectQuery(query.filter)"></nested-menu-item>
                </nested-menu>
                <nested-menu v-if="searchValue">
                    <nested-menu-item :title="`Search everywhere for: ${searchValue}`"></nested-menu-item>
                </nested-menu>
            </div>
            <!--generic-form slot="dropdownContent" :schema="queryFields" v-model="queryDropdown.value"
                          @input="extractValue" @submit="executeQuery" :condensed="true"></generic-form-->
        </triggerable-dropdown>
        <!-- Button controlling the execution of currently filled query -->
        <a class="btn btn-adjoined" @click="$emit('submit')">go</a>

        <!--i class="icon-help trigger-help" @click="helpTooltip.open = !helpTooltip.open"></i>
        <div v-show="helpTooltip.open" class="help">
            <div>An advanced query is a recursive expression defined as:</div>
            <div>EXPR: [ not ] &lt;field path&gt; COMP &lt;required value&gt; [ LOGIC EXPR ]</div>
            <div>COMP:  == | != | > | < | >= | <= | in</div>
            <div>LOGIC: and | or</div>
            <div>The value can be a primitive, like a string or a number, or a function like:</div>
            <div>regex(&lt;regular expression&gt;)</div>
        </div-->
    </div>
</template>

<script>
	import TriggerableDropdown from '../../components/popover/TriggerableDropdown.vue'
    import NestedMenu from '../../components/menus/NestedMenu.vue'
    import NestedMenuItem from '../../components/menus/NestedMenuItem.vue'

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
		components: {TriggerableDropdown, NestedMenu, NestedMenuItem},
		props: ['value'],
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
			}
		},
		data () {
			return {
				searchValue: this.value,
				helpTooltip: {
					open: false
				}
			}
		},
		methods: {
			...mapActions({
				fetchSavedQueries: FETCH_SAVED_QUERIES,
				fetchExecutedQueries: FETCH_EXECUTED_QUERIES
			}),
			selectQuery (filter) {
				this.searchValue = filter
				this.$emit('input', this.searchValue)
				this.$refs.greatInput.focus()
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
				Promise.all([this.filterSavedQueries(), this.filterExecutedQueries()])
                    .then((response) => console.log("Got them all"))
                    .catch((error) => console.log(error))
                this.$emit('input', this.searchValue)
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
                .form-control {
                    border-radius: 0;
                }
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
        .btn {
            vertical-align: middle;
            line-height: 30px;
        }
    }
</style>