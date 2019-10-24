<template>
  <draggable
    tag="transition-group"
    :animation="1000"
    v-model="orderedPanels"
    draggable=".card__item"
    handle=".header"
    ghost-class="ghost"
    class="x-panels"
    >
      <x-card
        v-for="(chart, chartInd) in orderedPanels"
         class="card__item"
        :draggable="true"
        :id="chart.uuid"
        :key="chart.uuid"
        :title="chart.name"
        :removable="!isReadOnly && hovered === chartInd"
        :editable="!isReadOnly && hovered === chartInd && chart.user_id !== '*'"
        :exportable="chart.metric==='segment' && hovered === chartInd"
        @mouseenter.native="() => enterPanel(chartInd)"
        @mouseleave.native="leavePanel"
        @remove="() => verifyRemovePanel(chart.uuid)"
        @edit="() => editPanel(chart)"
        @export="() => exportCSV(chart.uuid, chart.name)"
      >
        <div
          v-if="chart.metric !== 'timeline'"
          class="card-history"
        >
          <x-historical-date
            v-model="cardToDate[chart.uuid]"
            :hide="hovered !== chartInd && !cardToDate[chart.uuid]"
            @clear="clearDate(chart.uuid)"
            @input="confirmPickDate(chart.uuid, chart.name)"
          />
        </div>
        <div
          v-if="chart.loading"
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
        <component
          :is="`x-${chart.view}`"
          v-else-if="!isChartEmpty(chart)"
          :data="chart.data"
          @click-one="($event) => runChartFilter(chartInd, $event)"
          @fetch="(skip) => fetchMorePanel(chart.uuid, skip)"
        />
        <div
          v-else
          class="no-data-found"
        >
          <svg-icon name="illustration/binocular" :original="true" height="50"/>
          <div>No data found</div>
        </div>
      </x-card>
      <slot name="pre"/>
      <slot name="post" />
      <x-card
      :key="9999"
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
      <x-modal
      :key="10000"
        v-if="removed"
        size="lg"
        approve-text="Remove Chart"
        @confirm="confirmRemovePanel"
        @close="cancelRemovePanel"
      >
        <div slot="body">
          <div>This chart will be completely removed from the system.</div>
          <div>Removing the chart is an irreversible action.</div>
          <div>Do you want to continue?</div>
        </div>
      </x-modal>
  </draggable>
</template>

