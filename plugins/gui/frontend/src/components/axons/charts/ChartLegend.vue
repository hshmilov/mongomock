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
        :style="{...columnValue.style}"
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

import { formatPercentage } from '@constants/utils';
import { ChartTypesEnum } from '@constants/dashboard';
import defaultChartsColors from '@constants/colors';
import { getItemIndex, getLegendItemColorClass, getRemainderSliceLabel } from '@/helpers/dashboard';
import XPaginator from '../layout/Paginator.vue';

export default {
  name: 'XChartLegend',
  components: { XPaginator },
  props: {
    data: {
      type: Array,
      default: () => {},
    },
    baseColor: {
      type: String,
      default: undefined,
    },
    intersectingColors: {
      type: Array,
      default: () => [],
    },
    pageSize: {
      type: Number,
      default: 10,
    },
    chartId: {
      type: String,
      required: true,
    },
    chartMetric: {
      type: String,
      required: true,
      validator(value) {
        return [...Object.values(ChartTypesEnum)].indexOf(value) > -1;
      },
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
      return this.pageData.reduce((columnValues, legendItem, index) => {
        const { portion, remainder, value, name } = legendItem;
        let legendItemColorIndex = this.getItemIndex(legendItem, this.chartMetric);
        legendItemColorIndex = legendItemColorIndex < 0 ? index : legendItemColorIndex;
        const colorClassname = this.getLegendItemColorClass(legendItemColorIndex, legendItem);
        columnValues.push({
          value: '',
          class: ['column-color', colorClassname],
          style: this.getLegentItemColorStyle({ chartColor: legendItem.chart_color, colorClassname }),
          onClick: () => {},
        });
        columnValues.push({
          value: remainder ? getRemainderSliceLabel(legendItem) : name,
          class: 'column-name',
          onClick: () => this.$emit('on-item-click', index),
        });
        columnValues.push({
          value,
          class: 'column-value',
          onClick: () => {},
        });
        columnValues.push({
          value: formatPercentage(portion) || '(0%)',
          class: 'column-percentage',
          onClick: () => {},
        });
        return columnValues;
      }, result);
    },
  },
  created() {
    this.getItemIndex = getItemIndex.bind(this);
    this.getLegendItemColorClass = getLegendItemColorClass.bind(this);
  },
  methods: {
    getLegentItemColorStyle({ chartColor, colorClassname }) {
      if (chartColor) {
        return {
          fill: chartColor,
          backgroundColor: chartColor,
        };
      }
      const [selectedFirstIntersectingColor, selectedSecondIntersectingColor] = this.intersectingColors;
      if (colorClassname === 'pie-fill-1') {
        return {
          fill: this.baseColor,
          backgroundColor: this.baseColor,
        };
      }
      if (colorClassname === 'pie-fill-2' && selectedFirstIntersectingColor) {
        return {
          fill: selectedFirstIntersectingColor,
          backgroundColor: selectedFirstIntersectingColor,
        };
      }
      if (colorClassname === 'pie-fill-3' && selectedSecondIntersectingColor) {
        return {
          fill: selectedSecondIntersectingColor,
          backgroundColor: selectedSecondIntersectingColor,
        };
      }

      if (colorClassname === 'fill-intersection-2-3') {
        const firstIntersectionColor = selectedFirstIntersectingColor || defaultChartsColors.intersectingColors[0];
        const secondIntersectionColor = selectedSecondIntersectingColor || defaultChartsColors.intersectingColors[1];

        return {
          fill: `url(#defined-colors-${this.chartId})`,
          background: `repeating-linear-gradient(45deg, ${firstIntersectionColor}, 
                ${firstIntersectionColor} 4px,
                 ${secondIntersectionColor} 4px,
                  ${secondIntersectionColor} 8px)`,
        };
      }
      if (colorClassname.includes('indicator-fill-') && selectedFirstIntersectingColor) {
        return {
          fill: selectedFirstIntersectingColor,
          backgroundColor: selectedFirstIntersectingColor,
        };
      }
      return {};
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
