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
      :limit="8"
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
        (maxWidth, legendItem) => Math.max(maxWidth, legendItem.numericValue), 10,
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
          value: legendItem.numericValue,
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
        margin-top: 1px;
        display: inline-block;
        height: 16px;
        width: 16px;
        border-radius: 4px;
        opacity: 0.8;

        &.fill-intersection-2-4 {
            fill: url(#intersection-2-4);
            background: repeating-linear-gradient(45deg, nth($pie-colours, 2),
                    nth($pie-colours, 2) 4px, nth($pie-colours, 4) 4px, nth($pie-colours, 4) 8px);
        }
      }

      .column-name {
        cursor: pointer;
        text-overflow: ellipsis;
        overflow: hidden;
        margin-right: 4px;
      }

      .column-value {
        padding-left: 4px;
        white-space: nowrap;
        text-align: end;
        overflow: hidden;
        text-overflow: ellipsis;
        border-left: 1px solid $grey-2;
      }

      .column-percentage {
        text-align: end;
      }
    }

    .x-paginator {
      flex-grow: 1;
      align-items: flex-end;
    }
  }

</style>
