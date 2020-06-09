<template>
  <div class="x-chart-metric">
    <XSelectSymbol
      :value="entity"
      :options="entities"
      type="icon"
      placeholder="module..."
      @input="updateEntity"
    />
    <XSelect
      v-model="view"
      :options="currentViewOptions"
      :searchable="true"
      placeholder="query (or empty for all)"
      class="view-name grid-span2"
    />
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
import XSelect from '../../../axons/inputs/select/Select.vue';
import XSelectSymbol from '../../../neurons/inputs/SelectSymbol.vue';
import chartMixin from './chart';
import XChartSortSelector from '../../../neurons/inputs/ChartSortSelector.vue';
import {
  ChartSortTypeEnum,
  ChartSortOrderEnum,
} from '../../../../constants/dashboard';

export default {
  name: 'XChartAdapterSegment',
  components: {
    XSelect, XSelectSymbol, XChartSortSelector,
  },
  mixins: [chartMixin],
  computed: {
    initConfig() {
      return {
        entity: '',
        selected_view: '',
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
    view: {
      get() {
        return this.config.selected_view;
      },
      set(view) {
        this.config = { ...this.config, selected_view: view };
      },
    },
    currentViewOptions() {
      return this.viewOptions(this.entity, this.view);
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
  },
  methods: {
    updateEntity(entity) {
      if (entity === this.entity) return;
      this.config = {
        entity,
        selected_view: '',
        sort: { sort_by: ChartSortTypeEnum.value, sort_order: ChartSortOrderEnum.desc },
      };
    },
    validate() {
      this.$emit('validate', this.config.entity !== '');
    },
  },
};

</script>

<style>
</style>
