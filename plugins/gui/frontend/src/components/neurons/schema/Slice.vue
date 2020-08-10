<template>
  <div class="x-slice">
    <slot :sliced="slicedData" />
    <APopover
      v-if="remainder"
      :get-popup-container="getPopupContainer"
      :destroy-tooltip-on-hide="true"
    >
      <template slot="content">
        <XTable
          slot="body"
          v-bind="tooltipTable"
        />
      </template>
      <div
        class="remainder"
      >
        <span>+{{ remainder }}</span>
      </div>
    </APopover>
  </div>
</template>

<script>
import { Popover } from 'ant-design-vue';
import _get from 'lodash/get';
import { mapState } from 'vuex';
import XTable from '../../axons/tables/Table.vue';
import { isObjectListField } from '../../../constants/utils';

export default {
  name: 'XSlice',
  components: {
    XTable,
    APopover: Popover,
  },
  props: {
    schema: {
      type: Object,
      required: true,
    },
    value: {
      type: [String, Number, Boolean, Array, Object],
      default: undefined,
    },
  },
  computed: {
    ...mapState({
      defaultColumnLimit(state) {
        return _get(state, 'configuration.data.system.defaultColumnLimit', 0);
      },
    }),
    limit() {
      if (!Array.isArray(this.value) || this.schema.name === 'adapters') {
        return 0;
      }
      if (isObjectListField(this.schema)) {
        return 1;
      }
      if (this.schema.limit) return this.schema.limit;
      return this.defaultColumnLimit;
    },
    slicedData() {
      if (!this.limit) {
        return this.value;
      }
      return this.value.slice(0, this.limit);
    },
    remainder() {
      return this.limit && this.value.length > this.limit ? this.value.length - this.limit : 0;
    },
    tooltipTable() {
      let schema = { ...this.schema };
      if (schema.type === 'array' && !Array.isArray(schema.items) && !isObjectListField(schema)) {
        schema = { ...schema, ...schema.items };
      }
      if (this.value.length > 500) {
        schema.title += ' (first 500 results)';
      }
      return {
        fields: [schema],
        data: this.value.slice(0, 500),
        colFilters: {
          [schema.name]: this.filter,
        },
        filterable: false,
      };
    },
  },
  methods: {
    getPopupContainer() {
      return this.$el.closest('.x-table-wrapper > .x-table') || this.$el;
    },
  },
};
</script>

<style lang="scss">
  .x-slice {
    display: flex;
    align-items: center;
    position: relative;
    .remainder {
      position: relative;
      height: 20px;
      padding: 0 4px;
      border-radius: 4px;
      background: rgba($theme-orange, .4);
      color: initial;
      font-size: 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
    }
  }
</style>
