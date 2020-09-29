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

function getLabels(entry) {
  if (typeof entry === 'string') return entry;
  return entry.label;
}

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
      let [xAxisLabels] = this.data;
      xAxisLabels = xAxisLabels.map(getLabels);

      let yAxisValues = this.data.slice(1);
      const lastDiscoverdValue = new Map();

      yAxisValues = yAxisValues.reduce((axisValues, entry) => {
        const [discoveryDay, ...values] = entry;
        const graphEntry = [new Date(discoveryDay)];
        values.forEach((value, index) => {
          if (_isNil(value)) {
          // no history for the current day, use the value of the last discovery for the matching query (line)
            graphEntry.push(lastDiscoverdValue.get(index) || 0);
          } else {
            graphEntry.push(value);
            lastDiscoverdValue.set(index, value);
          }
        });
        return [...axisValues, graphEntry];
      }, []);
      return [
        xAxisLabels,
        ...yAxisValues,
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
