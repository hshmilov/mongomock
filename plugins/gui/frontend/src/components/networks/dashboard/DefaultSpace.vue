<template>
  <x-panels
    :panels="panels"
    :panelsOrder="panelsOrder"
    new-id="dashboard_wizard"
    class="x-default-space"
    @add="$emit('add')"
    @edit="$emit('edit', $event)"
  >
    <template slot="pre">
      <x-data-discovery-card
        :key="1"
        class="device-discovery"
        :data="discoveryData.devices.data"
        name="Device"
        @filter="runFilterDevices"
      />
      <x-data-discovery-card
        :key="2"
        class="user-discovery"
        :data="discoveryData.users.data"
        name="User"
        @filter="runFilterUsers"
      />
    </template>
    <x-card
      :key="3"
      slot="post"
      title="System Lifecycle"
      class="chart-lifecycle print-exclude"
    >
      <x-cycle :data="lifecycle.subPhases" />
      <div class="cycle-info">
        <div class="cycle-history">
          <div>Last cycle started at:</div>
          <div class="cycle-date">{{ lastStartTime }}</div>
          <div>Last cycle completed at:</div>
          <div class="cycle-date">{{ lastFinishedTime }}</div>
        </div>
        <div class="cycle-time">
          <div class="cycle-next">
            <div>Next cycle starts in:</div>
            <div class="cycle-next-time blue">{{ nextRunTime }}</div>
          </div>
        </div>
      </div>
    </x-card>
  </x-panels>
</template>

<script>
    import xPanels from './Panels.vue'
    import xDataDiscoveryCard from '../../neurons/cards/DataDiscoveryCard.vue'
    import xCard from '../../axons/layout/Card.vue'
    import xCycle from '../../axons/charts/Cycle.vue'

    import {mapState, mapGetters, mapMutations, mapActions} from 'vuex'
    import {IS_ENTITY_RESTRICTED} from '../../../store/modules/auth'
    import {UPDATE_DATA_VIEW} from '../../../store/mutations'
    import {formatDate} from '../../../constants/utils'

    export default {
    name: 'XDefaultSpace',
    components: {
      xPanels, xDataDiscoveryCard, xCard, xCycle
    },
    props: {
      panels: {
        type: Array,
        required: true
      },
      panelsOrder: {
        type: Array,
      }
    },
    computed: {
      ...mapState({
        discoveryData (state) {
          return state.dashboard.dataDiscovery
        },
        lifecycle (state) {
          return state.dashboard.lifecycle.data || {}
        }
      }),
      ...mapGetters({
        isEntityRestricted: IS_ENTITY_RESTRICTED
      }),
      nextRunTime () {
        let leftToRun = new Date(parseInt(this.lifecycle.nextRunTime) * 1000) - Date.now()
        let thresholds = [1000, 60 * 1000, 60 * 60 * 1000, 24 * 60 * 60 * 1000]
        let units = ['seconds', 'minutes', 'hours', 'days']
        for (let i = 1; i < thresholds.length; i++) {
          if (leftToRun < thresholds[i]) {
            return `${Math.round(leftToRun / thresholds[i - 1])} ${units[i - 1]}`
          }
        }
        return `${Math.round(leftToRun / thresholds[thresholds.length - 1])} ${units[units.length - 1]}`
      },
      lastStartTime () {
        if(this.lifecycle.lastStartTime) {
          return formatDate(this.lifecycle.lastStartTime);
        }
        return ' ';
      },
      lastFinishedTime () {
        if(this.lifecycle.lastFinishedTime) {
          return formatDate(this.lifecycle.lastFinishedTime);
        }
        return ' ';
      }
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW
      }),
      runFilter (filter, module) {
        if (this.isEntityRestricted(module)) return
        this.updateView({
          module,
          view: {
            page: 0,
            query: {
              filter, expressions: []
            }
          },
          uuid: null
        })
        this.$router.push({ path: module })
      },
      runFilterDevices (filter) {
        this.runFilter(filter, 'devices')
      },
      runFilterUsers (filter) {
        this.runFilter(filter, 'users')
      }
    }
  }
</script>

<style lang="scss">
  .x-default-space {
    .chart-lifecycle {
      &.print-exclude{
        grid-column: 3;
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
            color: $theme-blue;
            white-space: pre;
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
              text-align: left;
            }
          }
        }
      }
    }
  }
</style>