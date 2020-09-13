<template>
  <div
    :id="chart.uuid"
    :class="chartClass"
    :name="chart.name"
    class="x-chart draggable"
  >
    <div class="x-chart__main">
      <XChartHeader
        :title="chart.name"
        :filterable="search || history"
        :filters="chartFilters"
        :filter-layer-visible="filtersLayerVisible"
        class="main__header"
        @on-open-filters="filtersLayerVisible = !filtersLayerVisible"
      >
        <XChartActionsMenu
          v-if="!filtersLayerVisible"
          slot="actions-menu"
          :exportable="exportable"
          :trend="trend"
          :sortable="sortable"
          :sort="chartSort"
          :chart="chart"
          :permit-all-actions="isPersonalSpace"
          @export="exportChartCSV"
          @sort-changed="onSortChanged"
          @move-or-copy="moveOrCopyVisible = true"
          @edit="displayEditChartModal = true"
          @remove="onRemoveChart"
          @refresh="onRefreshChartData"
        />
      </XChartHeader>
      <XChartFilters
        v-if="filtersLayerVisible"
        :search="search"
        :history="history"
        :filters="chartFilters"
        @change="onFiltersChanged"
      />
      <XChartContent
        v-else
        :loading="chartData.loading"
        :error="chartData.error"
        :empty="isChartEmpty"
        @refresh="onRefreshChartData"
      >
        <!-- slot for data vizualiztion -->
        <slot
          :page-data="pageData"
          :data="chartData"
          :history="chartFilters.history"
        />
      </XChartContent>
      <XChartFooter
        v-if="!filtersLayerVisible"
        :pagination="pagination"
        :page="currentPage"
        :chart-data="chartData"
        :display-count="displayCount"
        :total-items-name="totalItemsName"
        :draggable="draggable && canDragCard"
        :legend="legend"
        :trend="trend"
        :trend-disabled="isTrendChartDisabled"
        :expanded="Boolean(expanded)"
        :format-count-label="formatCountLabel"
        :show-less="isChartEmpty || chartData.error"
        class="main__footer"
        @on-page-changed="onPageChanged"
        @open-drawer="onOpenDrawer"
        @close-drawer="expanded = false"
      />
      <XChartEditWizard
        v-if="displayEditChartModal"
        :panel="chart"
        :space="activeSpaceId"
        :edit-mode="true"
        @close="displayEditChartModal = false"
        @update="onChartUpdated"
      />
    </div>
    <div
      v-if="expanded"
      class="x-chart__expand"
    >
      <slot
        name="expand"
        :context="expanded"
        :data="chartData"
        :trend="trendChartData"
        :refresh-trend="() => fetchTrendChartData(true)"
        :history="chartFilters.history"
      />
    </div>
    <XMoveOrCopy
      v-if="moveOrCopyVisible"
      :current-panel="chart"
      :current-space="activeSpaceId"
      @close="moveOrCopyVisible = false"
      @moved="onChartMovedFromSpace"
      @duplicate="$emit('chart-duplicated', $event)"
    />
  </div>
</template>

<script>
import { mapActions, mapState, mapGetters } from 'vuex';
import dayjs from 'dayjs';
import _get from 'lodash/get';
import _isEqual from 'lodash/isEqual';
import { REMOVE_DASHBOARD_PANEL, FETCH_CHART_CSV, GET_SPACE_BY_ID } from '@store/modules/dashboard';
import { fetchChartData } from '@api/dashboard';
import XChartEditWizard from '@networks/dashboard/Wizard.vue';
import XMoveOrCopy from '@networks/dashboard/MoveOrCopy.vue';
import {
  ChartSortTypeEnum,
  ChartSortOrderEnum,
  SpaceTypesEnum,
} from '@constants/dashboard';
import { DiscoveryStatusEnum } from '@constants/discovery';
import XChartHeader from './ChartHeader.vue';
import XChartFooter from './ChartFooter.vue';
import XChartFilters from './ChartFilters.vue';
import XChartActionsMenu from './ChartActionsMenu.vue';
import XChartContent from './ChartContent.vue';


