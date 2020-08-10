<template>
  <div
    class="card-container-outer"
    :name="chart.name"
    :class="{ 'double-card': !!attachedCardData }"
    @mouseenter="showHistory = true"
    @mouseleave="showHistory = false"
  >
    <div class="card-container-inner">
      <XCard
        v-if="attachedCardData"
        :class="attachedCardData.cardClass"
      >
        <Component
          :is="attachedCardData.component"
          v-if="attachedCardData.data.length"
          :data="attachedCardData.data"
          @on-item-click="onLegendItemClick"
        />
        <div
          v-else
          class="no-data-found"
        >
          <XIcon
            family="illustration"
            type="binocular"
          />
          <div>No data found</div>
        </div>
      </XCard>
      <div
        class="x-card card__item"
        :class="{'custom-card': canBeDragged}"
      >

        <div class="header">
          <div class="header__title">
            <div
              class="card-title"
              :title="chart.name"
            >{{ chart.name }}</div>
          </div>
          <PanelActions
            :chart="chart"
            :sortable="isSortable(chart)"
            :is-chart-filterable="isChartFilterable"
            :ignore-permissions="ignorePermissions"
            :current-search-filter="filter"
            v-on="$listeners"
            @edit="editPanel"
            @toggleShowSearch="toggleShowSearch"
            @menu-clicked="menuClicked"
          />

        </div>

        <div class="body">
          <div
            v-if="chart.metric !== ChartTypesEnum.timeline"
            class="card-history"
          >
            <div class="x-card-header">
              <XHistoricalDate
                :value="chart.historical"
                :allowed-dates="allowedDates"
                :class="{hidden: !showHistory && !chart.historical}"
                @input="(selectedDate) => confirmPickDate(chart, selectedDate)"
              />
              <XSearchInput
                v-if="isChartFilterable && showSearch"
                v-model="dataFilter"
                :auto-focus="false"
              />

            </div>
          </div>
          <div
            v-if="showLoading"
            class="chart-spinner"
          >
            <MdProgressSpinner
              class="progress-spinner"
              md-mode="indeterminate"
              :md-stroke="3"
              :md-diameter="25"
            />
            <span>Fetching data...</span>
          </div>
          <Component
            :is="chartView"
            v-if="chart.view && !isChartEmpty(chart)"
            v-show="!showLoading"
            :data="chart.data"
            @click-one="(queryInd) => linkToQueryResults(queryInd, chart.historical)"
            @fetch="(skip) => fetchChartData(chart.uuid, skip, chart.historical)"
            @legend-data-modified="onlegendDataModified"
          />
          <div
            v-if="isTimelinePartialData"
            class="chart-warning"
          >
            <XIcon
              family="symbol"
              type="warning"
              :style="{fontSize: '20px'}"
            />
            <div class="chart-warning__text">
              Timeline charts may be showing partial data since historical snapshots are disabled.
            </div>
          </div>
          <div
            v-if="chartDataNotFound"
            class="no-data-found"
          >
            <XIcon
              family="illustration"
              type="binocular"
            />
            <div>No data found</div>
          </div>
        </div>
        <div class="footer">
          <div class="toggle-container">
            <div
              v-if="showTrendToggle && !isChartEmpty(chart) && chart.linkedData"
              class="toggle toggle-trend"
              :class="{'trend-toggle-disabled': trendDisabled}"
              :title="trendToggleTooltip"
              @click="toggleTrend"
            >
              <XIcon
                family="symbol"
                type="trend"
                :style="{fontSize: '16px'}"
              />
            </div>
            <div
              v-if="chart.view === 'pie' && !isChartEmpty(chart)"
              class="toggle toggle-legend"
              @click="toggleLegend"
            >
              <VIcon
                size="16"
                @mouseover="toggleIconHover = true"
                @mouseout="toggleIconHover = false"
              >{{ `$vuetify.icon.${legendIcon}` }}
              </VIcon>
            </div>
          </div>
          <div
            v-if="canBeDragged"
            class="drag-handle"
          >
            <VIcon size="15">
              $vuetify.icons.cardDraggable
            </VIcon>
          </div>
        </div>
        <div class="right-padding" />
      </div>
    </div>
  </div>
