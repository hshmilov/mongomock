<template>
  <div class="x-chart-stacked">
    <XChartTooltip
      :header="tooltipDetails.header"
      :body="tooltipDetails.body"
    >
      <div
        slot="tooltipActivator"
        class="matrix-container"
      >
        <div
          class="groups-container"
        >
          <div
            v-for="(group, groupIndex) in pageData"
            :key="groupIndex"
          >
            <div class="intersection-group">
              <div
                v-for="(intersection, index) in group.intersections"
                :key="index"
                class="intersection-slice"
                :class="getColorClass(intersection.intersectionIndex)"
                :style="getSliceStyle(intersection)"
                @click="onClick(intersection.originalIndex)"
                @mouseover="updateHover(intersection, group)"
                @mouseout="clearHover()"
              />
              <div
                class="group-total"
                :title="group.value"
              >
                {{ group.value }}
              </div>
            </div>
            <div
              class="intersection-group group-name"
              :title="group.name"
            >
              {{ group.name }}
            </div>
          </div>
        </div>
        <div class="matrix-footer">
          <div class="separator" />
          <div class="matrix-total">
            {{ 'Total ' + totalValue }}
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
import XPaginator from '../layout/Paginator.vue';
import XChartTooltip from './ChartTooltip.vue';

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
      // eslint-disable-next-line arrow-body-style
      return this.intersectionGroups.reduce((totalValue, currentGroup) => {
        return totalValue + currentGroup.value;
      }, 0);
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
      // eslint-disable-next-line arrow-body-style
      return this.intersectionGroups.reduce((maxValue, currentGroup) => {
        return currentGroup.value > maxValue ? currentGroup.value : maxValue;
      }, 0);
    },
    tooltipDetails() {
      if (!this.hover.intersection) {
        return {};
      }

      const { value } = this.hover.intersection;
      const intersectionName = this.hover.intersection.name;
      const headerClass = `tooltip-header-content ${this.getColorClass(this.hover.intersection.intersectionIndex)}`;

      const { name } = this.hover.group;
      const groupValue = this.hover.group.value;

      return {
        header: {
          class: headerClass,
          name,
        },
        body: {
          name: intersectionName,
          value,
          percentage: this.getValuePercentage(value, groupValue),
        },
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
    getValuePercentage(value, groupValue) {
      let percentage = (value / groupValue) * 100;
      if (percentage) {
        percentage = `(${percentage % 1 ? percentage.toFixed(2) : percentage}%)`;
      } else {
        percentage = '';
      }
      return percentage;
    },
    getSliceStyle(intersection) {
      return {
        width: `${this.getSliceWidth(intersection.value)}px`,
      };
    },
    getSliceWidth(sliceValue) {
      return (sliceValue / this.maxGroupValue) * this.maxBarWidth;
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

      .matrix-container {
        height: 100%;

        .groups-container {
          height: 240px;

          .intersection-group {
            margin-bottom: 4px;
            display: flex;

            .intersection-slice {
              cursor: pointer;
              opacity: 0.8;
              transition: opacity ease-in 0.4s;

              &:hover {
                opacity: 1;
              }
            }

            .group-total {
              max-width: 60px;
              overflow: hidden;
              text-overflow: ellipsis;
              align-self: center;
              padding-left: 4px;
            }

            &.group-name {
              max-width: 250px;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }
          }
        }

        .matrix-total {
          text-align: center;
          line-height: 24px;
        }
      }
    }
  }

</style>
