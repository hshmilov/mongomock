<template>
  <XChart
    pagination
    history
    sortable
    draggable
    display-count
    :page-limit="limit"
    :active-space-id="activeSpaceId"
    :chart="chart"
    :is-empty="isEmpty"
    :format-count-label="formatCountLabel"
    v-on="$listeners"
  >
    <template slot-scope="{ data, pageData, history }">
      <XStacked
        :data="data.content"
        :page-data="pageData"
        :chart-config="chart.config"
        @click-one="displaySegmentResults($event, pageData, history)"
      />
    </template>
  </XChart>
</template>

<script>
import { mapMutations } from 'vuex';
import _get from 'lodash/get';
import _isNil from 'lodash/isNil';
import { ChartTypesEnum } from '@constants/dashboard';
import XStacked from '@axons/charts/Stacked.vue';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import XChart from '../Chart.vue';

export default {
  name: 'XStackedVisualization',
  components: { XChart, XStacked },

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
  data() {
    return { limit: 5 };
  },
  computed: {
    isMetricTypeCompare() {
      const { metric } = this.chart;
      return metric === ChartTypesEnum.compare;
    },
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    isEmpty(content) {
      return !content.length;
    },
    formatCountLabel(strings, chartData) {
      const { content } = chartData;
      const count = content.reduce((sum, currentIntersectionGroup) => sum + currentIntersectionGroup.value, 0);
      return `Total ${count}`;
    },
    displaySegmentResults({ groupIndex, intersectionIndex }, pageData, history) {
      const segment = _get(pageData, `[${groupIndex}].intersections[${intersectionIndex}]`);
      const { view, module, name, view_id: viewId } = segment;
      if (!this.$canViewEntity(module) || _isNil(view)) {
        return;
      }
      this.updateView({
        module,
        view: history ? {
          ...view,
          historical: history,
        } : view,
        name: this.isMetricTypeCompare ? name : undefined,
        selectedView: { uuid: viewId },
      });
      this.$router.push({ path: module });
    },
  },
};
</script>

<style lang="scss">
</style>
