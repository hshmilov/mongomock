<template>
  <XFeedbackModal
    :launch="true"
    :handle-save="saveNewDashboard"
    :disabled="isDisabled"
    :note="note"
    approve-id="chart_save"
    @change="finishNewDashboard"
  >
    <h3 v-if="editMode">
      Edit Dashboard Chart - "{{ panel.data.name }}"
    </h3>
    <h3 v-else>
      Create a Dashboard Chart
    </h3>
    <div class="x-chart-wizard">
      <!-- Last name to appear as a title above the chart -->
      <label
        class="chart-metric"
        for="chart_name"
      >Chart title</label>
      <input
        id="chart_name"
        v-model="dashboard.name"
        type="text"
      >
      <!-- Select metric to be tested by chart -->
      <label class="chart-metric">Chart metric</label>
      <XSelect
        id="metric"
        :value="dashboard.metric"
        :options="metricOptions"
        placeholder="by..."
        @input="updateMetric"
      />
      <!-- Select method of presenting the data of the chart -->
      <template v-if="dashboard.metric">
        <label>Chart presentation</label>
        <div class="dashboard-view">
          <template v-for="view in availableViews">
            <input
              :id="view"
              :key="view"
              v-model="dashboardView"
              type="radio"
              :value="view"
            >
            <label
              :key="`label_${view}`"
              :for="view"
              class="type-label"
            >
              <SvgIcon
                :name="`symbol/${view}`"
                :original="true"
                height="24"
              />
            </label>
          </template>
        </div>
        <Component
          :is="dashboard.metric"
          ref="dashboardRef"
          v-model="dashboard.config"
          :entities="entityOptions"
          :view-options="viewSelectOptionsGetter(!isPersonalDashboardSpaceId)"
          :chart-view="dashboard.view"
          class="grid-span2"
          @validate="configValid = $event"
        />
      </template>
      <div
        v-if="message"
        class="grid-span2 error-text"
      >
        {{ message }}
      </div>
    </div>
  </XFeedbackModal>
</template>

<script>
import { mapActions, mapGetters, mapState } from 'vuex';
import { formatDate } from '@constants/utils';
import XFeedbackModal from '../../neurons/popover/FeedbackModal.vue';
import XSelect from '../../axons/inputs/select/Select.vue';

import intersect from './charts/Intersect.vue';
import compare from './charts/Compare.vue';
import segment from './charts/Segment.vue';
import abstract from './charts/Abstract.vue';
import timeline from './charts/Timeline.vue';
import matrix from './charts/Matrix.vue';

import viewsMixin from '../../../mixins/views';

import { SAVE_DASHBOARD_PANEL, CHANGE_DASHBOARD_PANEL } from '../../../store/modules/dashboard';
import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '../../../store/modules/onboarding';
import { DASHBOARD_CREATED } from '../../../constants/getting-started';
import { LAZY_FETCH_DATA_FIELDS } from '../../../store/actions';
import { DATE_FORMAT } from '../../../store/getters';
import { ChartViewEnum, ChartTypesEnum, SpaceTypesEnum } from '../../../constants/dashboard';