export default {
  name: 'XChart',
  components: {
    XChartHeader,
    XChartFooter,
    XChartFilters,
    XChartEditWizard,
    XChartActionsMenu,
    XChartContent,
    XMoveOrCopy,
  },
  props: {
    chart: {
      type: Object,
      required: true,
    },
    activeSpaceId: {
      type: String,
      required: true,
    },
    search: {
      type: Boolean,
      default: false,
    },
    history: {
      type: Boolean,
      default: false,
    },
    displayCount: {
      type: Boolean,
      default: false,
    },
    totalItemsName: {
      type: String,
      default: undefined,
    },
    pagination: {
      type: Boolean,
      default: false,
    },
    pageLimit: {
      type: Number,
      default: 5,
    },
    legend: {
      type: Boolean,
      default: false,
    },
    trend: {
      type: Boolean,
      default: false,
    },
    draggable: {
      type: Boolean,
      default: true,
    },
    exportable: {
      type: Boolean,
      default: false,
    },
    sortable: {
      type: Boolean,
      default: false,
    },
    isEmpty: {
      type: Function,
      default: undefined,
    },
    limit: {
      type: Number,
      default: 50,
    },
    formatCountLabel: {
      type: Function,
      default: undefined,
    },
  },
  data() {
    const defaultSortType = this.sortable ? _get(this.chart, 'config.sort.sort_by', ChartSortTypeEnum.name) : null;
    const defaultSortOrder = this.sortable ? _get(this.chart, 'config.sort.sort_order', ChartSortOrderEnum.asc) : null;
    return {
      displayEditChartModal: false,
      filtersLayerVisible: false,
      expanded: false,
      moveOrCopyVisible: false,
      currentPage: 1,
      chartFilters: { search: undefined, history: undefined },
      chartSort: {
        type: defaultSortType,
        order: defaultSortOrder,
      },
      chartData: {
        loading: true,
        content: [],
        count: 0,
        error: false,
      },
      trendChartData: {
        loading: true,
        content: [],
        error: false,
      },
    };
  },
  computed: {
    ...mapState({
      discoveryStatus(state) {
        return state.dashboard.lifecycle.data.status;
      },
    }),
    ...mapGetters({
      getSpaceById: GET_SPACE_BY_ID,
    }),
    isChartEmpty() {
      // some chart has their own specification of empy charts
      // for that reason we let them decied wheater the chart is empty, or not.
      const empty = this.isEmpty
        ? this.isEmpty(this.chartData.content)
        : !this.chartData.content.length;

      return !this.chartData.loading && empty;
    },
    pageData() {
      // pageData represent the segment of data
      // the user curenly observe. (mostly relevant in paginatio charts)
      if (this.chartData.loading) return [];
      if (!this.pagination) return this.chartData.content;
      const from = (this.currentPage - 1) * this.pageLimit;
      const to = from + this.pageLimit;
      const pageData = this.chartData.content.slice(from, to);
      return pageData;
    },
    chartClass() {
      return {
        'x-chart--expand-active': this.expanded,
        [`x-chart-${this.chart.uuid}`]: true,
      };
    },
    isTrendChartDisabled() {
      if (!this.chartFilters.history) {
        return '';
      }
      const historical = dayjs(this.chartFilters.history);
      const trendTimeframe = _get(this.chart, 'config.timeframe.count', 0);

      const firstDayOfTrend = dayjs().subtract(trendTimeframe, 'days');

      return historical.isBefore(firstDayOfTrend)
        ? `Timeline is limited to the last ${trendTimeframe} days`
        : '';
    },
    isPersonalSpace() {
      const activeSpace = this.getSpaceById(this.activeSpaceId);
      return activeSpace.type === SpaceTypesEnum.personal;
    },
    canDragCard() {
      return this.$can(this.$permissionConsts.categories.Spaces,
        this.$permissionConsts.actions.Update)
      || this.isPersonalSpace;
    },
  },
  watch: {
    chart(newChart, prevChart) {
      const { config } = newChart;
      const { config: prevConfig } = prevChart;

      if (!_isEqual(config, prevConfig)) {
        this.resetChartState();
      }
    },
    discoveryStatus: {
      handler: 'fetchDataWhenDiscoveryDone',
      immediate: true,
    },
  },
  created() {
    // we make the first call with blocking = true to ensure we wait for new chart's data
    this.fetchData({ blocking: true });
    if (this.trend) {
      this.fetchTrendChartData();
    }
  },
  methods: {
    ...mapActions({
      removeChart: REMOVE_DASHBOARD_PANEL,
      downloadAsCsv: FETCH_CHART_CSV,
    }),
    async fetchDataWhenDiscoveryDone(status, prevStatus) {
      if (status === DiscoveryStatusEnum.done && prevStatus === DiscoveryStatusEnum.running) {
        this.fetchData({ blocking: true });
      }
    },
    // header events callbacks
    onFiltersChanged(filters) {
      this.chartFilters = filters;
      this.filtersLayerVisible = false;
      this.currentPage = 1;
      this.fetchData();
    },
    // update chart data
    async fetchTrendChartData(refresh = undefined) {
      try {
        const trendChartId = this.chart.linked_dashboard;
        const { data, status } = await fetchChartData({ uuid: trendChartId, limit: 1000, refresh });
        if (status !== 200) {
          throw new Error();
        }
        this.trendChartData = {
          content: data.data,
          loading: false,
          error: false,
        };
      } catch (err) {
        this.trendChartData = {
          loading: false,
          content: [],
          error: true,
        };
      }
    },
    async fetchData(params = {}) {
      const {
        skip = (this.currentPage - 1) * this.pageLimit,
        refresh = false,
        blocking = false,
      } = params;

      // show loading indication
      this.chartData.loading = true;

      // defaults or action-menu selections
      const { type, order } = this.chartSort;
      try {
        const { data, status } = await fetchChartData({
          uuid: this.chart.uuid,
          spaceId: this.activeSpaceId,
          skip,
          limit: this.limit,
          historical: this.chartFilters.history,
          search: this.chartFilters.search,
          sortBy: type,
          sortOrder: order,
          refresh: refresh ? true : null,
          blocking: blocking ? true : null,
        });

        if (status !== 200) {
          throw new Error();
        }

        const {
          data: head, data_tail: tail, count,
        } = data;
        let chartData = {};
        if (this.pagination) {
          chartData = this.getPaginatedDataObject(head, tail, count, this.currentPage, this.chartData.content);
        } else {
          chartData = {
            content: [...head, ...tail],
            count,
            loading: false,
            error: false,
          };
        }
        this.chartData = chartData;
      } catch (err) {
        this.setContentError();
      }
    },
    getPaginatedDataObject(head, tail, count, page, content) {
      let dataContent;
      if (page === 1) {
        dataContent = new Array(count);
        dataContent.splice(0, head.length, ...head);

        if (Array.isArray(tail) && tail.length) {
          dataContent.splice(count - tail.length, tail.length, ...tail);
        }
      } else {
        dataContent = [...content];
        const from = (this.currentPage - 1) * this.pageLimit;
        dataContent.splice(from, head.length, ...head);
      }
      return {
        content: dataContent,
        count,
        loading: false,
        error: false,
      };
    },
    setContentError() {
      this.chartData = {
        content: [],
        count: 0,
        loading: false,
        error: true,
      };
    },
    resetChartState() {
      // reset filters
      this.chartFilters = { search: undefined, history: undefined };
      // reset sort
      const defaultSortType = this.sortable ? _get(this.chart, 'config.sort.sort_by', ChartSortTypeEnum.name) : null;
      const defaultSortOrder = this.sortable ? _get(this.chart, 'config.sort.sort_order', ChartSortOrderEnum.asc) : null;
      this.chartSort = {
        type: defaultSortType,
        order: defaultSortOrder,
      };
      // reset page
      this.currentPage = 1;
      // close expandable drawer
      this.expanded = false;
      // fetch data
      this.fetchData({ refresh: true });
      if (this.trend) {
        this.fetchTrendChartData(true);
      }
    },
    // actions-menu events callbacks
    exportChartCSV({ trend }) {
      const params = {
        uuid: trend ? this.chart.linked_dashboard : this.chart.uuid,
        historical: trend ? undefined : this.chartFilters.history,
        name: this.chart.name,
      };
      this.downloadAsCsv(params);
    },
    onSortChanged(sort) {
      this.chartSort = sort;
      this.currentPage = 1;
      this.fetchData();
    },
    onChartUpdated(data) {
      this.$emit('chart-changed', data);
    },
    onRemoveChart() {
      this.$safeguard.show({
        text: `
            This chart will be completely deleted from the system.
            Deleting the chart is an irreversible action.
            <br />
            Do you want to continue?
          `,
        confirmText: 'Delete Chart',
        onConfirm: async () => {
          await this.removeChart({
            panelId: this.chart.uuid,
            spaceId: this.activeSpaceId,
          });

          this.$emit('chart-removed', this.chart.uuid);
        },
      });
    },
    onRefreshChartData() {
      this.resetChartState();
    },
    // footer events callback
    onPageChanged(page) {
      const skip = (page - 1) * this.pageLimit;
      this.fetchData({ skip });
      this.currentPage = page;
    },
    onOpenDrawer(type) {
      this.expanded = type;
    },
    onChartMovedFromSpace(chartId) {
      this.$emit('chart-removed', chartId);
    },
  },
};
</script>

