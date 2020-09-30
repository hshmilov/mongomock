<template>
  <div
    class="x-spaces__content"
  >
    <Draggable
      v-model="list"
      tag="transition-group"
      :animation="1000"
      draggable=".x-chart"
      handle=".drag-handle"
      ghost-class="ghost"
      class="charts"
      :move="onChartDragged"
    >
      <Component
        :is="ChartComponentByViewEnum[chart.view]"
        v-for="(chart) in list"
        :key="chart.uuid"
        :chart="chart"
        :active-space-id="activeSpaceId"
        v-on="$listeners"
      />

      <XDataDiscoveryCard
        v-if="isAxoniusDashboard && canViewDevices"
        key="devices-discovery"
        class="device-discovery x-chart"
        :class="`position-${positioningClassnames.indexOf('device-discovery') + 1}`"
        entity="devices"
        name="Device"
      />
      <XDataDiscoveryCard
        v-if="isAxoniusDashboard && canViewUsers"
        key="users-discovery"
        class="user-discovery x-chart"
        :class="`position-${positioningClassnames.indexOf('user-discovery') + 1}`"
        entity="users"
        name="User"
      />
      <XAdapterConnectionsStatus
        v-if="canShowAdapterConnectionStatus && isAxoniusDashboard"
        key="adapter-connections-status x-chart"
        :class="`position-${positioningClassnames.indexOf('adapter-connections-status') + 1}`"
      />
      <XLifecycleChart
        v-if="canRunDiscovery && isAxoniusDashboard"
        key="lifecycle-chart"
        class="x-chart"
        :class="`position-${positioningClassnames.indexOf('lifecycle-chart') + 1}`"
      />
      <div
        v-if="canAddChart"
        key="new-chart"
        class="x-chart x-chart__new"
        name="New Chart"
      >
        <XIcon
          type="plus"
          class="add-button"
          @click.native="$emit('add-new-chart')"
        />
      </div>
    </Draggable>
  </div>
</template>

<script>
import Draggable from 'vuedraggable';
import XHistogram from '@pages/dashboards/chart/visualization/Histogram.vue';
import XAdapterHistogram from '@pages/dashboards/chart/visualization/AdaptersHistogram.vue';
import XPie from '@pages/dashboards/chart/visualization/Pie.vue';
import XLine from '@pages/dashboards/chart/visualization/Line.vue';
import XStacked from '@pages/dashboards/chart/visualization/Stacked.vue';
import XSummary from '@pages/dashboards/chart/visualization/Summary.vue';
import XAdapterConnectionsStatus from '@pages/dashboards/chart/default-charts/AdapterConnectionsStatus.vue';
import XDataDiscoveryCard from '@pages/dashboards/chart/default-charts/DataDiscoveryCard.vue';
import XLifecycleChart from '@pages/dashboards/chart/default-charts/LifecycleChart.vue';
import { ChartComponentByViewEnum } from '@constants/dashboard';

export default {
  name: 'XSpaceContent',
  components: {
    Draggable,
    XHistogram,
    XAdapterHistogram,
    XPie,
    XLine,
    XStacked,
    XSummary,
    XAdapterConnectionsStatus,
    XDataDiscoveryCard,
    XLifecycleChart,
  },
  props: {
    value: {
      type: Array,
      default: () => [],
    },
    activeSpaceId: {
      type: String,
      required: true,
    },
    canAddChart: {
      type: Boolean,
      default: false,
    },
    isAxoniusDashboard: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    list: {
      get() {
        return [...this.value].filter(((chart) => chart.space === this.activeSpaceId));
      },
      set(value) {
        this.$emit('input', value.filter((chart) => chart && chart.uuid));
      },
    },
    canRunDiscovery() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.RunManualDiscovery);
    },
    canViewDevices() {
      return this.$can(this.$permissionConsts.categories.DevicesAssets,
        this.$permissionConsts.actions.View);
    },
    canViewUsers() {
      return this.$can(this.$permissionConsts.categories.UsersAssets,
        this.$permissionConsts.actions.View);
    },
    canShowAdapterConnectionStatus() {
      return this.$can(this.$permissionConsts.categories.Adapters,
        this.$permissionConsts.actions.View);
    },
    positioningClassnames() {
      const positions = [];
      if (this.canViewDevices) {
        positions.push('device-discovery');
      }
      if (this.canViewUsers) {
        positions.push('user-discovery');
      }
      if (this.canShowAdapterConnectionStatus) {
        positions.push('adapter-connections-status');
      }
      if (this.canRunDiscovery) {
        positions.push('lifecycle-chart');
      }
      return positions;
    },
  },
  created() {
    this.ChartComponentByViewEnum = ChartComponentByViewEnum;
  },
  methods: {
    onChartDragged({ relatedContext, draggedContext }) {
      const relatedElement = relatedContext.element;
      const draggedElement = draggedContext.element;
      // block drop cards after addNewChart card
      if (!relatedElement) return false;
      // block changing position of fixed charts
      return (
        ((!relatedElement || !relatedElement.fixed) && !draggedElement.fixed)
      );
    },
  },
};
</script>
