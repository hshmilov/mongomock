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
        >Export CSV</x-button>
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
    data () {
      return {
        searchValue: ''
      }
    },
    computed: {
      stateLocation () {
        return `${this.module}/current/data/advanced/${this.index}`
      },
      mergedData () {
        return this.data.filter((subset, i) => {
          let found = false
          let j = 0
          while (!found && j < this.data.length) {
            if (i !== j) {
              let superset = this.data[j]
              if ((this.isSubset(subset, superset)) && (!this.isEqual(subset, superset) || j > i)) {
                found = true
              }
            }
            j++
          }
          return !found
        })
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
      sortedData () {
        return [ ...this.filteredData ].sort((first, second) => {
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
          if (typeof(first) === 'string') {
            return (first < second)? -1 : 1
          }
          return first - second
        })
      },
      fields () {
        return this.schema.items.filter(item => this.mergedData.find(currentData => currentData[item.name]))
          .map(item => {
            return { ...item, path: [this.module, 'aggregator', ...name.split('.').slice(1)] }
          })
      }
    },
    mounted () {
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
      isSubset (subset, superset) {
        for (let [key, value] of Object.entries(subset)) {
          if (value && !superset[key]) return false
          if (!this.isSubsetValue(value, superset[key])) return false
        }
        return true
      },
      isSubsetValue (subsetValue, supersetValue) {
        if (typeof(subsetValue) !== typeof(supersetValue)) return false
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
        if (typeof(value) === 'object') {
          return this.isSubset(subsetValue, supersetValue)
        }
        return (subsetValue === supersetValue)
      },
      isEqual (value1, value2) {
        if (!value1 && !value2) return true
        if ((!value1 && value2) || (value1 && !value2) || (typeof(value1) !== typeof(value2))) return false
        if (Array.isArray(value1)) {
          if (value1.length !== value2.length) return false
          return value1.filter((item1, i) => !this.isEqual(item1, value2[i])).length === 0
        }
        if (typeof(value1) === 'object') {
          if (Object.keys(value1).length !== Object.keys(value2).length) return false
          return Object.keys(value1).filter(key => !this.isEqual(value1[key], value2[key]))
        }
        return value1 === value2
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

    .header {
      .x-search-input {
        width: 60%;
      }
    }
  }

</style>