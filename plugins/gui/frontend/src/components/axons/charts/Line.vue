<template>
  <GChart
    type="LineChart"
    :data="processedData"
    :options="chartOptions"
    class="x-line"
  />
</template>

<script>
import { GChart } from 'vue-google-charts';

export default {
  name: 'XLine',
  components: { GChart },
  props: { data: { required: true } },
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
    chartOptions() {
      return {
        chartArea: {
          width: '100%', height: '80%',
        },
        colors: ['#15C59E', '#1593C5', '#8A32BB'],
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
