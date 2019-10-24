<template>
  <x-slicer
    :schema="schema"
    :value="filteredValue"
  >
    <x-table-data
      slot-scope="{ sliced }"
      :schema="processedSchema"
      :data="sliced"
    />
  </x-slicer>
</template>

<script>
  import xSlicer from '../schema/types/Slicer.vue'
  import xTableData from '../../axons/tables/TableData.vue'

  import {isObject, includesIgnoreCase, formatStringTemplate} from '../../../constants/utils'

  export default {
    name: 'XTableData',
    components: {
      xTableData, xSlicer
    },
    props: {
      schema: {
        type: Object,
        required: true
      },
      data: {
        type: [String, Number, Boolean, Array, Object],
        default: undefined
      },
      sort: {
        type: Object,
        default: () => {
          return {
            field: '', desc: true
          }
        }
      },
      filter: {
        type: String,
        default: ''
      }
    },
    computed: {
      fieldName () {
        return this.schema.name
      },
      value () {
        if (!this.data && this.data !== false) {
          return ''
        }
        if (!this.fieldName || !isObject(this.data)) {
          return this.data
        }
        let value = this.data[this.fieldName]
        if (Array.isArray(value) && this.sort && this.fieldName === this.sort.field && !this.sort.desc) {
          return [...value].reverse()
        }
        return value
      },
      filteredValue () {
        if (!this.filter) {
          return this.value
        }
        if (Array.isArray(this.value)) {
          return this.value.filter(item => this.hasFilter(item))
        }
        return this.hasFilter(this.value) ? this.value : null
      },
      processedSchema () {
        if (!this.schema.link) {
          return this.schema
        }
        return { ...this.schema,
          link: formatStringTemplate(this.schema.link, this.data)
        }
      }
    },
    methods: {
      hasFilter (data) {
        if (!data) {
          return false
        }
        if (typeof data === 'string') {
          return includesIgnoreCase(data, this.filter)
        }
        if (typeof data !== 'object') {
          return false
        }
        const itemsToCheck = Array.isArray(data) ? data : Object.values(data)
        return Boolean(itemsToCheck.find(item => this.hasFilter(item)))
      }
    }
  }
</script>

<style lang="scss">
</style>