<template>
  <div class="array inline">
    <template v-if="showRaw">
      <x-array-raw-view
        v-for="{schema, data} in dataSchemaItems"
        :key="schema.name"
        :data="data"
        :schema="schema"
        class="item"
      />
    </template>
    <template v-else-if="wrapChip">
      <md-chip
        v-for="{schema, data} in dataSchemaItems"
        :key="schema.name"
        class="item"
        :class="schema.format"
      >
        <component
          :is="schema.type"
          :schema="schema"
          :value="data"
        />
      </md-chip>
    </template>
    <template v-else>
      <div
        v-for="{schema, data} in dataSchemaItems"
        :key="schema.name"
        class="item"
      >
        <component
          :is="schema.type"
          :schema="schema"
          :value="data"
        />
      </div>
    </template>
  </div>
</template>

<script>
  import string from '../string/StringView.vue'
  import number from '../numerical/NumberView.vue'
  import integer from '../numerical/IntegerView.vue'
  import bool from '../boolean/BooleanView.vue'
  import file from './FileView.vue'
  import xArrayRawView from './ArrayRawView.vue'
  import xTable from '../../../../axons/tables/Table.vue'

  import arrayMixin from '../../../../../mixins/array'
  import { isObjectListField } from '../../../../../constants/utils'
  import _get from 'lodash/get'

  export default {
    name: 'XArrayTableView',
    components: {
      string, number, integer, bool, file, xArrayRawView, xTable
    },
    mixins: [arrayMixin],
    data () {
      return {
        inHoverRemainder: false,
        position: {
          top: false,
          left: false
        }
      }
    },
    computed: {
      showRaw () {
        return isObjectListField(this.schema)
      },
      isTag () {
        return _get(this.schema, 'items.format') === 'tag'
      },
      wrapChip () {
        const isSeparatedList = this.dataSchemaItems.length > 1 && this.schema.name !=='adapters'
        return isSeparatedList || this.isTag
      },
      processedData () {
        if (this.isOrderedObject) {
          return this.data
        }
        let items = Object.values(this.data)
        if (this.schema.sort) {
          items.sort()
        }
        if (this.schema.unique) {
          items = Array.from(new Set(items))
        }
        return items
      }
    }
  }
</script>

<style lang="scss">
  .array.inline {
    display: flex;
    align-items: center;
    position: relative;

    .item {
      margin-right: 8px;
      line-height: 24px;
      display: flex;

      &.md-chip {
          transition: none;

          &:not(.tag):not(.x-array-raw-view) {
            font-size: 14px;
            border: 1px solid rgba($theme-orange, 0.2)!important;
            background-color: transparent!important;
            height: 24px;
            line-height: 24px;
          }
      }

      &:first-child.md-chip {
        margin-left: -12px;
      }
    }
  }

</style>