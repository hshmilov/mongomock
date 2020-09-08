<template>
  <XChart
    draggable
    class="x-chart-vizualization x-summary-vizualization"
    :active-space-id="activeSpaceId"
    :chart="chart"
    :is-empty="isEmpty"
    v-on="$listeners"
  >
    <template slot-scope="{ data, pageData, history }">
      <div class="summary-chart-wrapper">
        <XSummary
          :data="data.content"
          @click-one="displaySegmentResults($event, pageData, history)"
        />
      </div>
    </template>
  </XChart>
</template>

<script>
import { mapMutations } from 'vuex';
import _isNil from 'lodash/isNil';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import XSummary from '@axons/charts/Summary.vue';
import XChart from '../Chart.vue';

export default {
  name: 'XSummaryVisualization',
  components: { XChart, XSummary },

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
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    isEmpty(content) {
      return !content.length || !content[0].value;
    },
    displaySegmentResults(index, data, history) {
      const dataEntry = data[index];
      const { view, module, name, view_id: viewId } = dataEntry;
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
.x-summary-vizualization {
  .summary-chart-wrapper {
    height: 100%;
    display: flex;
    flex-direction: row;
    align-items: center;
  }
}
</style>