</template>

<script>
import {
  mapActions, mapMutations, mapState,
} from 'vuex';
import _debounce from 'lodash/debounce';
import _uniq from 'lodash/uniq';
import _merge from 'lodash/merge';
import _isNil from 'lodash/isNil';
import _findIndex from 'lodash/findIndex';
import _get from 'lodash/get';
import XIcon from '@axons/icons/Icon';
import { FETCH_DASHBOARD_PANEL, FETCH_SEGMENT_TIMELINE } from '../../../store/modules/dashboard';
import { UPDATE_DATA_VIEW } from '../../../store/mutations';
import XCard from '../../axons/layout/Card.vue';
import XHistoricalDate from '../../neurons/inputs/HistoricalDate.vue';
import XHistogram from '../../axons/charts/Histogram.vue';
import XPie from '../../axons/charts/Pie.vue';
import XSummary from '../../axons/charts/Summary.vue';
import XLine from '../../axons/charts/Line.vue';
import XSearchInput from '../../neurons/inputs/SearchInput.vue';
import XChartLegend from '../../axons/charts/ChartLegend.vue';
import PanelActions from './PanelActions.vue';
import XStacked from '../../axons/charts/Stacked.vue';
import XAdapterHistogram from '../../axons/charts/AdapterHistogram.vue';
import {
  ChartTypesEnum, ChartViewEnum, ChartComponentByViewEnum,
} from '../../../constants/dashboard';

