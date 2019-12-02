<template>
  <div class="x-entity-advanced">
    <x-table
      :title="schema.title"
      :module="stateLocation"
      :static-fields="fields"
      :static-data="mergedData"
      :searchable="true"
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
  import xTable from '../../../neurons/data/Table.vue'
  import xButton from '../../../axons/inputs/Button.vue'

  import { mapActions, mapState } from 'vuex'
  import { FETCH_DATA_CONTENT_CSV } from '../../../../store/actions'

  export default {
    name: 'XEntityAdvanced',
    components: {
      xTable, xButton
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
    data () {
      return {
        searchValue: ''
      }
    },
    computed: {
      ...mapState({
        hyperlinks (state) {
          const hyperlinks = state[this.module].hyperlinks.data
          if (!hyperlinks || !hyperlinks['aggregator']) {
            return {}
          }
          return eval(hyperlinks['aggregator'])
        }
      }),
      stateLocation () {
        return `${this.module}/current/data/advanced/${this.index}`
      },
      mergedData () {
        // returns a "merged" version of the data:
        // "if a row is a full subset of another row, do not show it"
        let localData = [...this.data]
        let totalExcludedSet = new Set()
        let stringFields = this.schema.items.filter(x => x.type === 'string' && !x.name.includes('.'))

        // out of all fields, on the topmost level, which are scalars (specifically a string)
        // those that are unique (and non-null) are never a superset or a subset of any other row
        // this code will find those unique ones and add them to 'totalExcludedSet', so they will
        // not take place in the rest of the algorithm.
        // this is O(n)
        stringFields.forEach(schema_item => {
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
        stringFields.forEach(schema_item => {
          let fieldName = schema_item.name
          let d = {}

          localData.filter(x => x !== undefined)
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
                } else if (this.isSubset(localData[j], localData[i])) {
                  localData[j] = undefined
                }
              }
            }

          })
        })

        // this is the lousy part of this algorithm, it is in O(n^2)
        // where (n) = amount of row - amount of rows eliminated in previous steps
        // Goes over any unique pair and check if one is a subset of the other, and if it is,
        // hide show the subset.
        let result = Array.from(totalExcludedSet).map(index => localData[index])
        localData.forEach((x, index) => {
          if (x === undefined || totalExcludedSet.has(index)) return

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
      fields () {
        return this.schema.items.filter(item => {
          return this.isSimpleList(item) && this.hasAnyValue(item.name)
        }).map(item => {
          return { ...item,
            hyperlinks: this.hyperlinks[`${this.schema.name}.${item.name}`]
          }
        })
      }
    },
    methods: {
      ...mapActions({
        fetchDataCSV: FETCH_DATA_CONTENT_CSV
      }),
      isEmpty(value) {
        return value === undefined || value === null || value === ''
      },
      hasAnyValue(name) {
        return this.mergedData.find(currentData => !this.isEmpty(currentData[name]))
      },
      isSimpleList(schema) {
        return (schema.type !== 'array' || schema.items['type'] !== 'array')
      },
      isSubset (subset, superset) {
        for (let [key, value] of Object.entries(subset)) {
          if (value && !superset[key]) return false
          if (!this.isSubsetValue(value, superset[key])) return false
        }
        return true
      },
      isSubsetValue (subsetValue, supersetValue) {
        if (typeof (subsetValue) !== typeof (supersetValue)) return false
        if (Array.isArray(subsetValue)) {
          if (subsetValue.length > supersetValue.length) return false
          for (let i = 0; i < subsetValue.length; i++) {
            let found = false
            supersetValue.forEach(supersetItem => {
              if (this.isSubsetValue(subsetValue[i], supersetItem)) found = true
            })
            if (!found) return false
          }
          return true
        }
        if (typeof (subsetValue) === 'object') {
          return this.isSubset(subsetValue, supersetValue)
        }
        return (subsetValue === supersetValue)
      },
      exportCSV () {
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
    }

</style>