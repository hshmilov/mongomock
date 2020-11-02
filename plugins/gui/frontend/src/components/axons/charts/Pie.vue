<template>
  <div
    class="x-pie"
  >

    <div
      v-if="tooManyValues"
      class="pie-unavailable"
    >Pie charts cannot exceed 100 different values</div>
    <XChartTooltip
      v-else
      :header="tooltipDetails.header"
      :body="tooltipDetails.body"
      :additional-data="tooltipDetails.additionalData"
      :style-object="tooltipDetails.styleObject"
      :intersecting="tooltipDetails.intersecting"
    >
      <svg
        slot="tooltipActivator"
        viewBox="-1 -1 2 2"
        @mouseout="inHover = -1"
      >
        <XIntersectionSlice
          :chartId="chartId"
          :includesIntersectionColors="false"
          :intersecting-colors="customIntersectingColors"
        />

        <g
          v-for="(slice, index) in slices"
          :key="index"
          :class="`slice-${index}`"
          @click="onClick(index)"
          @mouseover="inHover = index"
        >
          <path
            :d="slice.path"
            :style="slice.sliceColorStyle"
            :class="`filling ${slice.class} ${inHover === index? 'in-hover' : ''}`"
          />
          <text
            v-if="showPercentageText(slice.portion)"
            class="scaling"
            :style="getTextColor(slice)"
            text-anchor="middle"
            :x="slice.middle.x"
            :y="slice.middle.y"
          >
            {{ Math.round(slice.portion * 100) }}%
          </text>
        </g>
      </svg>
    </XChartTooltip>
  </div>
</template>

<script>
import _sumBy from 'lodash/sumBy';
import _get from 'lodash/get';
import { formatPercentage } from '@constants/utils';
import defaultChartsColors from '@constants/colors';
import { ChartTypesEnum } from '@constants/dashboard';
import XChartTooltip from './ChartTooltip.vue';
import XIntersectionSlice from './IntersectionSlice.vue';
import { getVisibleTextColor } from '@/helpers/colors';
import { getItemIndex, getLegendItemColorClass, getRemainderSliceLabel } from '@/helpers/dashboard';