export default {
  name: 'XPanel',
  components: {
    XCard,
    XHistoricalDate,
    XHistogram,
    XAdapterHistogram,
    XPie,
    XSummary,
    XLine,
    XSearchInput,
    XChartLegend,
    PanelActions,
    XStacked,
    XIcon,
  },
  props: {
    chart: {
      type: Object,
      default: () => {},
    },
    draggable: {
      type: Boolean,
      default: false,
    },
    currentSpace: {
      type: String,
      default: null,
    },
    ignorePermissions: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      filter: '',
      showLegend: false,
      showTrend: false,
      showSearch: false,
      showHistory: false,
      toggleIconHover: false,
      chartDataFull: false,
      chartDataFullFetching: false,
    };
  },
  computed: {
    ...mapState({
      allowedDates(state) {
        if (!this.chart.config) {
          return {};
        }
        if (this.chart.metric === ChartTypesEnum.compare) {
          const modules = this.chart.config.views.map((view) => view.entity);
          return _uniq(modules).reduce((acc, curr) => {
            _merge(acc, state.constants.allowedDates[curr]);
            return acc;
          }, {});
        }
        return state.constants.allowedDates[this.chart.config.entity];
      },
      historyEnabled(state) {
        return _get(state, 'configuration.data.global.historyEnabled', false);
      },
    }),
    chartDataNotFound() {
      return this.isChartEmpty(this.chart) && !this.chart.loading;
    },
    dataFilter: {
      get() {
        return this.filter;
      },
      set(filter) {
        this.filter = filter;
        this.fetchFilteredPanel();
      },
    },
    isChartFilterable() {
      return this.chart.view === ChartViewEnum.histogram
              && this.chart.metric === ChartTypesEnum.segment;
    },
    legendIcon() {
      return `legend${this.showLegend ? 'Open' : 'Closed'}${this.toggleIconHover ? 'Darker' : ''}`;
    },
    showLoading() {
      return this.chart.loading
        || (!this.isChartEmpty() && (this.chart.linked_dashboard && !this.chart.linkedData));
    },
    isTimelinePartialData() {
      return this.chart.metric === ChartTypesEnum.timeline && !this.historyEnabled;
    },
    chartView() {
      return ChartComponentByViewEnum[this.chart.view];
    },
    showTrendToggle() {
      return _get(this.chart, 'config.show_timeline');
    },
    trendDisabled() {
      if (!this.showTrendToggle || !this.chart.historical) {
        return false;
      }
      const selectedDate = new Date(this.chart.historical).getTime();
      const timeframeDate = this.getPastDateFromTimeframe();

      const isDisabled = selectedDate < timeframeDate;
      if (isDisabled) {
        // eslint-disable-next-line vue/no-side-effects-in-computed-properties
        this.showTrend = false;
      }
      return isDisabled;
    },
    trendToggleTooltip() {
      if (this.trendDisabled) {
        return `Timeline is limited to the last ${this.chart.config.timeframe.count} days`;
      }
      return '';
    },
    attachedCardData() {
      if (this.showLegend) {
        return {
          cardClass: 'legend',
          component: 'XChartLegend',
          data: this.chart.data,
        };
      }
      if (this.showTrend) {
        return {
          cardClass: 'trend',
          component: 'XLine',
          data: this.chart.linkedData,
        };
      }
      return null;
    },
    canBeDragged() {
      return (
        this.ignorePermissions
        || this.$can(this.$permissionConsts.categories.Dashboard,
          this.$permissionConsts.actions.Update,
          this.$permissionConsts.categories.Charts)
      )
          && this.draggable;
    },
  },
  mounted() {
    this.filter = this.chart.search || '';
  },
  created() {
    this.ChartTypesEnum = ChartTypesEnum;
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
      moveOrCopyToggle: 'moveOrCopyToggle',
    }),
    ...mapActions({
      fetchDashboardPanel: FETCH_DASHBOARD_PANEL,
      fetchSegmentTimeline: FETCH_SEGMENT_TIMELINE,
    }),
    confirmPickDate(chart, selectedDate) {
      if (selectedDate === chart.historical) {
        return;
      }
      this.fetchChartData(chart.uuid, 0, selectedDate, true, this.filter);
    },
    linkToQueryResults(queryInd, historical) {
      const query = this.chart.data[queryInd];
      if (!this.$canViewEntity(query.module) || _isNil(query.view)) {
        return;
      }
      this.updateView({
        module: query.module,
        view: historical ? {
          ...query.view,
          historical: this.allowedDates[historical],
        } : { ...query.view },
        selectedView: { uuid: query.view_id },
      });
      this.$router.push({ path: query.module });
    },
    isChartEmpty() {
      const isChartEmptyBase = (!this.chart.data
              || (this.chart.data.length === 0)
              || (this.chart.data.length === 1 && this.chart.data[0].value === 0));
      // in case the chart metric is timeline,
      // all data must be obtained before rendering the component
      // while we keeping the loader on by return true
      if (this.chart.metric === ChartTypesEnum.timeline) {
        if (!this.allDataExist()) {
          // fetch all the data only once
          if (!this.chartDataFullFetching) {
            const nextIndex = _findIndex(this.chart.data, (row) => !row);
            this.fetchAllChartData(this.chart.uuid, nextIndex);
          }
          return !this.chartDataFull;
        }
      }
      return isChartEmptyBase;
    },
    fetchChartData(uuid, skip, historical, refresh, search) {
      const sortBy = _get(this.chart, 'selectedSort.sortBy') || _get(this.chart, 'config.sort.sort_by');
      const sortOrder = _get(this.chart, 'selectedSort.sortOrder') || _get(this.chart, 'config.sort.sort_order');
      return this.fetchDashboardPanel({
        uuid,
        spaceId: this.currentSpace,
        skip,
        limit: 100,
        historical,
        search: search || this.filter,
        refresh,
        sortBy,
        sortOrder,
      });
    },
    async fetchAllChartData(uuid, skip) {
      this.chartDataFullFetching = true;
      const promises = [];
      // create list of all the request needed to get all the data
      // considering the starting skip and a limit of 100
      const totalRequests = Math.ceil(this.chart.data.length / 100);
      for (let i = 0; i < totalRequests; i += 1) {
        const currentSkip = skip + (i * 100);
        promises.push(this.fetchDashboardPanel({
          uuid,
          spaceId: this.currentSpace,
          skip: currentSkip,
          limit: 100,
          historical: this.chart.historical,
        }));
      }
      // wait for all the requests to return
      await Promise.all(promises);
      this.setAllChartDataFull();
    },
    setAllChartDataFull() {
      if (this.allDataExist()) {
        this.chartDataFull = true;
      } else {
        // if one of the request failed, no data will appear
        this.chart.data = [];
      }
    },
    allDataExist() {
      return !this.chart.data.includes(undefined);
    },
    // eslint-disable-next-line func-names
    fetchFilteredPanel: _debounce(function () {
      this.fetchChartData(this.chart.uuid, 0, this.chart.historical, false, this.filter);
    }, 300),
    editPanel() {
      this.filter = '';
      this.showLegend = false;
      this.showTrend = false;
    },
    onlegendDataModified(legendData) {
      this.legendData = legendData;
    },
    onLegendItemClick(itemIndex) {
      this.linkToQueryResults(itemIndex, this.chart.historical);
    },
    openMoveOrCopy() {
      this.moveOrCopyToggle({
        active: true,
        currentPanel: this.chart,
      });
    },
    toggleShowSearch() {
      this.showSearch = !this.showSearch;
    },
    isSortable(chart) {
      return (((chart.metric === ChartTypesEnum.segment || chart.metric === ChartTypesEnum.compare)
              && chart.view === ChartViewEnum.histogram)
              || chart.view === ChartViewEnum.stacked
              || chart.view === ChartViewEnum.adapter_histogram);
    },
    menuClicked() {
      this.showTrend = false;
    },
    toggleLegend() {
      if (this.showTrend) {
        this.showTrend = false;
      }
      this.showLegend = !this.showLegend;
    },
    toggleTrend() {
      if (this.trendDisabled) {
        return;
      }
      if (this.showLegend) {
        this.showLegend = false;
      }
      this.showTrend = !this.showTrend;
    },
    getPastDateFromTimeframe() {
      return Date.now() - this.chart.config.timeframe.count * 1000 * 60 * 60 * 24;
    },
  },
};
</script>

