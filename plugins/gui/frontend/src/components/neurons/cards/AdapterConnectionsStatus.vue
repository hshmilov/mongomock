<template>
  <div
    class="x-card adapter-connections-status"
    :class="{double}"
  >
    <div class="header">
      <div class="header__title">
        <div
          class="card-title"
          title="Adapter Connections Status"
        >Adapter Connections Status</div>
      </div>
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
              <a :href="`/adapters/${adapter.id}`">
                <img
                  :src="require(`Logos/adapters/${adapter.id}.png`)"
                  width="30"
                >
              </a>
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
              @mouseover="hoveredItem = { header: 'Number of connections with no errors', body: adapter.successClients }"
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

      <template v-if="dataLength">
        <div class="separator" />
        <XPaginator
          :from.sync="dataFrom"
          :to.sync="dataTo"
          :limit="limit"
          :count="dataLength"
        />
      </template>


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
import XIcon from '@axons/icons/Icon';
import _orderBy from 'lodash/orderBy';
import XPaginator from '@axons/layout/Paginator.vue';
import XChartTooltip from '@axons/charts/ChartTooltip.vue';
import { mapGetters, mapActions } from 'vuex';
import { FETCH_ADAPTERS } from '@store/modules/adapters';

export default {
  name: 'XAdapterConnectionsStatus',
  components: { XPaginator, XChartTooltip, XIcon },
  props: {
    data: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      dataFrom: 1,
      dataTo: 1,
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
      return this.dataLength > 6;
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
      return this.sortedAdapters.slice(this.dataFrom - 1, this.dataTo);
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
  },
  created() {
    this.fetchAdapters();
  },
  methods: {
    ...mapActions({ fetchAdapters: FETCH_ADAPTERS }),
  },
};
</script>

<style lang="scss">
  .adapter-connections-status {
    --adapter-row-height: 30px;
    --adapter-row-margin-bottom: 20px;
    grid-column: 3;
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
        }
        .quantity {
          font-weight: 400;
          font-size: 16px;
        }
        .icon-error svg, .icon-success {
          font-size: 20px;
          margin-right: 4px;
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
      border-top: 2px dashed #DEDEDE;
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

  }
</style>
