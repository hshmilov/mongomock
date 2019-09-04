<template>
  <div
    class="array inline"
    :title="allItems"
  >
    <div
      v-for="item in limitedItems"
      :key="item.name"
      class="item"
    >
      <x-array-raw-view
        v-if="showRaw"
        :data="processedData[item.name]"
        :schema="item"
      />
      <component
        :is="item.type"
        v-else
        :schema="item"
        :value="processedData[item.name]"
      />
    </div>
    <div
      v-if="limit && filteredItems.length > limit"
      class="item"
    >+{{ remainder }}</div>
  </div>
</template>

<script>
  import string from '../string/StringView.vue'
  import number from '../numerical/NumberView.vue'
  import integer from '../numerical/IntegerView.vue'
  import bool from '../boolean/BooleanView.vue'
  import file from './FileView.vue'
  import xArrayRawView from './ArrayRawView.vue'

  import arrayMixin from './array'
  import { includesIgnoreCase } from '../../../../../constants/utils'

  export default {
    name: 'XArrayTableView',
    components: {
      string, number, integer, bool, file, xArrayRawView
    },
    mixins: [arrayMixin],
    props: {
      filter: {
        type: String,
        default: ''
      }
    },
    computed: {
      showRaw () {
        return this.isOrderedObject || this.schema.items.type === 'array'
      },
      filteredItems () {
        if (!this.filter) {
          return this.dataSchemaItems
        }
        let processedData = this.processedData
        return this.dataSchemaItems.filter(item => this.hasFilter(processedData[item.name]))
      },
      limit () {
        if (this.schemaItems.length && this.schemaItems[0].format === 'logo') {
          return null
        }
        if (this.showRaw) {
          return 1
        }
        return 2
      },
      processedData () {
        if (this.isOrderedObject) return this.data
        let items = Object.values(this.data)
        if (this.schema.sort) {
          items.sort()
        }
        if (this.schema.unique) {
          items = Array.from(new Set(items))
        }
        return items
      },
      limitedItems () {
        if (!this.filteredItems || !this.limit || (this.filteredItems.length <= this.limit)) {
          return this.filteredItems
        }
        return this.filteredItems.slice(0, this.limit)
      },
      remainder () {
        return this.filteredItems.length - this.limit
      },
      allItems () {
        if (this.showRaw) {
          return undefined
        }
        if (Array.isArray(this.processedData)) {
          return this.processedData.join(',')
        }
        return Object.values(this.processedData).join(',')
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
  .array.inline {
    display: flex;

    .item {
      margin-right: 8px;
      line-height: 24px;
      display: flex;
      align-items: center;
    }
  }
</style>
