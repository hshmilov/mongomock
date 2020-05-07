<template>
  <div class="x-chart-metric sort-container">
    <label class="sort-label">
      Default Sort
    </label>

    <VContainer pa-0>
      <VRow>
        <template v-for="type in availableSortTypes">
          <VCol class="sort-col">
            <input
              :id="getSortTypeId(type)"
              :key="type"
              type="radio"
              :value="type"
              :checked="type === sortType"
              @change="$emit('update:sortType', $event.target.value)"
            >
            <label
              :for="type"
              class="type-label"
            >
              {{ getSortTitle(type) }}
            </label>
          </VCol>
        </template>
      </VRow>

      <VRow>
        <template v-for="order in availableSortOrders">
          <VCol class="sort-col">
            <input
              :id="getSortOrderId(order)"
              :key="order"
              type="radio"
              :value="order"
              :checked="order === sortOrder"
              @change="$emit('update:sortOrder', $event.target.value)"
            >
            <label
              :for="order"
              class="type-label"
            >
              {{ ChartSortOrderLabelEnum[order] }}
            </label>
          </VCol>
        </template>
      </VRow>
    </VContainer>
  </div>
</template>

<script>
import { ChartSortOrderEnum, ChartSortOrderLabelEnum, ChartSortTypeEnum } from '../../../constants/dashboard';

export default {
  name: 'XChartSortSelector',
  components: {},
  props: {
    availableSortTypes: {
      type: Array,
      default: () => [],
    },
    availableSortOrders: {
      type: Array,
      default: () => [],
    },
    sortType: {
      type: String,
      default: null,
    },
    sortOrder: {
      type: String,
      default: null,
    },
  },
  created() {
    this.ChartSortTypeEnum = ChartSortTypeEnum;
    this.ChartSortOrderEnum = ChartSortOrderEnum;
    this.ChartSortOrderLabelEnum = ChartSortOrderLabelEnum;
  },
  methods: {
    getSortTitle(type) {
      return `Sort by ${type}`;
    },
    getSortTypeId(type) {
      return `sort_by_${type}`;
    },
    getSortOrderId(order) {
      return `sort_order_${order}`;
    },
  },
};
</script>

<style lang="scss">
  .sort-container {
    margin-top: 16px;
  }
</style>
