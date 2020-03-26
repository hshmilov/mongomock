<template>
  <XChartTooltip
    :header="tooltipDetails.header"
    :body="tooltipDetails.body"
  >
    <div
      slot="tooltipActivator"
      class="x-histogram"
      :class="{disabled: readOnly, condensed}"
    >
      <div
        class="histogram-container"
      >
        <div
          v-for="(item, index) in pageData"
          :key="index"
          class="histogram-item"
          @click="() => onClick(index)"
        >
          <div
            class="item-bar"
          >
            <img
              v-if="condensed"
              :src="require(`Logos/adapters/${item.name}.png`)"
              width="30"
              @mouseover="hoveredItem = item"
              @mouseout="hoveredItem = null"
            >
            <div class="bar-container">
              <div :style="{width: calculateBarWidth(item.value) + 'px'}">
                <div
                  class="bar growing-x"
                  :name="item.name"
                  @mouseover="hoveredItem = item"
                  @mouseout="hoveredItem = null"
                />
              </div>
              <div class="quantity">
                {{ item.title || item.value }}
              </div>
            </div>
          </div>
          <div
            v-if="!condensed"
            class="item-title"
            @mouseover="hoveredItem = item"
            @mouseout="hoveredItem = null"
          >{{ item.name }}</div>
        </div>
      </div>
      <template v-if="dataLength">
        <div class="separator" />
        <XPaginator
          :from.sync="dataFrom"
          :to.sync="dataTo"
          :limit="limit"
          :count="dataLength"
        />
      </template>
    </div>
  </XChartTooltip>
</template>

<script>
import XPaginator from '../layout/Paginator.vue';
import XChartTooltip from './ChartTooltip.vue';
import { pluginMeta } from '../../../constants/plugin_meta';

export default {
  name: 'XHistogram',
  components: { XPaginator, XChartTooltip },
  props: {
    data: {
      type: Array,
      required: true,
    },
    limit: {
      type: Number,
      default: 5,
    },
    condensed: {
      type: Boolean,
      default: false,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      dataFrom: 1,
      dataTo: 0,
      hoveredItem: null,
    };
  },
  computed: {
    maxWidth() {
      if (this.condensed) return 280;
      return 240;
    },
    maxQuantity() {
      if (!this.pageData.length) {
        return 0;
      }
      let max = this.data[0].value;
      this.data.slice(1).forEach((item) => {
        if (item && item.value > max) {
          max = item.value;
        }
      });
      return max;
    },
    dataLength() {
      return this.data.length;
    },
    nextFetchFrom() {
      return this.dataTo + this.limit;
    },
    prevFetchFrom() {
      return this.dataFrom - 1 - this.limit;
    },
    pageData() {
      if (this.nextFetchFrom < this.dataLength && !this.data[this.nextFetchFrom]) {
        this.$emit('fetch', this.nextFetchFrom);
      }
      if (this.prevFetchFrom >= 0 && !this.data[this.prevFetchFrom]) {
        this.$emit('fetch', Math.max(1, this.prevFetchFrom - 100 + this.limit));
      }
      if (!this.data[this.dataFrom - 1]) {
        return [];
      }
      return this.data.slice(this.dataFrom - 1, this.dataTo);
    },
    tooltipDetails() {
      if (!this.hoveredItem) {
        return {};
      }

      const { value } = this.hoveredItem;
      let { name } = this.hoveredItem;
      name = pluginMeta[name] ? pluginMeta[name].title : name;

      return {
        header: {
          class: 'tooltip-header-content pie-fill-1',
          name,
        },
        body: {
          value,
          percentage: this.getValuePercentage(value),
        },
      };
    },
    totalValue() {
      return this.data.reduce((total, item) => {
        const value = item.name === 'No Value' ? 0 : item.value;
        return total + value;
      }, 0);
    },
  },
  methods: {
    getValuePercentage(value) {
      let percentage = (value / this.totalValue) * 100;
      if (percentage) {
        percentage = `(${percentage % 1 ? percentage.toFixed(2) : percentage}%)`;
      } else {
        percentage = '';
      }
      return percentage;
    },
    calculateBarWidth(quantity) {
      return (this.maxWidth * quantity) / this.maxQuantity;
    },
    onClick(pageIndex) {
      this.$emit('click-one', this.dataFrom + pageIndex - 1);
    },
  },
};
</script>

<style lang="scss">

   .card-history ~.x-histogram {
      .histogram-container {
        min-height: 220px
      }
    }
    .x-histogram {
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        position: relative;
        .histogram-container {
          display: flex;
          flex-direction: column;
          flex: 1 0 auto;
        }
        .histogram-item {
            width: 100%;
            cursor: pointer;
            .bar-container {
                display: flex;
                width: 100%;
            }
            .item-bar {
                display: flex;
                align-items: center;
                line-height: 24px;
                img {
                    margin-right: 8px;
                }
                .bar {
                    height: 20px;
                    background-color: rgba($grey-2, 0.4);
                    &:hover {
                        background-color: $grey-2;
                    }
                }
                .quantity {
                    margin-left: 8px;
                    flex: 1 0 auto;
                    text-align: right;
                    font-weight: 400;
                    font-size: 18px;
                }
            }
            .item-title {
                white-space: nowrap;
                text-overflow: ellipsis;
                overflow: hidden;
                width: 300px;
            }
        }
        .separator {
          width: 100%;
          height: 1px;
          background-color: rgba(255, 125, 70, 0.2);
          margin: 12px 0;
        }
        .remainder {
            font-size: 12px;
            color: $grey-3;
            width: 100%;
            text-align: right;
        }
        &.disabled {
            .histogram-item {
                cursor: default;
                .bar:hover {
                    background-color: rgba($grey-2, 0.4);
                }
            }
        }
        &.condensed {
            .bar-container {
                width: calc(100% - 36px);
                flex-direction: column;
            }
            .item-bar {
                width: 100%;
                cursor: pointer;
                margin-bottom: 12px;
                .bar {
                    height: 8px;
                    background-color: rgba($grey-2, 0.8);
                }
                .quantity {
                    font-size: 16px;
                    text-align: left;
                    margin-top: 2px;
                    margin-left: 0;
                }
            }
            &.disabled .histogram-item .bar:hover {
                background-color: rgba($grey-2, 0.8);
            }
        }
    }
</style>
