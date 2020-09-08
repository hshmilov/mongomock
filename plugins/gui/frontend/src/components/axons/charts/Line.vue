<template>
  <div :class="classNames">
    <GChart
      type="LineChart"
      :data="processedData"
      :options="chartOptions"
      class="timeline-chart"
      v-on="$listeners"
    />
    <div
      v-if="isPartial"
      class="partial-warning"
    >
      <XIcon
        family="symbol"
        type="warning"
        :style="{fontSize: '20px'}"
      />
      <span>
        Timeline charts may be showing partial data since historical snapshots are disabled.
      </span>
    </div>
  </div>
</template>

<script>
import { mapState } from 'vuex';
import _get from 'lodash/get';
import _isNil from 'lodash/isNil';
import { GChart } from 'vue-google-charts';
import XIcon from '@axons/icons/Icon';
import defaultChartColors from '@constants/colors';

export default {
  name: 'XLine',
  components: { GChart, XIcon },
  props: {
    data: {
      type: Array,
      required: true,
    },
    chartConfig: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      defaultChartColors,
    };
  },
  computed: {
    ...mapState({
      historyEnabled(state) {
        return _get(state, 'configuration.data.global.historyEnabled', false);
      },
    }),
    isPartial() {
      return !this.historyEnabled;
    },
    classNames() {
      return {
        'x-line': true,
        'x-line--partial': this.isPartial,
      };
    },
    processedData() {
      if (!this.data[0]) return [];
      const lastValues = Array(this.data[0].length - 1).fill(null);
      return [
        this.data[0].map((entry) => {
          if (typeof entry === 'string') return entry;
          return entry.label;
        }),
        ...this.data.slice(1).map((row) => {
          const [day, ...values] = row;
          values.forEach((value, index) => {
            lastValues[index] = _isNil(value) ? 0 : value;
          });
          return [new Date(day), ...lastValues];
        }),
      ];
    },
    chartColors() {
      if (this.chartConfig && this.chartConfig.views[0]) {
        return this.chartConfig.views.map(
          (item, i) => (item.chart_color ? item.chart_color
            : this.defaultChartColors.lineColors[i]),
        );
      }
      return this.defaultChartColors.lineColors;
    },
    chartOptions() {
      return {
        chartArea: {
          width: '70%',
          height: '80%',
        },
        colors: this.chartColors,
        vAxis: {
          textPosition: 'in',
          textStyle: {
            fontSize: 12,
          },
        },
        hAxis: {
          textPosition: 'out',
          slantedText: false,
          textStyle: {
            fontSize: 12,
          },
          gridlines: {
            color: '#DEDEDE',
          },
        },
        legend: {
          position: 'top',
        },
        tooltip: {
          textStyle: {
            fontSize: 12,
          },
          showColorCode: true,
          ignoreBounds: false,
          isHtml: true,
        },
        interpolateNulls: true,
      };
    },
  },
};
</script>

<style lang="scss">
.x-line {
  height: 90%;
  max-width: 100%;
  .timeline-chart {
    height: 100%;
    width: 350px;
    rect:first-of-type {
      fill: transparent;
    }
  }
  &--partial {
    height: 70%;
    .partial-warning {
      display: flex;
      flex-direction: row;
      align-items: center;
      padding-top: 24px;
      .x-icon {
        width: 20%;
        padding-right: 4px;
      }
      span {
        text-align: left;
      }
    }
  }
}
</style>
