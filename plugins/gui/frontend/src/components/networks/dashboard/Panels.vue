<template>
  <div class="x-panels">
    <slot name="pre" />
    <x-card
      v-for="(chart, chartInd) in processedPanels"
      :id="getId(chart.name)"
      :key="chart.name"
      :title="chart.name"
      :removable="!isReadOnly"
      @remove="removeDashboard(chart.uuid)"
    >
      <div
        v-if="chart.metric !== 'timeline'"
        class="card-history"
      >
        <x-historical-date
          v-model="cardToDate[chart.uuid]"
          @clear="clearDate(chart.uuid)"
          @input="confirmPickDate(chart.uuid, chart.name)"
        />
      </div>
      <component
        :is="`x-${chart.view}`"
        :id="getId(chart.name) + '_view'"
        :data="chart.data"
        @click-one="runChartFilter(chartInd, $event)"
      />
    </x-card>
    <slot name="post" />
    <x-card
      title="New Chart"
      class="chart-new print-exclude"
    >
      <x-button
        :id="newId"
        link
        :disabled="isReadOnly"
        @click="addNewPanel"
      >+</x-button>
    </x-card>
    <x-toast
      v-if="message"
      v-model="message"
    />
  </div>
</template>

<script>
  import xCard from '../../axons/layout/Card.vue'
  import xHistoricalDate from '../../neurons/inputs/HistoricalDate.vue'
  import xHistogram from '../../axons/charts/Histogram.vue'
  import xPie from '../../axons/charts/Pie.vue'
  import xSummary from '../../axons/charts/Summary.vue'
  import xLine from '../../axons/charts/Line.vue'
  import xButton from '../../axons/inputs/Button.vue'
  import xToast from '../../axons/popover/Toast.vue'

  import {mapState, mapGetters, mapMutations, mapActions} from 'vuex'
  import {REMOVE_DASHBOARD_PANEL, FETCH_HISTORICAL_SAVED_CARD} from '../../../store/modules/dashboard'
  import {IS_ENTITY_RESTRICTED} from '../../../store/modules/auth'
  import {UPDATE_DATA_VIEW} from '../../../store/mutations'

  export default {
    name: 'XPanels',
    components: {
      xCard, xHistoricalDate, xHistogram, xPie, xSummary, xLine, xButton, xToast
    },
    props: {
      panels: {
        type: Array,
        required: true
      },
      newId: {
        type: String,
        default: undefined
      }
    },
    data () {
      return {
        cardToDate: {},
        cardToHistory: {},
        message: ''
      }
    },
    computed: {
      ...mapState({
        isReadOnly (state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions.Dashboard === 'ReadOnly'
        }
      }),
      ...mapGetters({
        isEntityRestricted: IS_ENTITY_RESTRICTED
      }),
      processedPanels () {
        return this.panels.map(chart => {
          if (chart.metric === 'timeline') return chart
          return { ...chart,
            showingHistorical: this.cardToDate[chart.uuid],
            data: chart.data.map(item => {
              let historicalCard = this.cardToHistory[chart.uuid]
              if (historicalCard) {
                let historicalCardView = historicalCard[item.name]
                if (!historicalCardView) return null
                return {
                  ...item,
                  value: historicalCard[item.name].value,
                  showingHistorical: historicalCard[item.name].accurate_for_datetime
                }
              }
              return item
            }).filter(x => x)
          }
        })
        // Filter out spaces without data or with hide_empty and remainder 100%
        .filter(chart => chart && chart.data && !(chart.hide_empty && [0, 1].includes(chart.data[0].value)))
      }
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW
      }),
      ...mapActions({
        removeDashboard: REMOVE_DASHBOARD_PANEL,
        fetchHistoricalCard: FETCH_HISTORICAL_SAVED_CARD
      }),
      addNewPanel() {
        this.$emit('add')
      },
      getId (name) {
        return name.split(' ').join('_').toLowerCase()
      },
      clearDate (cardId) {
        this.cardToDate = { ...this.cardToDate, [cardId]: null }
        this.cardToHistory = { ...this.cardToHistory, [cardId]: null }
      },
      confirmPickDate (cardId, cardName) {
        let pendingDateChosen = this.cardToDate[cardId]
        if (!pendingDateChosen) {
          this.clearDate(cardId)
          return
        }
        this.fetchHistoricalCard({
          cardId: cardId,
          date: pendingDateChosen
        }).then(response => {
          if (!response.data) {
            this.message = `No data from ${pendingDateChosen} for '${cardName}'`
            this.clearDate(cardId)
          } else {
            this.cardToDate = { ...this.cardToDate }
            this.cardToHistory = { ...this.cardToHistory, [cardId]: response.data }
          }
        })
      },
      runChartFilter (chartInd, queryInd) {
        let query = this.processedPanels[chartInd].data[queryInd]
        if (this.isEntityRestricted(query.module) || query.view === undefined || query.view === null) {
          return
        }
        this.updateView({
          module: query.module, view: query.view
        })
        this.$router.push({ path: query.module })
      },
    }
  }
</script>

<style lang="scss">
    .x-panels {
        padding: 8px;
        display: grid;
        grid-template-columns: repeat(auto-fill, 344px);
        grid-gap: 12px;
        width: 100%;

        .x-card {
            min-height: 300px;

            .card-history {
                font-size: 12px;
                color: $grey-4;
                text-align: right;
                margin-bottom: 8px;

                .cov-vue-date {
                    width: auto;
                    margin-left: 4px;

                    .cov-datepicker {
                        line-height: 16px;
                    }

                    .cov-date-body {
                        max-width: 240px;
                    }
                }
            }
        }

        .chart-new {
            .link {
                font-size: 144px;
                text-align: center;
                line-height: 200px;
            }
        }
    }

</style>