export default {
  name: 'XPie',
  components: {
    XChartTooltip,
    XIntersectionSlice,
  },
  props: {
    data: {
      type: Array,
      required: true,
    },
    count: {
      type: Number,
      required: true,
    },
    metric: {
      type: String,
      default: '',
    },
    chartConfig: {
      type: Object,
      default: () => {},
    },
    chartId: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      inHover: -1,
      defaultChartsColors,
    };
  },
  computed: {
    tooManyValues() {
      const tooManyValues = this.count > 100;
      this.$emit('on-too-many-values', tooManyValues);
      return tooManyValues;
    },
    processedData() {
      const processData = this.data.map((item, index) => {
        const { portion, remainder, index_in_config: indexInConfig } = item;

        const colorClassname = this.getLegendItemColorClass(index, item);
        const sliceColorStyle = this.getPieSliceStyleObject(colorClassname, indexInConfig);
        return {
          ...item,
          index,
          class: colorClassname,
          percentage: formatPercentage(portion),
          name: remainder ? getRemainderSliceLabel(item) : item.name,
          sliceColorStyle,
        };
      });

      return processData;
    },
    slices() {
      let cumulativePortion = 0;
      return this.processedData.map((slice) => {
        // Starting slice at the end of previous one, and ending after percentage defined for item
        const [startX, startY] = this.getCoordinatesForPercent(cumulativePortion);
        cumulativePortion += slice.portion / 2;
        const [middleX, middleY] = this.getCoordinatesForPercent(cumulativePortion);
        cumulativePortion += slice.portion / 2;
        const [endX, endY] = this.getCoordinatesForPercent(cumulativePortion);
        return {
          ...slice,
          path: [
            `M ${startX} ${startY}`, // Move
            `A 1 1 0 ${slice.portion > 0.5 ? 1 : 0} 1 ${endX} ${endY}`, // Arc
            'L 0 0', // Line
          ].join(' '),
          middle: { x: middleX * 0.7, y: middleY * (middleY > 0 ? 0.8 : 0.5) },
        };
      });
    },
    tooltipDetails() {
      if (!this.data || this.data.length === 0 || this.inHover === -1) {
        return {};
      }
      const hoveredItem = this.processedData[this.inHover];
      const {
        percentage, name, remainder, intersection, value, class: colorClass,
      } = hoveredItem;

      let tooltip;
      if (intersection) {
        tooltip = this.getIntersectionTooltip(name, value, percentage, colorClass);
      } else if (this.inHover === 0 && remainder) {
        tooltip = this.getExcludingTooltip(name, value, percentage, colorClass);
      } else {
        tooltip = this.getNormalTooltip(name, value, percentage, colorClass);
      }

      const styleObject = { ...hoveredItem.sliceColorStyle };
      const pieSliceColorIndex = this.getItemIndex(this.inHover, hoveredItem);
      styleObject.color = getVisibleTextColor(styleObject.fill
              || defaultChartsColors.pieColors[pieSliceColorIndex % 10]);

      return {
        ...tooltip,
        styleObject,
      };
    },
    customIntersectingColors() {
      return _get(this.chartConfig, 'intersecting_colors', []);
    },
    customViewsColors() {
      return _get(this.chartConfig, 'views', []).map((view) => view.chart_color);
    },
    styleObject() {
      // If colors defined - mapping it into new style object
      let styleObject = {};
      if (this.metric === ChartTypesEnum.intersect) {
        styleObject = {};
      }
      return styleObject;
    },
  },
  created() {
    this.getItemIndex = getItemIndex.bind(this);
    this.getLegendItemColorClass = getLegendItemColorClass.bind(this);
  },
  methods: {
    getPieSliceStyleObject(sliceClassname, index) {
      if (this.customViewsColors.length) {
        return {
          backgroundColor: this.customViewsColors[index],
          fill: this.customViewsColors[index],
        };
      }

      const baseColor = this.chartConfig.base_color || this.defaultChartsColors.pieColors[0];
      const colorByIndex = (i) => (this.customIntersectingColors[i]
              || this.defaultChartsColors.intersectingColors[i]);
      const firstIntersectionColor = colorByIndex(0);
      const secondIntersectionColor = colorByIndex(1);
      if (sliceClassname === 'fill-intersection-2-3') {
        return {
          fill: this.customIntersectingColors.length ? `url(#defined-colors-${this.chartId})` : 'intersection-2-3',
          background: `repeating-linear-gradient(45deg, ${firstIntersectionColor}, 
              ${firstIntersectionColor} 4px, ${secondIntersectionColor} 4px, ${secondIntersectionColor} 8px)`,
        };
      }
      if (sliceClassname === 'pie-fill-1') {
        return {
          fill: baseColor,
          backgroundColor: baseColor,
        };
      }
      if (sliceClassname === 'pie-fill-2') {
        return {
          fill: firstIntersectionColor,
          backgroundColor: firstIntersectionColor,
        };
      }
      if (sliceClassname === 'pie-fill-3') {
        return {
          fill: secondIntersectionColor,
          backgroundColor: secondIntersectionColor,
        };
      }
      if (sliceClassname.includes('indicator-fill-') && this.customIntersectingColors[0]) {
        return {
          fill: firstIntersectionColor,
          backgroundColor: firstIntersectionColor,
        };
      }
      return {};
    },
    getNormalTooltip(name, value, percentage, colorClass) {
      return {
        header: {
          class: colorClass,
          name,
        },
        body: {
          value,
          percentage,
        },
      };
    },
    getExcludingTooltip(name, value, percentage, colorClass) {
      return {
        header: {
          class: colorClass,
          name,
        },
        body: {
          value,
          percentage,
        },
      };
    },
    getIntersectionTooltip(name, value, percentage, colorClass) {
      return {
        header: {
          class: colorClass,
          name: 'Intersection',
          value,
          percentage,
          intersecting: true,
        },
        additionalData: [{
          ...this.data[this.inHover - 1],
        }, {
          ...this.data[this.inHover + 1],
        }],
      };
    },
    getCoordinatesForPercent(portion) {
      return [Math.cos(2 * Math.PI * portion), Math.sin(2 * Math.PI * portion)];
    },
    showPercentageText(val) {
      return val > 0.04;
    },
    onClick(index) {
      this.$emit('click-one', index);
    },
    getTextColor(slice) {
      const sliceBgColor = _get(slice, 'sliceColorStyle.backgroundColor');
      return sliceBgColor ? {
        color: getVisibleTextColor(sliceBgColor),
        fill: getVisibleTextColor(sliceBgColor),
      } : {};
    },
  },
};
</script>

<style lang="scss" scoped>
  .x-pie {
      margin: auto;
      width: 240px;
      position: relative;

    .pie-unavailable {
      font-size: 20px;
      text-align: center;
      position: absolute;
      bottom: 50%;

      &::after {
        content: '.';
        font-size: 60px;
        color: $theme-orange;
        display: inline-block;
        line-height: 20px;
      }
    }

    g {
        cursor: pointer;

        path {
            opacity: 1;
            transition: opacity ease-in 0.4s;

            &.in-hover {
                opacity: 0.8;
            }
        }

        text {
            font-size: 1%;
            fill: $theme-black;
        }
    }

    &.disabled g {
        cursor: default;
    }

    .x-tooltip {
      &.top {
        bottom: auto;
      }
    }

    .pie-total {
      text-align: center;
      line-height: 24px;
      width: 100%;
      margin-top: 5px;
    }
  }

</style>
