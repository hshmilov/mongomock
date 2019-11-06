<template>
  <x-card
    :title="title"
    class="x-discovery-card"
    :class="dataSizeClass"
  >
    <div class="data-discovery">
      <x-histogram
        :data="dataCounters"
        :condensed="true"
        :limit="20"
        @click-one="runAdaptersFilter"
      />
      <div class="discovery-summary">
        <div class="summary-row">
          <div class="summary-title">Total {{ name }}s seen</div>
          <div class="quantity">{{ dataSeen }}</div>
        </div>
        <div class="summary-row">
          <div class="summary-title mid">Axonius {{ name }} Correlation</div>
          <div class="quantity">
            <svg-icon
              name="symbol/funnel"
              :original="true"
              width="48"
              height="48"
            />
          </div>
        </div>
        <div class="summary-row">
          <div class="summary-title">Total unique {{ name }}s</div>
          <div class="quantity">{{ dataUnique }}</div>
        </div>
      </div>
    </div>
  </x-card>
</template>

<script>
  import xCard from '../../axons/layout/Card.vue'
  import xHistogram from '../../axons/charts/Histogram.vue'

  export default {
    name: 'XDiscoveryCard',
    components: { xCard, xHistogram },
    props: {
      data: {
        type: Object,
        required: true
      },
      name: {
        type: String,
        required: true
      }
    },
    computed: {
      title () {
        return `${this.name} Discovery`
      },
      dataCounters () {
        if (!this.data || !this.data.counters) return []
        return [...this.data.counters]
          .sort((first, second) => second.value - first.value)
          .map(item => {
            return {
              name: item.name, value: item.value,
              title: (item.value !== item.meta) ? `${item.value} (${item.meta})` : item.value
            }
          })
      },
      dataSizeClass () {
        if (!this.dataCounters || !this.dataCounters.length) return ''
        if (this.dataCounters.length > 12) return 'triple'
        if (this.dataCounters.length > 4) return 'double'
        return ''
      },
      dataSeen () {
        let seen = this.data.seen || 0
        let seenGross = this.data.seen_gross || 0
        if (seen !== seenGross) {
          return `${seen} (${seenGross})`
        }
        return seen
      },
      dataUnique () {
        return Math.min(this.data.unique || 0, this.data.seen || 0)
      }
    },
    methods: {
      runAdaptersFilter (index) {
        if (!this.dataCounters || !this.dataCounters[index]) return
        this.$emit('filter', `adapters == '${this.dataCounters[index].name}'`)
      }
    }
  }
</script>

<style lang="scss">
   .x-discovery-card.device-discovery{
        grid-column: 1;
    }

    .x-discovery-card.user-discovery{
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
                        }
                    }

                    .quantity {
                        font-weight: 500;
                        width: 120px;
                        text-align: center;
                    }

                    .svg-icon {
                        margin: 6px 0;

                        .svg-fill {
                            fill: $theme-orange;
                        }
                    }
                }
            }
        }
    }
</style>