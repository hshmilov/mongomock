<template>
  <div
    class="x-dashboard-card x-discovery-card"
    :class="dataSizeClass"
  >
    <div class="header">
      <h3
        class="chart-title"
        :title="title"
      >{{ title }}</h3>
    </div>

    <div class="body">
      <div class="data-discovery">
        <XHistogram
          :data="dataCounters"
          :page-data="pageData"
          :condensed="true"
          :limit="20"
          @click-one="runAdaptersFilter"
        />
      </div>
    </div>
    <div class="footer">
      <div class="footer__paginator">
        <PaginatorFastNavWrapper
          :page="page"
          :total="count"
          :limit="20"
          @first="page = 1"
          @last="$event => page = $event"
        >
          <APagination
            v-model="page"
            size="small"
            simple
            :total="count"
            :page-size="limit"
            :default-current="1"
          />
        </PaginatorFastNavWrapper>
        <p class="pagination__text">
          {{ totalResults }}
        </p>
      </div>
      <div class="discovery-summary">
        <div class="summary-row">
          <div class="summary-title">
            Total {{ name }}s seen
          </div>
          <div
            class="quantity"
          >
            <span :title="summaryLevelUniqueAssetsLabel">{{ totalSeen }}</span>
            <span
              v-if="totalGrossSeen !== totalSeen"
              :title="summaryLevelDuplicatedAssetsLabel"
            >({{ totalGrossSeen }})</span>
          </div>
        </div>
        <div class="summary-row">
          <div class="summary-title mid">
            Axonius {{ name }} Correlation
          </div>
          <div class="quantity">
            <XIcon
              family="symbol"
              type="funnel"
            />
          </div>
        </div>
        <div class="summary-row">
          <div class="summary-title">
            Total unique {{ name }}s
          </div>
          <div class="quantity">
            {{ dataUnique }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { mapMutations, mapActions, mapState } from 'vuex';
import { DiscoveryStatusEnum } from '@constants/discovery';
import { FETCH_DISCOVERY_DATA } from '@store/modules/dashboard';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import XIcon from '@axons/icons/Icon';
import XHistogram from '@axons/charts/Histogram.vue';
import { Pagination as APagination } from 'ant-design-vue';
import PaginatorFastNavWrapper from '@axons/layout/PaginatorFastNavWrapper.vue';
import { getTotalResultsTitle } from '@/helpers/dashboard';

export default {
  name: 'XDiscoveryCard',
  components: {
    XHistogram, XIcon, APagination, PaginatorFastNavWrapper,
  },
  props: {
    entity: {
      type: String,
      required: true,
    },
    name: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      data: {},
      limit: 20,
      page: 1,
      adapterLevelDuplicatedAssetsLabel: 'The number of assets fetched from all adapter connections for this adapter, including '
              + 'assets fetched from different components/modules of this adapter, outdated or duplicated assets.',
      adapterLevelAssetsLabel: 'The number of assets fetched from all adapter connections for this adapter.',
      summaryLevelUniqueAssetsLabel: 'The number of adapter-unique assets fetched from all adapter connections.',
      summaryLevelDuplicatedAssetsLabel: 'The number of assets fetched from all adapter connections of all adapters, including'
              + ' assets fetched from different components/modules of all adapters, outdated or duplicated assets.',
    };
  },
  computed: {
    ...mapState({
      discoveryStatus(state) {
        return state.dashboard.lifecycle.data.status;
      },
    }),
    title() {
      return `${this.name} Discovery`;
    },
    dataCounters() {
      if (!this.data || !this.data.counters) return [];
      return [...this.data.counters]
        .sort((first, second) => second.value - first.value)
        .map(this.buildDiscoveryItem);
    },
    count() {
      return this.dataCounters.length;
    },
    pageData() {
      const from = (this.page - 1) * this.limit;
      const to = from + this.limit;
      const pageData = this.dataCounters.slice(from, to);
      return pageData;
    },
    dataSizeClass() {
      if (!this.dataCounters || !this.dataCounters.length) return '';
      if (this.dataCounters.length > 10) return 'triple';
      if (this.dataCounters.length > 5) return 'double';
      return '';
    },
    totalSeen() {
      return this.data.seen || 0;
    },
    totalGrossSeen() {
      return this.data.seen_gross || 0;
    },
    dataUnique() {
      return Math.min(this.data.unique || 0, this.data.seen || 0);
    },
    totalResults() {
      const rangeFrom = ((this.page * this.limit) - this.limit) + 1;
      const rangeTo = this.page * this.limit;
      return getTotalResultsTitle(this.count, [rangeFrom, rangeTo], 'adapters');
    },
  },
  watch: {
    discoveryStatus: {
      handler: 'fetchDataWhenDiscoveryDone',
      immediate: true,
    },
  },
  async created() {
    const res = await this.fetchDiscoveryData({ module: this.entity });
    this.data = res.data;
  },
  destroyed() {
    clearTimeout(this.timer);
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    ...mapActions({
      fetchDiscoveryData: FETCH_DISCOVERY_DATA,
    }),
    runAdaptersFilter(index) {
      if (!this.dataCounters || !this.dataCounters[index]) return;
      const filter = `adapters == '${this.dataCounters[index].name}'`;
      if (!this.$canViewEntity(this.entity)) return;
      this.updateView({
        module: this.entity,
        view: {
          page: 0,
          query: {
            filter, expressions: [],
          },
        },
        selectedView: null,
      });
      this.$router.push({ path: this.entity });
    },
    buildDiscoveryItem(item) {
      if (item.value !== item.meta) {
        return {
          ...item,
          htmlContent: `<span title="${this.adapterLevelAssetsLabel}">${item.value}</span>`
                  + `<span title="${this.adapterLevelDuplicatedAssetsLabel}"> (${item.meta})</span>`,
          value: item.value,
        };
      }
      return {
        ...item,
        title: item.value,
        adapterLevelAssetsLabel: this.adapterLevelAssetsLabel,
        htmlContent: `<span title="${this.adapterLevelAssetsLabel}">${item.value}</span>`,
        value: item.value,
      };
    },
    async fetchDataWhenDiscoveryDone(status, prevStatus) {
      if (status === DiscoveryStatusEnum.done && prevStatus === DiscoveryStatusEnum.running) {
        const res = await this.fetchDiscoveryData({ module: this.entity });
        this.data = res.data;
      }
    },
  },
};
</script>

<style lang="scss">
  .x-discovery-card {
    grid-row: 1;

    &.double {
      grid-row: 1 / span 2;
    }

    &.triple {
      grid-row: 1 / span 3;
    }
  }

  .x-discovery-card {
    .summary-title {
      text-transform: capitalize;
    }

    .footer {
      .discovery-summary {
        border-top: 1px dashed $grey-2;
        padding-top: 12px;

        .summary-row {
          display: flex;
          font-size: 16px;

          .summary-title {
            flex: auto 1 0;

            &.mid {
              font-size: 14px;
              color: $theme-orange;
              margin: auto 0;
              text-transform: capitalize;
              font-weight: 300;
            }
          }

          .quantity {
            font-weight: 500;
            width: 120px;
            text-align: center;
            .x-icon {
              font-size: 48px;
              color: $theme-orange;
              margin: 4px 0;
              .svg-fill {
                fill: $theme-orange;
              }
            }
          }
        }
      }
    }
  }
</style>
