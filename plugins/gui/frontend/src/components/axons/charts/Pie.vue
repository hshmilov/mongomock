<template>
  <div
    class="x-pie"
    :class="{disabled: readOnly}"
  >
    <XChartTooltip
      :header="tooltipDetails.header"
      :body="tooltipDetails.body"
      :additional-data="tooltipDetails.additionalData"
    >
      <svg
        slot="tooltipActivator"
        viewBox="-1 -1 2 2"
        @mouseout="inHover = -1"
      >
        <defs>
          <linearGradient id="intersection-2-4">
            <stop
              class="pie-stop-2"
              offset="0%"
            />
            <template v-for="n in 9">
              <stop
                :class="`pie-stop-${!(n % 2) ? 4 : 2}`"
                :offset="`${n}0%`"
              />
              <stop
                :class="`pie-stop-${!(n % 2) ? 2 : 4}`"
                :offset="`${n}0%`"
              />
            </template>
            <stop
              class="pie-stop-4"
              offset="100%"
            />
          </linearGradient>
        </defs>
        <g
          v-for="(slice, index) in slices"
          :key="index"
          :class="`slice-${index}`"
          @click="onClick(index)"
          @mouseover="inHover = index"
        >
          <path
            :d="slice.path"
            :class="`filling ${slice.class} ${inHover === index? 'in-hover' : ''}`"
          />
          <text
            v-if="showPercentageText(slice.value)"
            class="scaling"
            text-anchor="middle"
            :x="slice.middle.x"
            :y="slice.middle.y"
          >
            {{ Math.round(slice.value * 100) }}%
          </text>
        </g>
      </svg>
    </XChartTooltip>
  </div>
</template>

<script>
import XChartTooltip from './ChartTooltip.vue';

export default {
  name: 'XPie',
  components: {
    XChartTooltip,
  },
  props: {
    data: {
      type: Array,
      required: true,
    },
    forceText: {
      type: Boolean,
      default: false,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      inHover: -1,
    };
  },
  computed: {
    processedData() {
      const processData = this.data.map((item, index) => {
        const { value, remainder } = item;
        const modifiedItem = item;
        modifiedItem.index = index;
        modifiedItem.percentage = this.getPercentage(value);
        modifiedItem.name = remainder ? 'Excluding' : modifiedItem.name;
        modifiedItem.class = this.getItemClass(item, index);
        return modifiedItem;
      });

      this.$emit('legend-data-modified', processData);
      return processData;
    },
    slices() {
      let cumulativePortion = 0;
      return this.processedData.map((slice) => {
        // Starting slice at the end of previous one, and ending after percentage defined for item
        const [startX, startY] = this.getCoordinatesForPercent(cumulativePortion);
        cumulativePortion += slice.value / 2;
        const [middleX, middleY] = this.getCoordinatesForPercent(cumulativePortion);
        cumulativePortion += slice.value / 2;
        const [endX, endY] = this.getCoordinatesForPercent(cumulativePortion);
        return {
          ...slice,
          path: [
            `M ${startX} ${startY}`, // Move
            `A 1 1 0 ${slice.value > 0.5 ? 1 : 0} 1 ${endX} ${endY}`, // Arc
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

      const {
        percentage, name, remainder, intersection,
      } = this.processedData[this.inHover];

      const value = this.processedData[this.inHover].numericValue;
      const colorClass = this.processedData[this.inHover].class;
      let tooltip;
      if (intersection) {
        tooltip = this.getIntersectionTooltip(name, value, percentage, colorClass);
      } else if (this.inHover === 0 && remainder) {
        tooltip = this.getExcludingTooltip(name, value, percentage, colorClass);
      } else {
        tooltip = this.getNormalTooltip(name, value, percentage, colorClass);
      }
      return tooltip;
    },
  },
  methods: {
    getItemClass(item) {
      if (this.data.length === 2 && item.index === 1 && this.data[0].remainder) {
        return `indicator-fill-${Math.ceil(item.value * 4)}`;
      }
      const modIndex = (item.index % 10) + 1;
      if (item.intersection) {
        return `fill-intersection-${modIndex - 1}-${modIndex + 1}`;
      }
      return `pie-fill-${modIndex}`;
    },
    getPercentage(value) {
      let percentage = value * 100;
      percentage = percentage % 1 ? percentage.toFixed(2) : percentage;
      if (percentage < 0) {
        percentage = 100 + percentage;
      }
      return `(${percentage}%)`;
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
          value,
          percentage,
        },
        additionalData: this.processedData.filter((data) => !data.intersection && !data.remainder),
      };
    },
    getIntersectionTooltip(name, value, percentage, colorClass) {
      return {
        header: {
          class: colorClass,
          name: 'Intersection',
          value,
          percentage,
        },
        additionalData: [{
          ...this.processedData[this.inHover - 1],
        }, {
          ...this.processedData[this.inHover + 1],
        }],
      };
    },
    getCoordinatesForPercent(portion) {
      return [Math.cos(2 * Math.PI * portion), Math.sin(2 * Math.PI * portion)];
    },
    showPercentageText(val) {
      return (this.forceText && val > 0) || val > 0.04;
    },
    onClick(index) {
      if (this.readOnly) return;
      this.$emit('click-one', index);
    },
  },
};
</script>

<style lang="scss" scoped>
  .x-pie {
      margin: auto;
      width: 240px;
      position: relative;
      .fill-intersection-2-4 {
          fill: url(#intersection-2-4);
          background: repeating-linear-gradient(45deg, nth($pie-colours, 2),
                  nth($pie-colours, 2) 4px, nth($pie-colours, 4) 4px, nth($pie-colours, 4) 8px);
      }

      g {
          cursor: pointer;

          path {
              opacity: 0.8;
              transition: opacity ease-in 0.4s;

              &.in-hover {
                  opacity: 1;
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
  }

</style>
