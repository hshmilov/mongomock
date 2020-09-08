<template>
  <XChart
    draggable
    exportable
    :active-space-id="activeSpaceId"
    :chart="chart"
    :is-empty="isEmpty"
    v-on="$listeners"
  >
    <template slot-scope="{ data }">
      <XLine
        :data="data.content"
      />
    </template>
  </XChart>
</template>

<script>
import XLine from '@axons/charts/Line.vue';
import XChart from '../Chart.vue';

export default {
  name: 'XLineVisualization',
  components: { XChart, XLine },

  props: {
    chart: {
      type: Object,
      default: () => ({}),
    },
    activeSpaceId: {
      type: String,
      required: true,
    },
  },
  methods: {
    isEmpty(content) {
      return !content.length;
    },
  },
};
</script>

<style lang="scss">

</style>
