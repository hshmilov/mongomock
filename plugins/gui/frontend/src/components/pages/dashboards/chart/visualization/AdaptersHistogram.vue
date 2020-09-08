<template>
  <XChart
    pagination
    sortable
    draggable
    history
    exportable
    display-count
    :legend="false"
    :search="false"
    :page-limit="5"
    :active-space-id="activeSpaceId"
    :chart="chart"
    :is-empty="isEmpty"
    :format-count-label="formatCountLabel"
    total-items-name="unique adapters"
    v-on="$listeners"
  >
    <template slot-scope="{ data, pageData, history }">
      <XHistogram
        :data="data.content"
        :condensed="true"
        :page-data="pageData"
        @click-one="displaySegmentResults($event, pageData, history)"
      />
    </template>
  </XChart>
</template>

<script>
import { mapMutations } from 'vuex';
import _isNil from 'lodash/isNil';
import _get from 'lodash/get';
import XHistogram from '@axons/charts/Histogram.vue';
import { ChartTypesEnum } from '@constants/dashboard';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import XChart from '../Chart.vue';

export default {
  name: 'XAdaptersHistogramVisualization',
  components: { XChart, XHistogram },

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
    formatCountLabel(strings, { content }) {
      const entity = _get(this.chart, 'config.entity', '');
      const uniqueItems = _get(content, '[0].uniqueDevices');
      return `Total ${uniqueItems} unique ${entity}`;
    },
    displaySegmentResults(page, pageData, history) {
      const segment = pageData[page];
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
