<template>
  <div>
    <h5 class="mb-1">Select queries for comparison:</h5>
    <XSelectViews
      v-model="selectedViews"
      :entities="entities"
      :view-options="viewOptions"
      :min="1"
      :chart-view="chartView"
      :default-chart-colors="viewDefaultColors"
    />

    <XChartSortSelector
      v-if="showSortOptions"
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
import _every from 'lodash/every';
import chartMixin from './chart';
import XSelectViews from '../../../neurons/inputs/SelectViews.vue';
import {
  ChartSortOrderEnum,
  ChartSortOrderLabelEnum,
  ChartSortTypeEnum, ChartViewEnum,
} from '../../../../constants/dashboard';
import XChartSortSelector from '../../../neurons/inputs/ChartSortSelector.vue';
import defaultChartsColors from '../../../../constants/colors';

const dashboardView = { entity: '', id: '' };
export default {
  name: 'XChartCompare',
  components: {
    XSelectViews, XChartSortSelector,
  },
  mixins: [chartMixin],
  data() {
    return {
      ChartSortTypeEnum,
      ChartSortOrderEnum,
      ChartSortOrderLabelEnum,
      defaultChartsColors,
    };
  },
  computed: {
    initConfig() {
      return {
        views: [{ ...dashboardView }, { ...dashboardView }],
        sort: { sort_by: ChartSortTypeEnum.value, sort_order: ChartSortOrderEnum.desc },
      };
    },
    selectedViews: {
      get() {
        return this.config.views;
      },
      set(views) {
        this.config = { ...this.config, views };
      },
    },
    availableSortTypes() {
      return [ChartSortTypeEnum.value, ChartSortTypeEnum.name];
    },
    availableSortOrders() {
      return [ChartSortOrderEnum.desc, ChartSortOrderEnum.asc];
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
    showSortOptions() {
      return this.chartView === ChartViewEnum.histogram;
    },
    viewDefaultColors() {
      if (this.chartView && this.chartView === ChartViewEnum.pie) {
        return this.defaultChartsColors.pieColors;
      }
      return [];
    },
  },
  watch: {
    chartView(view) {
      if (view !== ChartViewEnum.histogram && this.config.sort) {
        this.config.sort = {
          sort_by: ChartSortTypeEnum.value,
          sort_order: ChartSortOrderEnum.desc,
        };
      }
    },
  },
  methods: {
    validate() {
      this.$emit('validate', _every(this.selectedViews, (view) => view.entity && view.id));
    },
    getSortTitle(type) {
      return `Sort by ${type}`;
    },
  },
};
</script>

<style lang="scss">

</style>
