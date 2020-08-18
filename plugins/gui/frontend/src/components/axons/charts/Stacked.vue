<template>
  <div class="x-chart-stacked">
    <XChartTooltip
      :header="tooltipDetails.header"
      :body="tooltipDetails.body"
      :style-object="tooltipDetails.styleObject"
    >
      <div
        slot="tooltipActivator"
        class="stacked-container"
      >
        <div
          class="groups-container"
        >
          <div
            v-for="(group, groupIndex) in pageData"
            :key="groupIndex"
          >
            <div
              class="intersection-group"
              @mouseleave="clearHover()"
            >
              <div
                v-for="(intersection, index) in group.intersections"
                :key="index"
                :style="getSliceStyle(intersection)"
                :class="getSliceClass(intersection.intersectionIndex)"
                class="intersection-slice"
                @click="onClick(intersection.originalIndex)"
              >
                <div
                  class="tooltip-invoker"
                  @mouseenter="updateHover(intersection, group)"
                />
              </div>
              <div
                class="group-total"
                :title="group.value"
              >
                {{ group.value }}
              </div>
            </div>
            <div class="intersection-group">
              <span
                class="group-name"
                :title="group.name"
              >
                {{ group.name }}
              </span>
            </div>
          </div>
        </div>
        <div>
          <div class="separator" />
          <div class="stacked-total">
            Total {{ totalValue }}
          </div>
          <XPaginator
            :from.sync="dataFrom"
            :to.sync="dataTo"
            :limit="limit"
            :count="dataLength"
          />
        </div>
      </div>
    </XChartTooltip>
  </div>
</template>

<script>
import _get from 'lodash/get';

import { formatPercentage } from '@constants/utils';
import XPaginator from '../layout/Paginator.vue';
import XChartTooltip from './ChartTooltip.vue';
import defaultChartsColors from '../../../constants/colors';
import { getVisibleTextColor } from '@/helpers/colors';

export default {
  name: 'XStacked',
  components: { XPaginator, XChartTooltip },
  props: {
    data: {
      type: Array,
      required: true,
    },
    limit: {
      type: Number,
      default: 5,
    },
    chartConfig: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      maxBarWidth: 250,
      pieFillArray: [2, 4, 3],
      hover: {
        intersection: null,
        group: null,
      },
      dataFrom: 1,
      dataTo: this.limit,
      defaultChartsColors,
    };
  },
  computed: {
    dataLength() {
      return this.intersectionGroups.length;
    },
    pageData() {
      return this.intersectionGroups.slice(this.dataFrom - 1, this.dataTo);
    },
    totalValue() {
      if (!this.data.length) {
        return 0;
      }
      const [{ portion, value }] = this.data;
      return portion === 1 ? value : Math.round(1 / (portion / value));
    },
    intersectionGroups() {
      let currentBaseIndex = -1;
      return this.data.reduce((groupArray, currentIntersection, originalIndex) => {
        if (!currentIntersection.numericValue) {
          return groupArray;
        }
        if (currentIntersection.baseIndex !== currentBaseIndex) {
          groupArray.push({
            name: currentIntersection.name,
            intersections: [],
            value: currentIntersection.value,
          });
          currentBaseIndex = currentIntersection.baseIndex;
        }
        groupArray[groupArray.length - 1].intersections.push({
          name: currentIntersection.intersectionName,
          intersectionIndex: currentIntersection.intersectionIndex,
          value: currentIntersection.numericValue,
          originalIndex,
        });
        return groupArray;
      }, []);
    },
    maxGroupValue() {
      return this.intersectionGroups.reduce((maxValue, currentGroup) => (
        currentGroup.value > maxValue ? currentGroup.value : maxValue), 0);
    },

    tooltipDetails() {
      if (!this.hover.intersection) {
        return {};
      }
      const { value, intersectionIndex } = this.hover.intersection;
      const intersectionName = this.hover.intersection.name;
      const headerClass = `tooltip-header-content ${this.getColorClass(this.hover.intersection.intersectionIndex)}`;

      const { name } = this.hover.group;
      const groupValue = this.hover.group.value;

      // Styles for pre-defined chart colors.

      const tooltipStyles = {
        backgroundColor: this.getIntersectingColor(intersectionIndex),
        fill: this.getIntersectingColor(intersectionIndex),
        color: getVisibleTextColor(this.getIntersectingColor(intersectionIndex)),
      };


      return {
        header: {
          class: headerClass,
          name,
        },
        body: {
          name: intersectionName,
          value,
          percentage: formatPercentage(value / groupValue),
        },
        styleObject: tooltipStyles,
      };
    },
  },
  methods: {
    updateHover(intersection, group) {
      this.hover = {
        intersection,
        group,
      };
    },
    clearHover() {
      this.hover = {
        intersection: null,
        group: null,
      };
    },
    onClick(index) {
      this.$emit('click-one', index);
    },
    getColorClass(intersectionIndex) {
      return `pie-fill-${this.pieFillArray[intersectionIndex]}`;
    },
    getIntersectingColor(index) {
      if (this.chartConfig.intersecting_colors && this.chartConfig.intersecting_colors[index]) {
        return this.chartConfig.intersecting_colors[index];
      }
      return this.defaultChartsColors.matrixColor[index];
    },
    getSliceStyle(intersection) {
      return {
        width: `${this.getSliceWidth(intersection.value)}px`,
        backgroundColor: this.getIntersectingColor(intersection.intersectionIndex),
        fill: this.getIntersectingColor(intersection.intersectionIndex),
      };
    },
    getSliceWidth(sliceValue) {
      return (sliceValue / this.maxGroupValue) * this.maxBarWidth;
    },
    getSliceClass(intersectionIndex) {
      const colorClass = this.getColorClass(intersectionIndex);
      const hoveredIntersection = _get(this.hover, 'intersection.intersectionIndex');
      const hoverClass = hoveredIntersection === intersectionIndex ? 'hovered' : '';

      return `${colorClass} ${hoverClass}`;
    },
  },
};

</script>

<style lang="scss">
  .x-chart-stacked {
    height: calc(100% - 40px);

    .header-content {
      opacity: 1;
    }

    .separator {
      width: 100%;
      height: 1px;
      background-color: rgba(255, 125, 70, 0.2);
      margin: 12px 0;
    }

    .x-chart-tooltip {
      height: 100%;

      .stacked-container {
        height: 100%;

        .groups-container {
          height: 240px;

          .intersection-group {
            margin-bottom: 4px;
            display: flex;

            .intersection-slice {
              height: 100%;
              min-width: 6px;
              cursor: pointer;
              padding: 0 2px;
              opacity: 1;
              transition: opacity ease-in 0.4s;

              &.hovered {
                opacity: 0.8;
              }

              .tooltip-invoker {
                height: 20px;
              }
            }

            .group-total {
              font-weight: 300;
              max-width: 60px;
              overflow: hidden;
              text-overflow: ellipsis;
              align-self: center;
              padding-left: 4px;
            }

            .group-name {
              max-width: 250px;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }
          }
        }

        .stacked-total {
          font-weight: 300;
          text-align: center;
          line-height: 24px;
        }
      }
    }
  }

</style>