const dashboard = {
  metric: '', view: '', name: '', config: null,
};
export default {
  name: 'XChartWizard',
  components: {
    XFeedbackModal, XSelect, intersect, compare, segment, abstract, timeline, matrix,
  },
  mixins: [viewsMixin],
  props: {
    space: {
      type: String,
      required: true,
    },
    panel: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      dashboard: { ...dashboard },
      configValid: false,
    };
  },
  computed: {
    ...mapState({
      isPersonalDashboardSpaceId(state) {
        return state.dashboard.spaces.data
          .find((space) => space.type === SpaceTypesEnum.personal).uuid === this.space;
      },
    }),
    ...mapGetters({
      dateFormat: DATE_FORMAT,
    }),
    dashboardView: {
      get() {
        return this.dashboard.view;
      },
      set(value) {
        this.dashboard.view = value;
      },
    },
    editMode() {
      return this.panel !== undefined && this.panel !== null && this.panel.data !== undefined;
    },
    metricOptions() {
      return [
        { name: ChartTypesEnum.intersect, title: 'Query Intersection' },
        { name: ChartTypesEnum.compare, title: 'Query Comparison' },
        { name: ChartTypesEnum.segment, title: 'Field Segmentation' },
        { name: ChartTypesEnum.abstract, title: 'Field Summary' },
        { name: ChartTypesEnum.timeline, title: 'Query Timeline' },
        { name: ChartTypesEnum.matrix, title: 'Matrix Data' },
      ];
    },
    availableViews() {
      if (
        this.dashboard.metric === ChartTypesEnum.compare
        || this.dashboard.metric === ChartTypesEnum.segment
      ) {
        return [ChartViewEnum.histogram, ChartViewEnum.pie];
      }
      if (this.dashboard.metric === ChartTypesEnum.intersect) {
        return [ChartViewEnum.pie];
      }
      if (this.dashboard.metric === ChartTypesEnum.timeline) {
        return [ChartViewEnum.line];
      }
      if (this.dashboard.metric === ChartTypesEnum.matrix) {
        return [ChartViewEnum.stacked];
      }
      return [ChartViewEnum.summary];
    },
    isDisabled() {
      return (
        !this.dashboard.name
        || !this.dashboard.metric
        || !this.dashboardView
        || !this.configValid
      );
    },
    message() {
      if (!this.isDisabled) return '';
      return 'Missing required configuration';
    },
    note() {
      if (!this.dashboard.updated) return '';
      return `Last edited on ${formatDate(this.dashboard.updated, undefined, this.dateFormat)}`;
    },
  },
  async created() {
    this.entityOptions.forEach((entity) => this.fetchDataFields({ module: entity.name }));
    if (this.editMode) {
      this.dashboard = { ...this.panel.data };
      this.configValid = true;
    }
  },
  methods: {
    ...mapActions({
      saveDashboard: SAVE_DASHBOARD_PANEL,
      changeDashboard: CHANGE_DASHBOARD_PANEL,
      completeMilestone: SET_GETTING_STARTED_MILESTONE_COMPLETION,
      fetchDataFields: LAZY_FETCH_DATA_FIELDS,
    }),
    updateMetric(metric) {
      if (this.dashboard.metric === metric) return;
      this.dashboard.metric = metric;
      this.dashboard.config = null;
      this.configValid = false;
      this.$nextTick(() => {
        if (!this.availableViews.includes(this.dashboardView)) {
          [this.dashboardView] = this.availableViews;
        }
      });
    },
    saveNewDashboard() {
      if (this.panel && this.panel.uuid) {
        this.$emit('update', this.panel.uuid);
        return this.changeDashboard({
          panelId: this.panel.uuid,
          spaceId: this.space,
          data: this.dashboard,
        });
      }
      return this.saveDashboard({
        data: this.dashboard,
        space: this.space,
      }).then((res) => {
        // complete milestone here
        this.completeMilestone({ milestoneName: DASHBOARD_CREATED });
      });
    },
    finishNewDashboard() {
      this.$emit('close');
    },
  },
};
</script>

<style lang="scss">
.x-chart-wizard {
  display: grid;
  grid-template-columns: 160px auto;
  grid-gap: 16px 8px;

  #chart_name {
    height: 30px;
  }

  .chart-metric {
    align-self: center;
  }

  .dashboard-view {
    display: flex;
    align-items: center;

    .type-label {
      cursor: pointer;
      margin-right: 24px;
      margin-bottom: 0;

      .svg-icon {
        margin-left: 8px;

        .svg-fill {
          fill: $grey-4;
        }


        .svg-stroke {
          stroke: $grey-4;
        }
      }

      &:hover {
        .svg-fill {
          fill: $theme-black;
        }
      }
    }

    input {
      cursor: pointer;
    }
  }

  .x-chart-metric {
    display: grid;
    grid-template-columns: 160px auto 20px;
    grid-gap: 16px 8px;
    min-width: 0;
    align-items: flex-start;
  }

  .ant-btn-link {
    margin: auto;
  }

  .sort-radio-group {
     label {
       font-size: 14px;
     }
  }

  .sort-view {
    display: flex;
    align-items: center;

    .type-label {
      cursor: pointer;
      margin-right: 30px;
      margin-bottom: 0;
    }

    input {
      cursor: pointer;
    }
  }

  .sort-label {
    align-self: flex-start
  }

  .sort-radio {
    white-space:nowrap;
  }

  .sort-col {
    padding-top: 0px;
    max-width: 145px;
  }
}
</style>
