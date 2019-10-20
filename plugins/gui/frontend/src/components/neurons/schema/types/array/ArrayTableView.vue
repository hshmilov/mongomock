<template>
  <div class="array inline">
    <div
      v-for="item in dataSchemaItems"
      :key="item.name"
      class="item"
    >
      <x-array-raw-view
        v-if="showRaw"
        :data="processedData[item.name]"
        :schema="item"
      />
      <template v-else-if="dataSchemaItems.length > 1 && schema.name !=='adapters' && item.format !== 'tag'">
        <md-chip>
          <component
            :is="item.type"
            :schema="item"
            :value="processedData[item.name]"
          />
        </md-chip>
      </template>
      <template v-else>
        <component
          :is="item.type"
          :schema="item"
          :value="processedData[item.name]"
        />
      </template>
    </div>
  </div>
</template>

<script>
  import string from '../string/StringView.vue'
  import number from '../numerical/NumberView.vue'
  import integer from '../numerical/IntegerView.vue'
  import bool from '../boolean/BooleanView.vue'
  import file from './FileView.vue'
  import xArrayRawView from './ArrayRawView.vue'
  import xTooltip from '../../../../axons/popover/Tooltip.vue'
  import xTable from '../../../../axons/tables/Table.vue'

  import arrayMixin from './array'
  import { isObjectListField } from '../../../../../constants/utils'

  export default {
    name: 'XArrayTableView',
    components: {
      string, number, integer, bool, file, xArrayRawView, xTooltip, xTable
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
      processedData () {
        if (this.isOrderedObject){
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

    &:hover .x-tooltip {
      display: block
    }

    .item {
      margin-right: 8px;
      line-height: 24px;
      display: flex;

      .md-chip {
          transition: none;

          &:not(.tag):not(.x-array-raw-view) {
            font-size: 14px;
            border: 1px solid rgba($theme-orange, 0.2)!important;
            background-color: transparent!important;
            height: 24px;
            line-height: 24px;
          }
      }

      &:first-child .md-chip {
        margin-left: -12px;
      }
    }
  }

</style>