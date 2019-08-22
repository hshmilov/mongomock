<template>
  <div
    class="x-histogram"
    :class="{disabled: readOnly, condensed}">
    <div class="histogram-container">
      <div
        v-for="(item, index) in limitedData"
        :key="index"
        class="histogram-item"
        @click="() => $emit('click-one', index)">
        <div class="item-bar">
          <img
            v-if="condensed"
            :src="require(`Logos/adapters/${item.name}.png`)"
            width="30">
          <div class="bar-container">
            <div :style="{width: calculateBarHeight(item.value) + 'px'}">
              <div
                class="bar growing-x"
                :title="item.name">
              </div>
            </div>
            <div class="quantity">{{ item.title || item.value }}</div>
          </div>
        </div>
        <div
          v-if="!condensed"
          class="item-title"
          :title="item.name">
          {{item.name}}
        </div>
      </div>
    </div>
    <template v-if="dataLength">
      <div class="separator"></div>
      <x-paginator :limit="limit" :data="data" v-model="limitedData"></x-paginator>
    </template>
  </div>
</template>

<script>

import xPaginator from '../layout/Paginator.vue'

export default {
  name: "x-histogram",
  components: { xPaginator },
  props: {
    data: { required: true },
    limit: { default: 5 },
    condensed: { default: false },
    readOnly: { default: false }
  },
  data() {
    return {
      limitedData: []
    }
  },
  computed: {
    maxWidth() {
      if (this.condensed) return 280;
      return 240;
    },
    maxQuantity() {
      let max = this.data[0].value;
      this.data.slice(1).forEach(item => {
        if (item.value > max) {
          max = item.value;
        }
      });
      return max;
    },
    dataLength() {
      return this.data.length;
    }
  },
  methods: {
    calculateBarHeight(quantity) {
      return (this.maxWidth * quantity) / this.maxQuantity;
    }
  }

};
</script>

<style lang="scss">
    .x-histogram {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        position: relative;
        flex:1;
        .histogram-container {
          display: flex;
          flex-direction: column;
          height: 100%;
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