<style lang="scss">
  .x-card-header {
    display: flex;
    .hidden {
      display: none;
    }
    > div {
      height: 30px;
      width: 158px;
      &.x-historical-date {
        margin-right: 5px;
      }
    }
  }

  .drag-handle {
    margin: 0 auto;
    display: block;
    padding: 4px;
    cursor: move;
    :hover g {
      fill: #949494;
    }
  }

  .toggle-container {
    display: flex;

    .toggle {
      cursor: pointer;
    }

    .toggle-legend {
      padding: 4px;
    }

    .toggle-trend {
      margin: 6px 0 0 10px;

      i {
        font-size: 20px !important;
      }

      &.trend-toggle-disabled {
        cursor: auto;
        color: rgba(0, 0, 0, .25);
      }

      &:not(.trend-toggle-disabled) {
        path {
          fill: #0076FF;
        }

        &:hover {
          path {
            fill: #2994ff;
          }
        }
      }
    }
  }

  .right-padding {
    flex: 1;
  }

  .card-container-outer {
    border: none;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.2);

    .card-container-inner {
      height: 100%;

      .x-card {
        height: 100%;
        box-shadow: none;
      }
    }

    &.double-card {
      grid-column: span 2;
      background-color: white;
      .card-container-inner {
        height: 100%;
        display: flex;

        .x-card {
          width: 50%;
          display: flex;
          justify-content: space-between;

          .card__item .header:hover {
            border: none;
          }

          &.legend {
            height: auto;
          }

          &:not(.legend) {
            border-width: 0 0 0 1px;
            border-style: solid;
            border-color: $grey-2;
          }
        }
      }
    }
  }

  .x-card-header {
    display: flex;
    &.hidden {
      display: none;
    }
    > div {
      height: 30px;
      width: 158px;
      &.x-historical-date {
        margin-right: 5px;
      }
    }
  }

  .x-panels {
    .body {
      .no-data-found > .x-icon {
        font-size: 50px;
      }
    }
    .footer {
      display: grid;
      grid-template-columns: 20% auto 20%;
      margin: -2px;
    }
  }

  .chart-warning {
    display: flex;
    align-items: center;
    margin-top: 8px;

    &__text {
      margin-left: 8px;
      line-height: 18px;
    }
  }

</style>
