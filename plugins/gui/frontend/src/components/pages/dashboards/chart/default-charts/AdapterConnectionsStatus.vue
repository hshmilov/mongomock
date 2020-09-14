<template>
  <div
    class="x-chart x-dashboard-card adapter-connections-status"
    :class="{double}"
  >
    <div class="header">
      <h3
        class="chart-title"
        title="Adapter Connections Status"
      >Adapter Connections Status</h3>
    </div>

    <div class="body">

      <XChartTooltip
        :header="tooltipDetails.header"
        :body="tooltipDetails.body"
      >
        <div
          slot="tooltipActivator"
          :class="{fullHeight}"
        >
          <div
            v-for="adapter in pageData"
            :key="adapter.title"
            class="adapter"
          >
            <div
              @mouseover="hoveredItem = { header: adapter.title, body: '' }"
              @mouseout="hoveredItem = null"
            >
              <RouterLink
                :to="getAdapterRoute(adapter.id)"
              >
                <img
                  :src="require(`Logos/adapters/${adapter.id}.png`)"
                  width="30"
                >
              </RouterLink>
            </div>


            <div
              v-if="adapter.errorClients"
              @mouseover="hoveredItem = { header: 'Number of connections with errors', body: adapter.errorClients }"
              @mouseout="hoveredItem = null"
            >
              <XIcon
                family="symbol"
                type="error"
                theme="filled"
                class="icon-error"
              />
              <span class="quantity">{{ adapter.errorClients }}</span>
            </div>

            <div
              v-if="adapter.successClients"
              @mouseover="hoveredItem = { header: 'Number of adapter connections successfully connected', body: adapter.successClients }"
              @mouseout="hoveredItem = null"
            >
              <XIcon
                family="symbol"
                type="success"
                theme="filled"
                class="icon-success"
              />
              <span class="quantity">{{ adapter.successClients }}</span>
            </div>


          </div>
        </div>
      </XChartTooltip>
    </div>
    <div class="footer">
      <div
        v-if="dataLength"
        class="footer__paginator"
      >
        <PaginatorFastNavWrapper
          :page="page"
          :total="dataLength"
          :limit="10"
          @first="page = 1"
          @last="$event => page = $event"
        >
          <APagination
            v-model="page"
            size="small"
            simple
            :total="dataLength"
            :page-size="limit"
            :default-current="1"
          />
        </PaginatorFastNavWrapper>
        <p class="pagination__text">
          {{ totalResults }}
        </p>
      </div>
      <div class="summaries">
        <div class="summary-row">
          <div class="summary-title">
            Configured Adapters
          </div>
          <div class="quantity">
            {{ getConfiguredAdapters.length }}
          </div>
        </div>
        <div class="summary-row">
          <div class="summary-title">
            Adapters with Errors
          </div>
          <div class="quantity">
            {{ getConfiguredAdapters.filter(adapter => adapter.errorClients).length }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import PaginatorFastNavWrapper from '@axons/layout/PaginatorFastNavWrapper.vue';
import { Pagination as APagination } from 'ant-design-vue';
import _orderBy from 'lodash/orderBy';
import XChartTooltip from '@axons/charts/ChartTooltip.vue';
import { mapGetters, mapActions } from 'vuex';
import { FETCH_ADAPTERS } from '@store/modules/adapters';
import { FETCH_DISCOVERY_DATA } from '@store/modules/dashboard';
import { getTotalResultsTitle } from '@/helpers/dashboard';


export default {
  name: 'XAdapterConnectionsStatus',
  components: { XChartTooltip, PaginatorFastNavWrapper, APagination },
  data() {
    return {
      data: {},
      page: 1,
      limit: 10,
      hoveredItem: null,
    };
  },
  computed: {
    ...mapGetters({
      getConfiguredAdapters: 'getConfiguredAdapters',
    }),
    fullHeight() {
      return this.dataLength >= this.limit;
    },
    double() {
      return this.dataLength > 5;
    },
    sortedAdapters() {
      const adapters = this.getConfiguredAdapters.map((adapter) => {
        let connectionOrder = 2;
        if (adapter.errorClients) {
          connectionOrder = 0;
          if (adapter.successClients) connectionOrder = 1;
        }
        return { ...adapter, connectionOrder };
      });

      return _orderBy(adapters, ['connectionOrder', 'errorClients', 'title'], ['asc', 'desc', 'asc']);
    },
    pageData() {
      const from = (this.page - 1) * this.limit;
      const to = from + this.limit;
      const pageData = this.sortedAdapters.slice(from, to);
      return pageData;
    },
    dataLength() {
      return this.sortedAdapters.length;
    },
    tooltipDetails() {
      if (!this.hoveredItem) {
        return {};
      }

      return {
        header: {
          class: 'tooltip-header-content pie-fill-1',
          name: this.hoveredItem.header,
        },
        body: {
          percentage: this.hoveredItem.body,
        },
      };
    },
    totalResults() {
      const rangeFrom = ((this.page * this.limit) - this.limit) + 1;
      const rangeTo = this.page * this.limit;
      return getTotalResultsTitle(this.dataLength, [rangeFrom, rangeTo], 'adapters');
    },
  },
  async created() {
    this.fetchAdapters();
    const res = await this.fetchDiscoveryData({ module: 'users' });
    this.data = res.data;
  },
  methods: {
    ...mapActions({ fetchAdapters: FETCH_ADAPTERS, fetchDiscoveryData: FETCH_DISCOVERY_DATA }),
    getAdapterRoute(adapterId) {
      return {
        path: `adapters/${adapterId}`,
      };
    },
  },
};
</script>

<style lang="scss">
  .adapter-connections-status {
    --adapter-row-height: 30px;
    --adapter-row-margin-bottom: 20px;
    grid-row: 1;
    &.double {
      grid-row: 1 / span 2;
    }
    .fullHeight {
      height: calc((var(--adapter-row-height) + var(--adapter-row-margin-bottom)) * 10);
    }
    .adapter {
      display: flex;
      margin-bottom: var(--adapter-row-margin-bottom);
      height: var(--adapter-row-height);
      > div {
        width: 30%;
        display: flex;
        align-items: center;
        .x-icon {
          margin: 0px 6px 0px 0px;
          font-size: 20px;
          margin-right: 8px;
        }
        .quantity {
          font-weight: 400;
          font-size: 16px;
        }
      }
    }
    .separator {
      width: 100%;
      height: 1px;
      background-color: rgba(255, 125, 70, 0.2);
      margin: 12px 0;
    }

    .summaries {
      border-top: 1px dashed #DEDEDE;
      padding-top: 12px;

      .summary-row {
          display: flex;
          font-size: 16px;
          &:nth-of-type(1) {
            margin-bottom: 12px;
          }
          .summary-title {
              flex: auto 1 0;
          }

          .quantity {
              font-weight: 500;
              width: 120px;
              text-align: center;
          }
      }
    }

    &.x-dashboard-card .footer {
      height: 150px;
    }

  }
</style>