<style lang="scss">
  .x-chart {
    // size
    width: 100%;
    height: 100%;
    // layout
    position: relative;
    display: flex;
    flex-direction: row-reverse;
    overflow: hidden;
    //box model
    padding: 8px;
    border-radius: 2px;
    border: 2px solid transparent;
    //style
    background-color: $theme-white;
    box-shadow: 0 2px 12px 0 rgba(0,0,0,.2);

    &--expand-active {
      //chart layout growth
      grid-column: 1 / span 2;
      width: 100%;
      grid-column: span 2;
      .x-chart__main {
        width: 50%;
        padding-left: 8px;
      }
      .main__footer {
        .x-button.close-drawer {
          //re-positioning legend toggler
          position: relative;
          right: 345px;
        }
      }
    }

    .x-chart__expand {
      width: 50%;
      padding-right: 8px;
      border-right: 1px dashed $grey-3;
    }

    &.ghost {
      border: 3px dashed rgba($theme-blue, 0.4);
    }

    &__main, &__expand {
      // layout
      display: flex;
      width: 100%;
      height: 100%;
      flex-direction: column;

      .main__header {
        height: 10%;
      }
      .main__body {
        flex-grow: 1;
        display: flex;
        justify-content: center;

        &--loading {
          align-items: center;
        }
        &--empty {
          display: flex;
          align-items: center;
          flex-direction: column;
          align-items: center;
          p {
            font-size: 20px;
          }
        }

        &--error {
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          .x-icon {
            font-size: 45px;
            margin-bottom: 24px;
          }
          .x-button {
            margin-top: 24px;
          }
        }
      }

      .main__filters-layer {
        // layout
        display: flex;
        height: 100%;
        flex-direction: column;
        justify-content: flex-start;
        // positioning
        position: relative;
        .filter-item {
          margin-top: 16px;
        }
        .filters-actions {
          // layout
          display: flex;
          width: 100%;
          justify-content: space-evenly;
          // positioning
          position: absolute;
          bottom: 24px;
        }
      }
    }
  }
</style>
