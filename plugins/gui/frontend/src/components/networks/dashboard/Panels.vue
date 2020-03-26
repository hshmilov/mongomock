<template>
  <Draggable
    v-model="orderedPanels"
    tag="transition-group"
    :animation="1000"
    draggable=".card__item"
    handle=".drag_handler"
    ghost-class="ghost"
    class="x-panels"
    :move="checkMove"
  >
    <XPanel
      v-for="(chart, chartInd) in orderedPanels"
      :id="chart.uuid"
      :key="chart.uuid"
      :chart="chart"
      :read-only="isReadOnly"
      :draggable="true"
      @remove="() => verifyRemovePanel(chart.uuid)"
      @edit="() => editPanel(chart)"
      @export="() => exportCSV(chart.uuid, chart.name, chart.historical)"
    />
    <slot name="pre" />
    <slot name="post" />
    <XCard
      :key="9999"
      title="New Chart"
      class="chart-new print-exclude"
    >
      <XButton
        :id="newId"
        link
        :disabled="isReadOnly"
        @click="addNewPanel"
      >
        +
      </XButton>
    </XCard>
    <XToast
      v-if="message"
      v-model="message"
    />
    <XModal
      v-if="removed"
      :key="10000"
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
    </XModal>
  </Draggable>
</template>

<script>
import Draggable from 'vuedraggable';
import {
  mapState, mapMutations, mapActions,
} from 'vuex';
import XCard from '../../axons/layout/Card.vue';
import XButton from '../../axons/inputs/Button.vue';
import xToast from '../../axons/popover/Toast.vue';
import XModal from '../../axons/popover/Modal/index.vue';
import XPanel from './Panel.vue';

import {
  REMOVE_DASHBOARD_PANEL, FETCH_CHART_SEGMENTS_CSV, SAVE_REORDERED_PANELS,
} from '../../../store/modules/dashboard';
import { UPDATE_DATA_VIEW } from '../../../store/mutations';

export default {
  name: 'XPanels',
  components: {
    XCard, XButton, xToast, XModal, Draggable, XPanel,
  },
  props: {
    panels: {
      type: Array,
      default: () => [],
    },
    newId: {
      type: String,
      default: undefined,
    },
    panelsOrder: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      removed: null,
      message: '',
    };
  },
  computed: {
    ...mapState({
      isReadOnly(state) {
        const user = state.auth.currentUser.data;
        if (!user || !user.permissions) return true;
        return user.permissions.Dashboard === 'ReadOnly';
      },
      currentSpace(state) {
        return state.dashboard.currentSpace || state.dashboard.spaces.data.find((space) => space.type === 'default').uuid;
      },
      allowedDates(state) {
        return state.constants.allowedDates;
      },
    }),
    orderedPanels: {
      get() {
        if (this.panelsOrder) {
          return this.panelsOrder.map((uuid) => this.panelsById[uuid])
            .filter((panel) => panel !== undefined);
        }
        return this.processedPanels;
      },
      set(newPanels) {
        this.saveReorderedPanels({
          panels_order: newPanels.map((panel) => panel.uuid),
          spaceId: this.currentSpace,
        });
      },
    },
    panelsById() {
      return this.processedPanels.reduce((acc, item) => {
        acc[item.uuid] = item;
        return acc;
      }, {});
    },
    processedPanels() {
      // Filter out spaces without data or with hide_empty and remainder 100%
      return this.panels.filter((chart) => (chart && chart.data && chart.data.length
                && ![0, 1].includes(chart.data[0].value)) || !chart.hide_empty);
    },
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    ...mapActions({
      removePanel: REMOVE_DASHBOARD_PANEL,
      fetchChartSegmentsCSV: FETCH_CHART_SEGMENTS_CSV,
      saveReorderedPanels: SAVE_REORDERED_PANELS,
    }),
    checkMove(evt) {
      // 1. FutureIndex is the index on whish your intend to drop on
      // when dragging after the last panel or on the first panel
      // the futureIndex is 0
      // 2. evt.related.id holds the uuid of the targeted panel.
      // Since whe want to prevent dragging after the last panel (Add New Chart Panel)
      // but enable dragging on the first panel
      return !(evt.draggedContext.futureIndex === 0 && evt.related.id !== this.panelsOrder[0]);
    },
    addNewPanel() {
      this.$emit('add');
    },
    verifyRemovePanel(chartId) {
      this.removed = chartId;
    },
    confirmRemovePanel() {
      this.removePanel({
        panelId: this.removed,
        spaceId: this.currentSpace,
      });
      this.removed = null;
    },
    editPanel(panel) {
      this.$emit('edit', {
        uuid: panel.uuid,
        data: {
          name: panel.name,
          metric: panel.metric,
          view: panel.view,
          config: panel.config,
          updated: panel.last_updated,
        },
      });
    },
    exportCSV(uuid, name, historical) {
      this.fetchChartSegmentsCSV({
        uuid,
        name,
        historical,
      });
    },
    cancelRemovePanel() {
      this.removed = null;
    },
  },
};
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
      .chart-spinner {
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
