<template>
  <div
    key="chart-lifecycle"
    class="x-dashboard-card chart-lifecycle print-exclude"
  >
    <div class="header">
      <h3
        class="chart-title"
        title="System Lifecycle"
      >System Lifecycle</h3>
    </div>


    <div class="body">
      <XCycle :data="lifecycle.subPhases || []" />
    </div>
    <div class="footer">
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
</template>

<script>
import { mapState, mapGetters } from 'vuex';
import { formatDate, getTimeZoneDiff } from '@constants/utils';
import XCycle from '@axons/charts/Cycle.vue';
import { DATE_FORMAT } from '@store/getters';

export default {
  name: 'XLifecycleChart',
  components: { XCycle },
  computed: {
    ...mapState({
      lifecycle(state) {
        return state.dashboard.lifecycle.data;
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
  },
};
</script>

<style lang="scss">
.chart-lifecycle {
  &.print-exclude{
    grid-row: 1;
  }
  display: flex;
  flex-direction: column;
  .body {
    display: flex;
  }
  &.chart-lifecycle .footer {
    height: 100px;
  }
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
</style>