<script>
  import draggable from 'vuedraggable'
  import xCard from '../../axons/layout/Card.vue'
  import xHistoricalDate from '../../neurons/inputs/HistoricalDate.vue'
  import xHistogram from '../../axons/charts/Histogram.vue'
  import xPie from '../../axons/charts/Pie.vue'
  import xSummary from '../../axons/charts/Summary.vue'
  import xLine from '../../axons/charts/Line.vue'
  import xButton from '../../axons/inputs/Button.vue'
  import xToast from '../../axons/popover/Toast.vue'
  import xModal from '../../axons/popover/Modal.vue'

  import {mapState, mapGetters, mapMutations, mapActions} from 'vuex'
  import {
    REMOVE_DASHBOARD_PANEL, FETCH_HISTORICAL_SAVED_CARD,
    FETCH_CHART_SEGMENTS_CSV, FETCH_DASHBOARD_PANEL,
    SAVE_REORDERED_PANELS
  } from '../../../store/modules/dashboard'
  import {IS_ENTITY_RESTRICTED} from '../../../store/modules/auth'
  import {UPDATE_DATA_VIEW} from '../../../store/mutations'

  export default {
    name: 'XPanels',
    components: {
      xCard, xHistoricalDate, xHistogram, xPie, xSummary, xLine, xButton, xToast, xModal, draggable
    },
    props: {
      panels: {
        type: Array,
      },
      newId: {
        type: String,
        default: undefined
      },
      panelsOrder: {
        type: Array,
      }
    },
    data () {
      return {
        cardToDate: {},
        cardToHistory: {},
        hovered: null,
        removed: null,
        message: '',
      }
    },
    computed: {
      ...mapState({
        isReadOnly (state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions.Dashboard === 'ReadOnly'
        },
        currentSpace (state) {
          return state.dashboard.currentSpace || state.dashboard.spaces.data.find(space => space.type === 'default').uuid
        }
      }),
      ...mapGetters({
        isEntityRestricted: IS_ENTITY_RESTRICTED,
      }),
      orderedPanels: {
        get () {
         if(this.panelsOrder){
            return this.panelsOrder.map( uuid => {
                return this.panelsById[uuid]
            }).filter( panel => panel !== undefined )
          } else {
            return this.processedPanels
          }
        },
        set (newPanels) {
          let paneslOrder = [];
            newPanels.forEach(panel => {
              paneslOrder.push(panel.uuid)
            })
          this.saveReorderedPanels({
            panels_order: newPanels.map(panel => panel.uuid),
            spaceId: this.currentSpace
          })
        }
      },
      panelsById () {
        return this.processedPanels.reduce((acc, item) => {
            acc[item.uuid] = item
            return acc
        }, {})
      },
      processedPanels () {
       return this.panels.map(chart => {
         if(chart)
          if (chart.metric === 'timeline' || !chart.data) return chart

          let historicalCard = this.cardToHistory[chart.uuid]
          if (!historicalCard) {
            return chart
          }
          return { ...chart,
            historical: this.cardToDate[chart.uuid],
            data: chart.data.map(item => {
              if (!historicalCard[item.name]) {
                return undefined
              }
              return {
                ...item,
                value: historicalCard[item.name].value,
              }
            }).filter(item => item)
          }
        })
        // Filter out spaces without data or with hide_empty and remainder 100%
        .filter(chart => (chart && chart.data && chart.data.length && ![0, 1].includes(chart.data[0].value))
                || !chart.hide_empty || chart.historical)
      }
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW
      }),
      ...mapActions({
        removePanel: REMOVE_DASHBOARD_PANEL,
        fetchHistoricalCard: FETCH_HISTORICAL_SAVED_CARD,
        fetchChartSegmentsCSV: FETCH_CHART_SEGMENTS_CSV,
        fetchDashboardPanel: FETCH_DASHBOARD_PANEL,
        saveReorderedPanels: SAVE_REORDERED_PANELS
      }),
      addNewPanel() {
        this.$emit('add')
      },
      enterPanel(id) {
        this.hovered = id
      },
      leavePanel() {
        this.hovered = null
      },
      verifyRemovePanel (chartId) {
        this.removed = chartId
      },
      confirmRemovePanel () {
        this.removePanel({panelId: this.removed, spaceId: this.currentSpace})
        this.removed = null
      },
      editPanel (panel) {
        this.$emit('edit', {
          uuid: panel.uuid,
          data: {
            name: panel.name,
            metric: panel.metric,
            view: panel.view,
            config: panel.config,
            updated: panel.last_updated
          }
        })
      },
      exportCSV (panelId, panelName) {
        this.fetchChartSegmentsCSV({
          panelId: panelId,
          chartName: panelName
        })
      },
      cancelRemovePanel () {
        this.removed = null
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
        let query = this.orderedPanels[chartInd].data[queryInd]
        if (this.isEntityRestricted(query.module) || query.view === undefined || query.view === null) {
          return
        }
        let historical = this.cardToDate[this.processedPanels[chartInd].uuid]
        this.updateView({
          module: query.module,
          view: historical ? { ...query.view, historical } : query.view,
          name: this.orderedPanels[chartInd].metric === 'compare' ? query.name : undefined,
          uuid: null,
        })
        this.$router.push({ path: query.module })
      },
      isChartEmpty(chart) {
        return (!chart.data || (chart.data.length === 0) || (chart.data.length === 1 && chart.data[0].value === 0))
      },
      fetchMorePanel(panelId, skip) {
        this.fetchDashboardPanel({
          uuid: panelId,
          skip,
          limit: 100
        })
      }
    }
  }
</script>

<style lang="scss">
  .flip-list-move {
  transition: transform .5s;
}

    .x-panels {
        padding: 8px;
        display: grid;
        grid-template-columns: repeat(auto-fill, 344px);
        grid-gap: 12px;
        width: 100%;
               
        > span {
          display: contents;
        }
        .card__item:not(.dragging):hover {
          border: 2px solid $grey-2;
        }
        .ghost {
            border: 3px dashed rgba($theme-blue, 0.4);
        }
        .x-card {
          min-height: 300px;
          &.chart-lifecycle {
            .header {
              padding-bottom: 0;
            }
            .body {
              padding-top: 0;
            }
          }

          .no-data-found{
            text-transform: uppercase;
            text-align: center;
            font-size: 18px;
            margin-top: 30px;

            svg {
              margin-bottom: 10px;
            }
          }

            > .body {
              flex: 1 0 auto;
              display: flex;
              flex-direction: column;
            }

            .card-history {
                height: 36px;
                font-size: 12px;
                color: $grey-4;
                text-align: right;
                margin-bottom: 8px;
                display: flex;
                justify-content: center;

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
                width: 100%;
            }
        }
      .chart-spinner{
        margin: 10px auto auto auto;
        width: 70%;
        padding: 10px;
        span {
          padding-left: 5px;
          text-transform: uppercase;
          font-size: 20px;
          vertical-align: super;
        }

        .md-progress-spinner-circle{
          stroke: $theme-orange;
        }
      }
      .chart-spinner{
        margin: 10px auto auto auto;
        width: 70%;
        padding: 10px;
        span {
          padding-left: 5px;
          text-transform: uppercase;
          font-size: 20px;
          vertical-align: super;
        }
        .md-progress-spinner-circle{
          stroke: $theme-orange;
        }
      }
    }

</style>