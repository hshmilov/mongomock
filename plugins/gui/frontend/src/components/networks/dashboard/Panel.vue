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
      <XCard
        class="card__item"
        :title="chart.name"
        :removable="!readOnly"
        :editable="!readOnly && chart.user_id !== '*'"
        :exportable="chart.metric==='segment'"
        :draggable="draggable"
        :is-chart-filterable="isChartFilterable"
        v-on="$listeners"
        @edit="editPanel"
        @refresh="fetchMorePanel(chart.uuid, 0, chart.historical, true)"
        @moveOrCopy="openMoveOrCopy"
        @toggleShowSearch="toggleShowSearch"
      >
        <div
          v-if="chart.metric !== 'timeline'"
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
        <Component
          :is="`x-${chart.view}`"
          v-if="!isChartEmpty(chart)"
          :data="chart.data"
          @click-one="(queryInd) => linkToQueryResults(queryInd, chart.historical)"
          @fetch="(skip) => fetchMorePanel(chart.uuid, skip, chart.historical)"
          @legend-data-modified="onlegendDataModified"
        />
        <div
          v-else-if="chart.loading"
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
        <div
          v-if="chart.view === 'pie'"
          class="footer"
        >
          <SvgIcon
            v-if="!isChartEmpty(chart)"
            class="toggle-legend"
            :name="showLegend ? 'action/toggle_light_dark' : 'action/toggle_dark_light'"
            width="16"
            :original="true"
            @click="showLegend = !showLegend"
          />
        </div>
      </XCard>
    </div>
  </div>
</template>

<script>
import {
  mapActions, mapGetters, mapMutations, mapState,
} from 'vuex';
import _debounce from 'lodash/debounce';
import _uniq from 'lodash/uniq';
import _merge from 'lodash/merge';
import { IS_ENTITY_RESTRICTED } from '../../../store/modules/auth';
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
  },
  props: {
    chart: {
      type: Object,
      default: () => {},
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
    draggable: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      filter: '',
      showLegend: false,
      showSearch: false,
      showHistory: false,
    };
  },
  computed: {
    ...mapState({
      allowedDates(state) {
        if (!this.chart.config) {
          return {};
        }
        if (this.chart.metric === 'compare') {
          const modules = this.chart.config.views.map((view) => view.entity);
          return _uniq(modules).reduce((acc, curr) => {
            _merge(acc, state.constants.allowedDates[curr]);
            return acc;
          }, {});
        }
        return state.constants.allowedDates[this.chart.config.entity];
      },
    }),
    ...mapGetters({
      isEntityRestricted: IS_ENTITY_RESTRICTED,
    }),
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
      return this.chart.view === 'histogram' && this.chart.metric === 'segment';
    },
  },
  mounted() {
    this.filter = this.chart.search || '';
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
      this.fetchDashboardPanel({
        uuid: chart.uuid,
        spaceId: this.currentSpace,
        skip: 0,
        limit: 100,
        historical: selectedDate,
        search: this.filter,
      });
    },
    linkToQueryResults(queryInd, historical) {
      const query = this.chart.data[queryInd];
      if (this.isEntityRestricted(query.module)
              || query.view === undefined
              || query.view === null
      ) {
        return;
      }
      this.updateView({
        module: query.module,
        view: historical ? {
          ...query.view,
          historical: this.allowedDates[historical],
        } : query.view,
        name: this.chart.metric === 'compare' ? query.name : undefined,
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
    fetchMorePanel(uuid, skip, historical, refresh) {
      this.fetchDashboardPanel({
        uuid,
        spaceId: this.currentSpace,
        skip,
        limit: 100,
        historical,
        search: this.filter,
        refresh,
      });
    },
    // eslint-disable-next-line func-names
    fetchFilteredPanel: _debounce(function () {
      this.fetchDashboardPanel({
        uuid: this.chart.uuid,
        spaceId: this.currentSpace,
        skip: 0,
        limit: 100,
        historical: this.chart.historical,
        search: this.filter,
      });
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

  .footer {
    padding: 0 12px;

    .toggle-legend {
      cursor: pointer;
    }
  }

  .card-container-outer {
    border: none;
    box-shadow: 0 2px 12px 0px rgba(0, 0, 0, 0.2);

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
</style>
