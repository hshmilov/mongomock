<template>
  <div
    slot="post"
    class="x-card x-discovery-card"
    :class="dataSizeClass"
  >
    <div class="header">
      <div class="header__title">
        <div
          class="card-title"
          :title="title"
        >{{ title }}</div>
      </div>
    </div>

    <div class="body">
      <div class="data-discovery">
        <XHistogram
          :data="dataCounters"
          :condensed="true"
          :limit="20"
          @click-one="runAdaptersFilter"
        />
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
  </div>
</template>

<script>
import XIcon from '@axons/icons/Icon';
import XHistogram from '../../axons/charts/Histogram.vue';

export default {
  name: 'XDiscoveryCard',
  components: { XHistogram, XIcon },
  props: {
    data: {
      type: Object,
      required: true,
    },
    name: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      adapterLevelDuplicatedAssetsLabel: 'The number of assets fetched from all adapter connections for this adapter, including '
              + 'assets fetched from different components/modules of this adapter, outdated or duplicated assets.',
      adapterLevelAssetsLabel: 'The number of assets fetched from all adapter connections for this adapter.',
      summaryLevelUniqueAssetsLabel: 'The number of adapter-unique assets fetched from all adapter connections.',
      summaryLevelDuplicatedAssetsLabel: 'The number of assets fetched from all adapter connections of all adapters, including'
              + ' assets fetched from different components/modules of all adapters, outdated or duplicated assets.',
    };
  },
  computed: {
    title() {
      return `${this.name} Discovery`;
    },
    dataCounters() {
      if (!this.data || !this.data.counters) return [];
      return [...this.data.counters]
        .sort((first, second) => second.value - first.value)
        .map(this.buildDiscoveryItem);
    },
    dataSizeClass() {
      if (!this.dataCounters || !this.dataCounters.length) return '';
      if (this.dataCounters.length > 12) return 'triple';
      if (this.dataCounters.length > 4) return 'double';
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
  },
  methods: {
    runAdaptersFilter(index) {
      if (!this.dataCounters || !this.dataCounters[index]) return;
      this.$emit('filter', `adapters == '${this.dataCounters[index].name}'`);
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
  },
};
</script>

<style lang="scss">
  .x-discovery-card.device-discovery {
    grid-column: 1;
  }

  .x-discovery-card.user-discovery {
    grid-column: 2;
  }

  .x-discovery-card {
    grid-row: 1;

    &.double {
      grid-row: 1 / span 2;
    }

    &.triple {
      grid-row: 1 / span 3;
    }

    .histogram-container {
      min-height: 180px;
    }
  }

  .x-discovery-card {
    .summary-title {
      text-transform: capitalize;
    }

    .data-discovery {
      display: flex;
      flex-direction: column;
      flex: 1;

      .discovery-summary {
        border-top: 2px dashed $grey-2;
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
