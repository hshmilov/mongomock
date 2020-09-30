<template>
  <div class="x-array-view">
    <div
      v-if="schema.title === 'SEPARATOR' && dataSchemaItems.length"
      class="subheader"
    >
      {{ getSubheader }}
    </div>

    <template v-else-if="schema.title && dataSchemaItems.length">
      <XButton
        type="link"
        class="expander"
        @click="toggleCollapsed"
      >{{ collapsed? '+': '-' }}</XButton>
      <label
        :title="schema.description || ''"
        class="label"
      >
        {{ schema.title }}
      </label>
    </template>
    <div
      class="array"
      :class="{ordered: isOrderedObject}"
    >
      <div
        v-for="({schema, data}, index) in visibleDataSchemaItems"
        :key="index"
        class="item-container"
        :class="{ collapsable }"
      >
        <!-- In collapsed mode, only first item is revealed -->
        <div
          ref="item"
          class="item"
          :class="{ 'growing-y': collapsable, numbered: isNumbered(schema)}"
        >
          <div
            v-if="isNumbered(schema)"
            class="index"
          >
            {{ schema.name + 1 }}.
          </div>
          <XTypeWrap
            v-bind="schema"
            :required="true"
          >
            <XSlice
              v-if="isMergedValue(data, schema)"
              :schema="schema"
              :value="data"
            >
              <XArrayTableView
                slot-scope="{ sliced }"
                :schema="schema"
                :value="sliced"
              />
            </XSlice>
            <Array
              v-else-if="schema.type === 'array'"
              ref="array"
              :schema="schema"
              :value="data"
              :index="index"
            />
            <XTableData
              v-else
              :ref="schema.type"
              :schema="schema"
              :data="data"
              :hyperlinks="hyperlinks"
            />
          </XTypeWrap>
        </div>
      </div>
    </div>
    <!-- Indication for more data for this item -->
    <div
      v-if="collapsed && (isOrderedObject || schemaItems.length > 5)"
      class="placeholder"
    >
      ...
    </div>
  </div>
</template>

<script>
import XTypeWrap from './TypeWrap.vue';
import XSlice from '../../Slice.vue';
import XTableData from '../../../../axons/tables/TableData';
import XArrayTableView from './ArrayTableView.vue';

import arrayMixin from '../../../../../mixins/array';

export default {
  name: 'Array',
  components: {
    XTypeWrap,
    XSlice,
    XTableData,
    XArrayTableView,
  },
  mixins: [arrayMixin],
  props: {
    hyperlinks: {
      type: Object,
      default: null,
    },
    index: {
      type: Number,
      default: null,
    },
  },
  computed: {
    collapsable() {
      return this.schema.title && this.schema.title !== 'SEPARATOR';
    },
    visibleDataSchemaItems() {
      const isItemVisible = (_, index) => !this.collapsed || (!this.isOrderedObject && index < 5);
      return this.dataSchemaItems.filter(isItemVisible);
    },
    getSubheader() {
      return ['Common Fields', 'Specific Fields'][this.index];
    },
  },
  created() {
    if (this.collapsable && !this.isOrderedObject) {
      // Collapsed by default, only for real lists (not an object with ordered fields)
      this.collapsed = true;
    }
  },
  methods: {
    updateCollapsed(collapsed) {
      if (!this.collapsable) return;

      if (!collapsed) {
        this.collapsed = false;
      } else if (!this.collapsed) {
        this.$refs.item.forEach((item, index) => {
          // Exit animation for items to be collapsed (all but first)
          if (this.isOrderedObject || index >= 5) item.classList.add('shrinking-y');
        });
        setTimeout(() => { this.collapsed = true; }, 1000);
      }
    },
    toggleCollapsed() {
      this.updateCollapsed(!this.collapsed);
    },
    collapseRecurse(collapsed) {
      this.updateCollapsed(collapsed);
      setTimeout(() => {
        if (!this.$refs.array) return;
        this.$refs.array.forEach((item) => {
          item.collapseRecurse(collapsed);
        });
      });
    },
    isNumbered(item) {
      return typeof item.name === 'number';
    },
    isMergedValue(value, schema) {
      return Array.isArray(value) && schema.type !== 'array';
    },
  },
};
</script>

<style lang="scss">
    .x-array-view {
        .subheader {
          font-size: 18px;
          border-bottom: 1px solid #1d222c36;
          font-weight: bold;
          padding-bottom: 10px;
          margin: 10px 0;
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
            text-overflow: ellipsis;
        }
    }
</style>
