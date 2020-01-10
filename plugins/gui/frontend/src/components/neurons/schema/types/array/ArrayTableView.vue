<template>
  <div class="array inline">
    <component
      :is="itemWrapper"
      v-for="{schema, data} in dataSchemaItems"
      :key="schema.name"
      class="item"
      :class="schema.format || format"
    >
      <component
        :is="schema.type"
        :schema="schema"
        :value="data"
      />
    </component>
  </div>
</template>

<script>
  import string from '../string/StringView.vue'
  import number from '../numerical/NumberView.vue'
  import integer from '../numerical/IntegerView.vue'
  import bool from '../boolean/BooleanView.vue'
  import file from './FileView.vue'
  import array from './ArrayRawView.vue'

  import arrayMixin from '../../../../../mixins/array'
  import { isObjectListField } from '../../../../../constants/utils'
  import _get from 'lodash/get'

  export default {
    name: 'XArrayTableView',
    components: {
      string, number, integer, bool, file, array
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
      format () {
        return this.schema.format
      },
      isRaw () {
        return isObjectListField(this.schema)
      },
      isTag () {
        return _get(this.schema, 'items.format') === 'tag'
      },
      wrapChip () {
        const isSeparatedList = this.dataSchemaItems.length > 1 && this.schema.name !=='adapters'
        return isSeparatedList || this.isTag || this.isRaw
      },
      itemWrapper () {
        return this.wrapChip ? 'v-chip' : 'div'
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

      &.v-chip {
        cursor: pointer;

        &:not(.tag) {
          font-size: 14px;
          height: 24px;
          line-height: 24px;
          border: 1px solid rgba($theme-orange, 0.2);
          background-color: transparent;

          &.table {
            background-color: rgba($grey-3, 0.2);
            border: 0;
          }
        }

      }

      &:first-child.v-chip {
        margin-left: -12px;
      }
    }
  }

</style>