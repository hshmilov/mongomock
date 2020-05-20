<template>
  <div class="x-chart-matrix x-chart-metric">
    <label class="chart-metric">Module for chart</label>
    <XSelectSymbol
      id="module"
      :value="entity"
      :options="entities"
      type="icon"
      placeholder="module..."
      class="grid-span2"
      @input="updateEntity"
    />

    <div
      ref="baseQueriesDiv"
      class="base-query-container grid-span3"
    >
      <div
        v-for="(baseItem, index) in base"
        :key="index"
        class="base-query-row"
      >
        <label>Base query</label>
        <XSelect
          :value="baseItem"
          :options="views[entity] || restrictedViewOptions(baseItem)"
          :searchable="true"
          placeholder="query (or empty for all)"
          @input="(view) => updateBase(index, view)"
        />
        <XButton
          v-if="index > 0"
          type="link"
          @click="removeBase(index)"
        >x</XButton>
      </div>
    </div>
    <XButton
      id="add-base-query"
      type="light"
      @click="addBase"
    >+</XButton>
    <div class="grid-span2">
      <div
        v-for="(intersectingItem, index) in intersecting"
        :key="index"
        class="intersection-query-row"
      >
        <label>Intersecting query</label>
        <XSelect
          :value="intersectingItem"
          :options="views[entity] || restrictedViewOptions(intersectingItem)"
          :searchable="true"
          placeholder="query..."
          @input="(view) => updateIntersecting(index, view)"
        />
        <XButton
          v-if="index > 0"
          type="link"
          @click="removeIntersecting(index)"
        >x</XButton>
      </div>
      <XButton
        id="add-intersecting-query"
        v-if="!hasMaxViews"
        type="light"
        @click="addIntersecting"
      >+</XButton>
    </div>
    <XChartSortSelector
      class="grid-span3"
      :available-sort-types="availableSortTypes"
      :available-sort-orders="availableSortOrders"
      :sort-type.sync="sortType"
      :sort-order.sync="sortOrder"
    />
  </div>
</template>

<script>
import _get from 'lodash/get';
import XButton from '../../../axons/inputs/Button.vue';
import XSelect from '../../../axons/inputs/select/Select.vue';
import XSelectSymbol from '../../../neurons/inputs/SelectSymbol.vue';
import chartMixin from './chart';
import XChartSortSelector from '../../../neurons/inputs/ChartSortSelector.vue';

import {
  ChartSortTypeEnum,
  ChartSortOrderEnum,
} from '../../../../constants/dashboard';

export default {
  name: 'XChartMatrix',
  components: {
    XButton, XSelect, XSelectSymbol, XChartSortSelector,
  },
  mixins: [chartMixin],
  data() {
    return {
      max: 3,
    };
  },
  computed: {
    initConfig() {
      return {
        entity: '',
        base: [''],
        intersecting: [''],
        sort: { sort_by: ChartSortTypeEnum.value, sort_order: ChartSortOrderEnum.desc },
      };
    },
    entity: {
      get() {
        return this.config.entity;
      },
      set(entity) {
        this.config = { ...this.config, entity };
      },
    },
    base: {
      get() {
        return this.config.base;
      },
      set(base) {
        this.config = { ...this.config, base: [...base] };
      },
    },
    sortType: {
      get() {
        return _get(this.config, 'sort.sort_by', ChartSortTypeEnum.value);
      },
      set(sortType) {
        const sort = { ...this.config.sort };
        sort.sort_by = sortType;
        this.config = { ...this.config, sort };
      },
    },
    sortOrder: {
      get() {
        return _get(this.config, 'sort.sort_order', ChartSortOrderEnum.desc);
      },
      set(sortOrder) {
        const sort = { ...this.config.sort };
        sort.sort_order = sortOrder;
        this.config = { ...this.config, sort };
      },
    },
    availableSortTypes() {
      return [ChartSortTypeEnum.value, ChartSortTypeEnum.name];
    },
    availableSortOrders() {
      return [ChartSortOrderEnum.desc, ChartSortOrderEnum.asc];
    },
    intersecting: {
      get() {
        return this.config.intersecting;
      },
      set(intersecting) {
        this.config = { ...this.config, intersecting: [...intersecting] };
      },
    },
    hasMaxViews() {
      if (!this.max) return false;
      return this.intersecting.length === this.max;
    },
    addBtnTitle() {
      return this.hasMaxViews ? `Limited to ${this.max} intersecting queries` : '';
    },
  },
  methods: {
    updateEntity(entity) {
      if (entity === this.entity) return;
      this.config = {
        entity,
        base: [''],
        intersecting: [''],
        sort: { sort_by: ChartSortTypeEnum.value, sort_order: ChartSortOrderEnum.desc },
      };
    },
    removeBase(index) {
      this.base.splice(index, 1);
      this.base = [...this.base];
    },
    addBase() {
      this.base = [...this.base, ''];
      setTimeout(() => {
        this.$refs.baseQueriesDiv.children[this.$refs.baseQueriesDiv.children.length - 1]
          .scrollIntoView();
      });
    },
    updateBase(index, view) {
      this.base = this.base.map((item, ind) => {
        if (ind === index) return view;
        return item;
      });
    },
    removeIntersecting(index) {
      this.intersecting.splice(index, 1);
      this.intersecting = [...this.intersecting];
    },
    addIntersecting() {
      this.intersecting = [...this.intersecting, ''];
    },
    updateIntersecting(index, view) {
      this.intersecting = this.intersecting.map((item, ind) => {
        if (ind === index) return view;
        return item;
      });
    },
    validate() {
      this.$emit('validate', !this.intersecting.filter((view) => view === '').length);
    },
    restrictedViewOptions(selectedView) {
      if (!this.entity || !selectedView) {
        return [];
      }
      return [{
        name: selectedView, title: 'Missing Permissions',
      }];
    },
  },
};
</script>

<style lang="scss">
  .x-chart-matrix {
    .base-query-container {
      max-height: 120px;
      overflow: auto;
      margin-right: -8px;
      padding-right: 8px;

      .base-query-row {
        display: flex;
        margin-bottom: 8px;

        label {
          align-self: center;
          margin-right: 97px;
        }

        .x-dropdown  {
          flex-grow: 1;
        }

        button.ant-btn-link {
          margin-left: 6px;
          padding-right: 0;
        }
      }
    }

    .intersection-query-row {
      display: flex;
      margin-bottom: 8px;

      label {
        align-self: center;
        margin-right: 15px;
      }

      .x-dropdown  {
        flex-grow: 1;
      }

      button.ant-btn-link {
        margin-left: 6px;
        padding-right: 0;
      }
    }

    .sort-container {
      margin-top: 0;
    }
  }
</style>
