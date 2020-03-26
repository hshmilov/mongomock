<template>
  <XPage title="axonius dashboard">
    <template v-if="isEmptySystem === null" />
    <template v-else-if="isEmptySystem">
      <XEmptySystem />
    </template>
    <template v-else>
      <XSearchInsights @click="onClickInsights" />
      <XSpaces :spaces="spaces" />
    </template>
  </XPage>
</template>


<script>
import {
  mapState, mapGetters, mapActions,
} from 'vuex';
import XPage from '../axons/layout/Page.vue';
import XEmptySystem from '../networks/onboard/EmptySystem.vue';
import XSearchInsights from '../neurons/inputs/SearchInsights.vue';
import XSpaces from '../networks/dashboard/Spaces.vue';

import viewsMixin from '../../mixins/views';

import {
  FETCH_DISCOVERY_DATA, FETCH_DASHBOARD_SPACES, FETCH_DASHBOARD_PANELS, FETCH_DASHBOARD_FIRST_USE, GET_PANEL_MAP,
} from '../../store/modules/dashboard';
import { IS_EXPIRED } from '../../store/getters';
import { SAVE_VIEW } from '../../store/actions';

export default {
  name: 'XDashboard',
  components: {
    XPage, XEmptySystem, XSearchInsights, XSpaces,
  },
  mixins: [viewsMixin],
  computed: {
    ...mapState({
      dashboard(state) {
        return state.dashboard;
      },
      spaces(state) {
        const panelsById = this.getPanelsMap;
        const addPanelIfExists = (existingPanelsList, panelId) => (
          panelsById[panelId] ? [...existingPanelsList, panelsById[panelId]] : existingPanelsList);
        const getCurrentSpacePanels = (space) => (space.panels_order.reduce(addPanelIfExists, []));
        return state.dashboard.spaces.data.map((space) => ({
          ...space,
          panels: getCurrentSpacePanels(space),
        }));
      },
      devicesView(state) {
        return state.devices.view;
      },
      devicesViewsList(state) {
        return state.devices.views.saved.content.data;
      },
      dashboardFirstUse(state) {
        return state.dashboard.firstUse.data;
      },
    }),
    ...mapGetters({
      isExpired: IS_EXPIRED,
      getPanelsMap: GET_PANEL_MAP,
    }),
    deviceDiscovery() {
      return this.dashboard.dataDiscovery.devices.data;
    },
    seenDevices() {
      return (this.deviceDiscovery && this.deviceDiscovery.seen);
    },
    isEmptySystem() {
      if (this.deviceDiscovery.seen === undefined || this.dashboardFirstUse === null) return null;

      return (!this.seenDevices && this.dashboardFirstUse);
    },
  },
  created() {
    this.fetchDashboardFirstUse();
    if (this.isExpired) {
      this.getDashboardData();
    }
  },
  beforeDestroy() {
    clearTimeout(this.timer);
  },
  methods: {
    ...mapActions({
      fetchDiscoveryData: FETCH_DISCOVERY_DATA,
      fetchDashboardFirstUse: FETCH_DASHBOARD_FIRST_USE,
      fetchSpaces: FETCH_DASHBOARD_SPACES,
      fetchPanels: FETCH_DASHBOARD_PANELS,
      saveView: SAVE_VIEW,
    }),
    onClickInsights() {
      this.$router.push({ name: 'Insights Explorer' });
    },
    getDashboardData() {
      return Promise.all([
        this.fetchDiscoveryData({ module: 'devices' }), this.fetchDiscoveryData({ module: 'users' }),
        this.fetchSpaces(),
      ]).then(this.fetchPanels).then(() => {
        if (this._isDestroyed) return;
        this.timer = setTimeout(this.getDashboardData, 30000);
      });
    },
    viewsCallback() {
      this.getDashboardData();
    },
  },
};
</script>


<style lang="scss">

</style>
