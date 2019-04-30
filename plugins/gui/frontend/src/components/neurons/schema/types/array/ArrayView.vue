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
            <component
              :is="item.type"
              :ref="item.type"
              :schema="item"
              :value="data[item.name]"
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
  import xTypeWrap from './TypeWrap.vue'
  import string from '../string/StringView.vue'
  import number from '../numerical/NumberView.vue'
  import integer from '../numerical/IntegerView.vue'
  import bool from '../boolean/BooleanView.vue'
  import file from './FileView.vue'
  import xButton from '../../../../axons/inputs/Button.vue'

  import arrayMixin from './array'

  export default {
    name: 'Array',
    components: {
      xTypeWrap, string, number, integer, bool, file, xButton
    },
    mixins: [arrayMixin],
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
      isNumbered(item) {
        return typeof item.name === 'number'
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
            overflow: hidden;
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
            display: inline-grid;
            white-space: pre-line;
            text-overflow: ellipsis;
        }
    }
</style>
