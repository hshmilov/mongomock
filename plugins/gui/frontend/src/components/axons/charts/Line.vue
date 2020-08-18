<template>
  <GChart
    type="LineChart"
    :data="processedData"
    :options="chartOptions"
    class="x-line"
    v-on="$listeners"
  />
</template>

<script>
import { GChart } from 'vue-google-charts';
import defaultChartColors from '@constants/colors';

export default {
  name: 'XLine',
  components: { GChart },
  props: {
    data: {
      type: Array,
      required: true,
    },
    showReadySpinner: {
      type: Boolean,
      required: false,
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
    processedData() {
      if (!this.data[0]) return [];
      const lastValues = Array(this.data[0].length - 1).fill(null);
      return [
        this.data[0],
        ...this.data.slice(1).map((row) => {
          const [day, ...values] = row;
          values.forEach((value, index) => {
            if (value) {
              lastValues[index] = value;
            }
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
          width: '100%', height: '80%',
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
        height: 240px;
    }
</style>
