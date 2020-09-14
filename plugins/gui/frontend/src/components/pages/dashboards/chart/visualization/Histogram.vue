<template>
  <XChart
    pagination
    history
    display-count
    :legend="false"
    :trend="isTrendChartLinked"
    :search="isSearchEnabled"
    :sortable="isSortEnabled"
    :page-limit="5"
    :exportable="isExportEabled"
    :active-space-id="activeSpaceId"
    :chart="chart"
    :is-empty="isEmpty"
    :format-count-label="formatCountLabel"
    v-on="$listeners"
  >
    <template slot-scope="{ data, pageData, history }">
      <XHistogram
        :data="data.content"
        :page-data="pageData"
        :chart-config="chart.config"
        :metric="chart.metric"
        @click-one="displaySegmentResults($event, pageData, history)"
      />
    </template>
    <template
      slot="expand"
      slot-scope="{ context, trend, refreshTrend}"
    >
      <XChartContent
        v-if="context === 'trend'"
        :loading="trend.loading"
        :error="trend.error"
        :empty="!trend.content.length"
        @refresh="refreshTrend"
      >
        <XLine
          :data="trend.content"
        />
      </XChartContent>
    </template>
  </XChart>
</template>

<script>
import { mapMutations } from 'vuex';
import _isNil from 'lodash/isNil';
import _get from 'lodash/get';
import XHistogram from '@axons/charts/Histogram.vue';
import XLine from '@axons/charts/Line.vue';
import { ChartTypesEnum, ChartViewEnum } from '@constants/dashboard';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import XChart from '../Chart.vue';
import XChartContent from '../ChartContent.vue';

export default {
  name: 'XHistogramVisualization',
  components: {
    XChart,
    XHistogram,
    XLine,
    XChartContent,
  },

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
    isMetricTypeSegment() {
      const { metric } = this.chart;
      return metric === ChartTypesEnum.segment;
    },
    isMetricTypeCompare() {
      const { metric } = this.chart;
      return metric === ChartTypesEnum.compare;
    },
    isSearchEnabled() {
      return this.chart.view === ChartViewEnum.histogram && this.isMetricTypeSegment;
    },
    isSortEnabled() {
      return this.isMetricTypeSegment || this.isMetricTypeCompare;
    },
    isExportEabled() {
      return this.isMetricTypeSegment;
    },
    isTrendChartLinked() {
      return _get(this.chart, 'config.show_timeline');
    },
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    isEmpty(content) {
      return !content.length;
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
    formatCountLabel(_, data) {
      if (!data.content.length) {
        return 0;
      }
      const [{ value, portion }] = data.content;
      if (!portion || !value) {
        return 0;
      }
      const count = portion === 1 ? value : Math.round(1 / (portion / value));
      return `Total ${count}`;
    },
  },
};
</script>

<style lang="scss">
</style>
