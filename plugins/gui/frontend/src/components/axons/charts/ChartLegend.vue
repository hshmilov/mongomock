<template>
  <div class="x-chart-legend">
    <div
      class="legend-grid"
      :style="gridTemplateColumns"
    >
      <div
        v-for="(columnValue, index) in columnValues"
        :key="index"
        :class="columnValue.class"
        :title="columnValue.value"
        @click="columnValue.onClick"
      >
        {{ columnValue.value }}
      </div>
    </div>
    <XPaginator
      v-if="showPaginator"
      :from.sync="legendFrom"
      :to.sync="legendTo"
      :limit="10"
      :count="data.length"
      :show-top="false"
    />
  </div>
</template>

<script>

import XPaginator from '../layout/Paginator.vue';

export default {
  name: 'XChartLegend',
  components: { XPaginator },
  props: {
    data: {
      type: Array,
      default: () => ([]),
    },
    pageSize: {
      type: Number,
      default: 10,
    },
  },
  data() {
    return {
      legendFrom: 1,
      legendTo: this.pageSize,
    };
  },
  computed: {
    gridTemplateColumns() {
      const numberColumnWidth = this.numberColumnWidth.toString().length + 1 > 10
        ? 10 : this.numberColumnWidth.toString().length + 1;
      return `grid-template-columns: 24px 1fr minmax(1ch, ${numberColumnWidth}ch) minmax(4ch, 8ch);`;
    },
    showPaginator() {
      return this.data.length > this.pageSize;
    },
    pageData() {
      return this.data.slice(this.legendFrom - 1, this.legendTo);
    },
    numberColumnWidth() {
      return this.pageData.reduce(
        (maxWidth, legendItem) => Math.max(maxWidth, legendItem.value), 10,
      );
    },
    columnValues() {
      const result = [];
      return this.pageData.reduce((columnValues, legendItem) => {
        columnValues.push({
          value: '',
          class: ['column-color', legendItem.class],
          onClick: () => {},
        });
        columnValues.push({
          value: legendItem.name,
          class: 'column-name',
          onClick: () => this.$emit('on-item-click', legendItem.index),
        });
        columnValues.push({
          value: legendItem.value,
          class: 'column-value',
          onClick: () => {},
        });
        columnValues.push({
          value: legendItem.percentage || '(0%)',
          class: 'column-percentage',
          onClick: () => {},
        });
        return columnValues;
      }, result);
    },
  },
};
</script>

<style lang="scss" scoped>

  .x-chart-legend {
    display: flex;
    height: 100%;
    flex-direction: column;

    .legend-grid {
      display: grid;
      grid-row-gap: 8px;

      .column-color {
        align-self: center;
        display: inline-block;
        height: 16px;
        width: 16px;
        border-radius: 4px;
        opacity: 0.8;
      }

      .column-name {
        cursor: pointer;
        text-overflow: ellipsis;
        overflow: hidden;
        margin-right: 4px;
        white-space: nowrap;
        height: 24px;
        line-height: 24px;
      }

      .column-value {
        padding-left: 4px;
        white-space: nowrap;
        text-align: end;
        overflow: hidden;
        text-overflow: ellipsis;
        border-left: 1px solid $grey-2;
        line-height: 24px;
      }

      .column-percentage {
        text-align: end;
        line-height: 24px;
      }
    }

    .x-paginator {
      flex-grow: 1;
      align-items: flex-end;
      margin-bottom: -14px;
    }
  }

</style>
