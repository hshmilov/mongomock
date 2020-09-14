<template>
  <XChart
    :legend="!isTooManyValues"
    history
    draggable
    :display-count="!isTooManyValues"
    :search="false"
    :active-space-id="activeSpaceId"
    :trend="isTrendChartLinked && !isTooManyValues"
    :chart="chart"
    :is-empty="isEmpty"
    :format-count-label="formatCountLabel"
    v-on="$listeners"
  >
    <template slot-scope="{ data, pageData, history }">
      <XPie
        :data="data.content"
        :count="data.count"
        :chart-id="chart.uuid"
        :chart-config="chart.config"
        :metric="chart.metric"
        @on-too-many-values="updateTooManyValues"
        @click-one="displaySegmentResults($event, pageData, history)"
      />
    </template>
    <template
      slot="expand"
      slot-scope="{ data, context, history, trend, refreshTrend }"
    >
      <XLegend
        v-if="context === 'legend'"
        :data="data.content"
        :chart-id="chart.uuid"
        :chart-metric="chart.metric"
        :base-color="baseQueryColor"
        :intersecting-colors="intersectingQueriesColors"
        @on-item-click="displaySegmentResults($event, data.content, history)"
      />
      <XChartContent
        v-else-if="context === 'trend'"
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
import _get from 'lodash/get';
import _isNil from 'lodash/isNil';
import XPie from '@axons/charts/Pie.vue';
import XLegend from '@axons/charts/ChartLegend.vue';
import XLine from '@axons/charts/Line.vue';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import { ChartTypesEnum } from '@constants/dashboard';
import XChart from '../Chart.vue';
import XChartContent from '../ChartContent.vue';

export default {
  name: 'XPieVisualization',
  components: {
    XChart,
    XPie,
    XLegend,
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
  data() {
    return {
      isTooManyValues: false,
    };
  },
  computed: {
    isMetricTypeCompare() {
      const { metric } = this.chart;
      return metric === ChartTypesEnum.compare;
    },
    isTrendChartLinked() {
      return _get(this.chart, 'config.show_timeline');
    },
    baseQueryColor() {
      return _get(this.chart, 'config.base_color');
    },
    intersectingQueriesColors() {
      return _get(this.chart, 'config.intersecting_colors');
    },
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    updateTooManyValues(value) {
      this.isTooManyValues = value;
    },
    isEmpty(content) {
      return !content.length || (content.length === 1 && content[0].value === 0);
    },
    displaySegmentResults(sliceIndex, pageData, history) {
      const segment = pageData[sliceIndex];
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
      const count = portion === 1 ? value : Math.round(1 / (portion / value));
      return `Total ${count}`;
    },
  },
};
</script>

<style lang="scss">
</style>
