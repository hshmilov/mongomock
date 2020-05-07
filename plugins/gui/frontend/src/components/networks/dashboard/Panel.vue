<template>
  <div
    class="card-container-outer"
    :name="chart.name"
    :class="{ 'double-card': showLegend }"
    @mouseenter="showHistory = true"
    @mouseleave="showHistory = false"
  >
    <div class="card-container-inner">
      <XCard
        v-if="showLegend"
        class="legend"
      >
        <XChartLegend
          :data="legendData"
          @on-item-click="onLegendItemClick"
        />
      </XCard>
      <div
        class="x-card card__item"
        :class="{'custom-card': draggable}"
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
            :editable="canUserUpdatePanels && chart.user_id !== '*'"
            :sortable="isSortable(chart)"
            :has-drop-down-menu="draggable && canUserUpdatePanels"
            :is-chart-filterable="isChartFilterable"
            v-on="$listeners"
            @edit="editPanel"
            @toggleShowSearch="toggleShowSearch"
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
            v-if="chart.loading"
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
            :is="`x-${chart.view}`"
            v-else-if="!isChartEmpty(chart)"
            :data="chart.data"
            @click-one="(queryInd) => linkToQueryResults(queryInd, chart.historical)"
            @fetch="(skip) => fetchChartData(chart.uuid, skip, chart.historical)"
            @legend-data-modified="onlegendDataModified"
          />
          <div
            v-else
            class="no-data-found"
          >
            <SvgIcon
              name="illustration/binocular"
              :original="true"
              height="50"
            />
            <div>No data found</div>
          </div>

        </div>

        <div class="footer">
          <div
            v-if="chart.view === 'pie' && !isChartEmpty(chart)"
            class="toggle-legend"
            @click="showLegend = !showLegend"
          >
            <VIcon
              size="16"
              @mouseover="toggleIconHover = true"
              @mouseout="toggleIconHover = false"
            >{{ `$vuetify.icon.${legendIcon}` }}
            </VIcon>
          </div>
          <div
            v-if="draggable"
            class="drag-handle"
          >
            <VIcon size="15">
              $vuetify.icons.cardDraggable
            </VIcon>
          </div>
        </div>
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
import { FETCH_DASHBOARD_PANEL } from '../../../store/modules/dashboard';
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
import {
  ChartTypesEnum, ChartViewEnum,
} from '../../../constants/dashboard';

export default {
  name: 'XPanel',
  components: {
    XCard,
    XHistoricalDate,
    XHistogram,
    XPie,
    XSummary,
    XLine,
    XSearchInput,
    XChartLegend,
    PanelActions,
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
  },
  data() {
    return {
      filter: '',
      showLegend: false,
      showSearch: false,
      showHistory: false,
      toggleIconHover: false,
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
    }),
    canUserUpdatePanels() {
      return this.$can(this.$permissionConsts.categories.Dashboard,
        this.$permissionConsts.actions.Update,
        this.$permissionConsts.categories.Charts);
    },
    headerClass() {
      return {
        'x-card-header': true,
        hidden: false,
        // hidden: !this.headerVisible,
      };
    },
    headerVisible() {
      return this.isChartFilterable() || this.dataFilter || this.chart.historical;
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
        } : query.view,
        name: this.chart.metric === ChartTypesEnum.compare ? query.name : undefined,
        uuid: null,
      });
      this.$router.push({ path: query.module });
    },
    isChartEmpty() {
      return (!this.chart.data
              || (this.chart.data.length === 0)
              || (this.chart.data.length === 1 && this.chart.data[0].value === 0)
      );
    },
    fetchChartData(uuid, skip, historical, refresh, search) {
      return this.fetchDashboardPanel({
        uuid,
        spaceId: this.currentSpace,
        skip,
        limit: 100,
        historical,
        search: search || this.filter,
        refresh,
      });
    },
    // eslint-disable-next-line func-names
    fetchFilteredPanel: _debounce(function () {
      this.fetchChartData(this.chart.uuid, 0, this.chart.historical, true, this.filter);
    }, 300),
    editPanel() {
      this.filter = '';
      this.showLegend = false;
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
      return (chart.metric === ChartTypesEnum.segment || chart.metric === ChartTypesEnum.compare)
              && chart.view === ChartViewEnum.histogram;
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
    width: 36px;
    margin: 0 auto;
    display: block;
    padding: 4px;
    cursor: move;
    :hover g {
      fill: #949494;
    }
  }

  .toggle-legend {
    padding: 4px;
    cursor: pointer;
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
    .footer {
      width: 100%;
      display: flex;
      margin: -2px;
    }
  }

</style>
