<template>
    <div class="x-entity-advanced">
        <div class="header">
            <x-search-input
                    v-model="searchValue"
                    :placeholder="`Search ${schema.title}...`"
            />
        </div>
        <x-table
                :title="schema.title"
                :module="stateLocation"
                :static-fields="fields"
                :static-data="sortedData"
        >
            <template slot="actions">
                <x-button
                        link
                        @click="exportCSV"
                >Export CSV
                </x-button>
            </template>
        </x-table>
    </div>
</template>

<script>
    import xSearchInput from '../../../neurons/inputs/SearchInput.vue'
    import xTable from '../../../neurons/data/Table.vue'
    import xButton from '../../../axons/inputs/Button.vue'

    import {mapMutations, mapActions} from 'vuex'
    import {FETCH_DATA_CONTENT_CSV} from '../../../../store/actions'
    import {UPDATE_DATA_VIEW} from '../../../../store/mutations'

    export default {
        name: 'XEntityAdvanced',
        components: {
            xSearchInput, xTable, xButton
        },
        props: {
            index: {
                type: Number,
                required: true
            },
            module: {
                type: String,
                required: true
            },
            entityId: {
                type: String,
                required: true
            },
            schema: {
                type: Object,
                required: true
            },
            data: {
                type: Array,
                default: () => []
            },
            sort: {
                type: Object,
                default: () => {
                    return {
                        field: '', desc: true
                    }
                }
            }
        },
        data() {
            return {
                searchValue: ''
            }
        },
        computed: {
            stateLocation() {
                return `${this.module}/current/data/advanced/${this.index}`
            },
            mergedData() {
                // returns a "merged" version of the data:
                // "if a row is a full subset of another row, do not show it"

                let localData = [...this.data]

                let totalExcludedSet = new Set()

                // out of all fields, on the topmost level, which are scalars (specifically a string)
                // those that are unique (and non-null) are never a superset or a subset of any other row
                // this code will find those unique ones and add them to 'totalExcludedSet', so they will
                // not take place in the rest of the algorithm.
                // this is O(n)
                this.schema.items.filter(x => x.type == 'string').forEach(schema_item => {
                    let fieldName = schema_item.name

                    let excludedSet = {}
                    let valuesSet = new Set()

                    localData.map(d => d[fieldName]).forEach((dataItem, index) => {
                        if (!dataItem) return


                        if (valuesSet.has(dataItem)) {
                            delete excludedSet[dataItem]
                        } else {
                            excludedSet[dataItem] = index
                            valuesSet.add(dataItem)
                        }
                    })

                    Object.values(excludedSet).forEach(x => totalExcludedSet.add(x))
                })

                
                // over all scalars (strings...) fields,
                // group all values of the same value (and not null) and for each group that has over 1
                // value, try to see if the whole row is also a subset or a superset, and if it does, mark them.
                // This reduces the amount of checks we do later.
                // This is O(n^2) where (n) is the maximal amount of identical values.
                this.schema.items.filter(x => x.type == 'string').forEach(schema_item => {
                    let fieldName = schema_item.name
                    let d = {}

                    localData.filter(x => x != undefined)
                        .map(d => d[fieldName])
                        .forEach((dataItem, index) => {
                            if (totalExcludedSet.has(index)) return
                            if (!dataItem) return

                            if (d[dataItem]) {
                                d[dataItem].push(index)
                            } else {
                                d[dataItem] = [index]
                            }
                        })

                    Object.values(d).forEach(list => {
                        if (list.length < 2) return

                        for (let i = 0; i < list.length; ++i) {
                            for (let j = 0; j < i; ++j) {
                                if (!localData[i] || !localData[j]) continue

                                if (this.isSubset(localData[i], localData[j])) {
                                    localData[i] = undefined
                                    continue
                                } else if (this.isSubset(localData[j], localData[i])) {
                                    localData[j] = undefined
                                    continue
                                }
                            }
                        }

                    })
                })


                // this is the lousy part of this algorithm, it is in O(n^2)
                // where (n) = amount of row - amount of rows eliminated in previous steps
                // Goes over any unique pair and check if one is a subset of the other, and if it is,
                // hide show the subset.
                let result = []
                localData.forEach((x, index) => {
                    if (x === undefined) return
                    if (totalExcludedSet.has(index)) {
                        result.push(x)
                        return
                    }
                    let found = false
                    for (let i = 0; i < result.length; ++i) {
                        if (this.isSubset(result[i], x)) {
                            result[i] = x
                            found = true
                            break
                        } else if (this.isSubset(x, result[i])) {
                            found = true
                            break
                        }
                    }
                    if (!found) {
                        result.push(x)
                    }
                })

                return result
            },
            filteredData() {
                if (!this.searchValue) return this.mergedData
                return this.mergedData.filter(item => {
                    return this.fields.filter(field => {
                        if (!item[field.name]) return false
                        return item[field.name].toString().toLowerCase().includes(this.searchValue.toLowerCase())
                    }).length
                })
            },
            sortedData() {
                return [...this.filteredData].sort((first, second) => {
                    if (!this.sort.field) return 1
                    first = first[this.sort.field] || ''
                    second = second[this.sort.field] || ''
                    if (Array.isArray(first)) {
                        first = first[0] || ''
                    }
                    if (Array.isArray(second)) {
                        second = second[0] || ''
                    }
                    if (this.sort.desc) {
                        let temp = first
                        first = second
                        second = temp
                    }
                    if (typeof (first) === 'string') {
                        return (first < second) ? -1 : 1
                    }
                    return first - second
                })
            },
            fields() {
                return this.schema.items.filter(item => this.mergedData.find(currentData => currentData[item.name]))
                    .map(item => {
                        return {...item, path: [
                          this.module, 'aggregator', 'data', this.schema.name
                        ]}
                    })
            }
        },
        mounted() {
            if (!this.sort.field) {
                this.updateView({
                    module: this.stateLocation,
                    view: {
                        sort: {
                            field: this.fields[0].name, desc: false
                        }
                    }
                })
            }
        },
        methods: {
            ...mapMutations({
                updateView: UPDATE_DATA_VIEW
            }),
            ...mapActions({
                fetchDataCSV: FETCH_DATA_CONTENT_CSV
            }),
            isSubset(subset, superset) {
                for (let [key, value] of Object.entries(subset)) {
                    if (value && !superset[key]) return false
                    if (!this.isSubsetValue(value, superset[key])) return false
                }
                return true
            },
            isSubsetValue(subsetValue, supersetValue) {
                if (typeof (subsetValue) !== typeof (supersetValue)) return false
                if (Array.isArray(subsetValue)) {
                    if (subsetValue.length > supersetValue.length) return false
                    subsetValue.forEach(subsetItem => {
                        let found = false
                        supersetValue.forEach(supersetItem => {
                            if (this.isSubsetValue(subsetItem, supersetItem)) found = true
                        })
                        if (!found) return false
                    })
                    return true
                }
                if (typeof (value) === 'object') {
                    return this.isSubset(subsetValue, supersetValue)
                }
                return (subsetValue === supersetValue)
            },
            exportCSV() {
                this.fetchDataCSV({
                    module: this.stateLocation,
                    endpoint: `${this.module}/${this.entityId}/${this.schema.name}`
                })
            }
        }
    }
</script>

<style lang="scss">
    .x-entity-advanced {
        height: calc(100% - 30px);

        .header {
            .x-search-input {
                width: 60%;
            }
        }
    }

</style>