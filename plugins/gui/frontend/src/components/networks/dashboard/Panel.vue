<template>
  <x-card
    class="card__item"
    :title="chart.name"
    :removable="!readOnly && hovered"
    :editable="!readOnly && hovered && chart.user_id !== '*'"
    :exportable="chart.metric==='segment' && hovered"
    v-on="$listeners"
    @edit="editPanel"
  >
    <div
      v-if="chart.metric !== 'timeline'"
      class="card-history"
    >
      <div
        :class="headerClass"
      >
        <x-search-input
          v-if="isChartFilterable"
          v-model="dataFilter"
          :auto-focus="false"
        />
        <x-historical-date
          :value="chart.historical"
          @input="(selectedDate) => confirmPickDate(chart, selectedDate)"
        />
      </div>
    </div>
    <component
      :is="`x-${chart.view}`"
      v-if="!isChartEmpty(chart)"
      :data="chart.data"
      @click-one="(queryInd) => linkToQueryResults(queryInd, chart.historical)"
      @fetch="(skip) => fetchMorePanel(chart.uuid, skip, chart.historical)"
    />
    <div
      v-else-if="chart.loading"
      class="chart-spinner"
    >
      <md-progress-spinner
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
      <svg-icon
        name="illustration/binocular"
        :original="true"
        height="50"
      />
      <div>No data found</div>
    </div>
  </x-card>
</template>

<script>
import { mapActions, mapGetters, mapMutations } from 'vuex';
import _debounce from 'lodash/debounce';
import { IS_ENTITY_RESTRICTED } from '../../../store/modules/auth';
import { FETCH_DASHBOARD_PANEL } from '../../../store/modules/dashboard';
import { UPDATE_DATA_VIEW } from '../../../store/mutations';
import xCard from '../../axons/layout/Card.vue';
import xHistoricalDate from '../../neurons/inputs/HistoricalDate.vue';
import xHistogram from '../../axons/charts/Histogram.vue';
import xPie from '../../axons/charts/Pie.vue';
import xSummary from '../../axons/charts/Summary.vue';
import xLine from '../../axons/charts/Line.vue';
import xSearchInput from '../../neurons/inputs/SearchInput.vue';

export default {
  name: 'XPanel',
  components: {
    xCard, xHistoricalDate, xHistogram, xPie, xSummary, xLine, xSearchInput,
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
    hovered: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      filter: '',
    };
  },
  computed: {
    ...mapGetters({
      isEntityRestricted: IS_ENTITY_RESTRICTED,
    }),
    headerClass() {
      return {
        'x-card-header': true,
        hidden: !this.headerVisible,
      };
    },
    headerVisible() {
      return this.hovered || this.dataFilter || this.chart.historical;
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
      return this.chart.view === 'histogram' && this.chart.metric === 'segment';
    },
  },
  mounted() {
    this.filter = this.chart.search || '';
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
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
          historical: this.allowedDates[query.module][historical],
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
    fetchMorePanel(uuid, skip, historical) {
      this.fetchDashboardPanel({
        uuid,
        spaceId: this.currentSpace,
        skip,
        limit: 100,
        historical,
        search: this.filter,
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
    },
  },
};
</script>

<style lang="scss">
  .x-card-header {
    display: flex;
    &.hidden {
      display: none;
    }
    > div {
      height: 30px;
      &.x-search-input {
        margin-right: 5px;
      }
    }
  }
</style>
