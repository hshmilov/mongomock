<template>
  <XPanels
    :panels="panels"
    :panels-order="panelsOrder"
    new-id="dashboard_wizard"
    class="x-default-space"
    @add="$emit('add')"
    @edit="$emit('edit', $event)"
  >
    <template slot="pre">
      <XDataDiscoveryCard
        :key="1"
        class="device-discovery"
        :data="discoveryData.devices.data"
        name="Device"
        @filter="runFilterDevices"
      />
      <XDataDiscoveryCard
        :key="2"
        class="user-discovery"
        :data="discoveryData.users.data"
        name="User"
        @filter="runFilterUsers"
      />
      <XAdapterConnectionsStatus
        v-if="canShowAdapterConnectionStatus"
        :key="3"
        :data="discoveryData.users.data"
      />
    </template>

    <div
      v-if="canRunDiscovery"
      :key="4"
      slot="post"
      class="x-card chart-lifecycle print-exclude"
    >
      <div class="header">
        <div class="header__title">
          <div
            class="card-title"
            title="System Lifecycle"
          >System Lifecycle</div>
        </div>
      </div>


      <div class="body">

        <XCycle :data="lifecycle.subPhases" />
        <div class="cycle-info">
          <div class="cycle-history">
            <div>Last cycle started at:</div>
            <div
              class="cycle-date"
              :title="lastStartTimeTitle"
            >
              {{ lastStartTime }}
            </div>
            <div>Last cycle completed at:</div>
            <div
              class="cycle-date"
              :title="lastFinishedTimeTitle"
            >
              {{ lastFinishedTime }}
            </div>
          </div>
          <div class="cycle-time">
            <div class="cycle-next">
              <div>Next cycle starts in:</div><div class="cycle-next-time">
                {{ nextRunTime }}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </XPanels>
</template>

<script>
import {
  mapState, mapMutations, mapGetters,
} from 'vuex';
import XDataDiscoveryCard from '@neurons/cards/DataDiscoveryCard.vue';
import XAdapterConnectionsStatus from '@neurons/cards/AdapterConnectionsStatus.vue';
import XPanels from './Panels.vue';
import XCycle from '../../axons/charts/Cycle.vue';

import { UPDATE_DATA_VIEW } from '../../../store/mutations';
import { DATE_FORMAT } from '../../../store/getters';
import { formatDate } from '../../../constants/utils';
import { getTimeZoneDiff } from '@constants/utils';

export default {
  name: 'XDefaultSpace',
  components: {
    XPanels, XDataDiscoveryCard, XCycle, XAdapterConnectionsStatus,
  },
  props: {
    panels: {
      type: Array,
      required: true,
    },
    panelsOrder: {
      type: Array,
      default: null,
    },
  },
  computed: {
    ...mapState({
      discoveryData(state) {
        return state.dashboard.dataDiscovery;
      },
      lifecycle(state) {
        return state.dashboard.lifecycle.data || {};
      },
    }),
    ...mapGetters({
      dateFormat: DATE_FORMAT,
    }),
    nextRunTime() {
      const leftToRun = this.lifecycle.nextRunTime;
      const thresholds = [0, 60, 60 * 60, 24 * 60 * 60];
      const units = ['seconds', 'minutes', 'hours', 'days'];
      for (let i = 1; i < thresholds.length; i++) {
        if (leftToRun < thresholds[i]) {
          if (i === 1) {
            return 'Less than 1 minute';
          }
          return `${Math.round(leftToRun / thresholds[i - 1])} ${units[i - 1]}`;
        }
      }
      return `${Math.round(leftToRun / thresholds[thresholds.length - 1])} ${units[units.length - 1]}`;
    },
    lastStartTime() {
      if (this.lifecycle.lastStartTime) {
        return formatDate(this.lifecycle.lastStartTime, undefined, this.dateFormat);
      }
      return ' ';
    },
    lastStartTimeTitle() {
      return `${this.lastStartTime} ${getTimeZoneDiff()}`;
    },
    lastFinishedTime() {
      if (this.lifecycle.lastFinishedTime) {
        return formatDate(this.lifecycle.lastFinishedTime, undefined, this.dateFormat);
      }
      return ' ';
    },
    lastFinishedTimeTitle() {
      return `${this.lastFinishedTime} ${getTimeZoneDiff()}`;
    },
    canRunDiscovery() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.RunManualDiscovery);
    },
    canShowAdapterConnectionStatus() {
      return this.$can(this.$permissionConsts.categories.Adapters,
        this.$permissionConsts.actions.View);
    },
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    runFilter(filter, module) {
      if (!this.$canViewEntity(module)) return;
      this.updateView({
        module,
        view: {
          page: 0,
          query: {
            filter, expressions: [],
          },
        },
        selectedView: null,
      });
      this.$router.push({ path: module });
    },
    runFilterDevices(filter) {
      this.runFilter(filter, 'devices');
    },
    runFilterUsers(filter) {
      this.runFilter(filter, 'users');
    },
  },
};
</script>

<style lang="scss">
  .x-default-space {
    .chart-lifecycle {
      &.print-exclude{
        grid-column: 4;
        grid-row: 1;
      }
      display: flex;
      flex-direction: column;

      .cycle {
        flex: 100%;
      }
      .cycle-info {
        display: flex;
        flex-direction: row;
        font-size: 12px;

        .cycle-history {
          display: flex;
          flex-direction: column;
          width: 100%;

          .cycle-date {
            color: $theme-orange;
            font-weight: 300;
          }
        }

        .cycle-time {
          display: flex;
          flex-direction: column;
          text-align: right;
          width: 100%;
          align-items: flex-end;
          justify-content: flex-end;

          .cycle-next {
            display: flex;
            flex-direction: column;
            .cycle-next-time {
              color: $theme-orange;
              text-align: left;
              font-weight: 300;
            }
          }
        }
      }
    }
  }
</style>
