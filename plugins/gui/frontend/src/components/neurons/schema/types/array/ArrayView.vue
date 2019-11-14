<template>
  <div class="x-array-view">
    <div
      v-if="schema.title === 'SEPARATOR' && dataSchemaItems.length"
      class="separator"
    >&nbsp;</div>
    <template v-else-if="schema.title && dataSchemaItems.length">
      <x-button
        link
        class="expander"
        @click="toggleCollapsed"
      >{{ collapsed? '+': '-' }}</x-button>
      <label
        :title="schema.description || ''"
        class="label"
      >{{ schema.title }}</label>
    </template>
    <div
      class="array"
      :class="{ordered: isOrderedObject}"
    >
      <div
        v-for="(item, index) in visibleDataSchemaItems"
        :key="index"
        class="item-container"
        :class="{ collapsable }"
      >
        <!-- In collapsed mode, only first item is revealed -->
        <div
          ref="item"
          class="item"
          :class="{ 'growing-y': collapsable, numbered: isNumbered(item)}"
        >
          <div
            v-if="isNumbered(item)"
            class="index"
          >{{ item.name + 1 }}.</div>
          <x-type-wrap
            v-bind="item"
            :required="true"
          >
            <x-slice
              v-if="isMergedValue(data[item.name], item)"
              :schema="item"
              :value="data[item.name]"
            >
              <x-array-table-view
                slot-scope="{ sliced }"
                :schema="item"
                :value="sliced"
              />
            </x-slice>
            <array
              v-else-if="item.type === 'array'"
              ref="array"
              :schema="item"
              :value="data[item.name]"
            />
            <x-table-data
              v-else
              :ref="item.type"
              :schema="item"
              :data="data[item.name]"
              :hyperlinks="hyperlinks"
            />
          </x-type-wrap>
        </div>
      </div>
    </div>
    <!-- Indication for more data for this item -->
    <div
      v-if="collapsed && (isOrderedObject || schemaItems.length > 5)"
      class="placeholder"
    >...</div>
  </div>
</template>

<script>
  import xButton from '../../../../axons/inputs/Button.vue'
  import xTypeWrap from './TypeWrap.vue'
  import xSlice from '../../Slice.vue'
  import number from '../numerical/NumberView.vue'
  import xTableData from '../../../../axons/tables/TableData'
  import xArrayTableView from './ArrayTableView.vue'

  import arrayMixin from '../../../../../mixins/array'

  export default {
    name: 'Array',
    components: {
      xButton, xTypeWrap, xSlice,
      xTableData, xArrayTableView
    },
    mixins: [arrayMixin],
    props: {
      hyperlinks: {
        type: Object,
        default: null
      }
    },
    computed: {
      collapsable () {
        return this.schema.title && this.schema.title !== 'SEPARATOR'
      },
      visibleDataSchemaItems () {
        return this.dataSchemaItems.filter((item, index) => !this.collapsed || (!this.isOrderedObject && index < 5))
      }
    },
    created () {
      if (this.collapsable && !this.isOrderedObject) {
        // Collapsed by default, only for real lists (not an object with ordered fields)
        this.collapsed = true
      }
    },
    methods: {
      updateCollapsed (collapsed) {
        if (!this.collapsable) return

        if (!collapsed) {
          this.collapsed = false
        } else if (!this.collapsed) {
          this.$refs.item.forEach((item, index) => {
            // Exit animation for items to be collapsed (all but first)
            if (this.isOrderedObject || index >= 5) item.classList.add('shrinking-y')
          })
          setTimeout(() => this.collapsed = true, 1000)
        }
      },
      toggleCollapsed () {
        this.updateCollapsed(!this.collapsed)
      },
      collapseRecurse (collapsed) {
        this.updateCollapsed(collapsed)
        setTimeout(() => {
          if (!this.$refs.array) return
          this.$refs.array.forEach(item => {
            item.collapseRecurse(collapsed)
          })
        })
      },
      isNumbered (item) {
        return typeof item.name === 'number'
      },
      isMergedValue (value, schema) {
        return Array.isArray(value) && schema.type !== 'array'
      }
    }
  }
</script>

<style lang="scss">
    .x-array-view {
        .separator {
            width: 100%;
            height: 1px;
            background-color: rgba($theme-orange, 0.2);
            margin: 12px 0;
        }
        .x-button.link.expander {
            display: inline-block;
            padding: 0;
            width: 16px;
            text-align: left;
        }
        .item-container {
            overflow: visible;
            &.collapsable {
              overflow: hidden;
            }
        }
        .placeholder {
            margin-left: 16px;
            color: $grey-3;
            font-weight: 500;
        }
        .label, .index {
            font-weight: 400;
            line-height: 20px;
        }
        .index {
            margin-right: 4px;
            display: inline-block;
            vertical-align: top;
        }
        .object {
            white-space: pre-line;
            text-overflow: ellipsis;
        }
    }
</style>
