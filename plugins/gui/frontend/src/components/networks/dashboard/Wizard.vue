<template>
  <x-feedback-modal
    :launch="true"
    :handle-save="saveNewDashboard"
    :disabled="isDisabled"
    :note="note"
    approve-id="chart_save"
    @change="finishNewDashboard"
    @enter="nextWizardState"
  >
    <h3 v-if="editMode">Edit Dashboard Chart - "{{ panel.data.name }}"</h3>
    <h3 v-else>Create a Dashboard Chart</h3>
    <div class="x-chart-wizard">
      <!-- Select metric to be tested by chart -->
      <label>Chart metric</label>
      <x-select
        id="metric"
        :value="dashboard.metric"
        :options="metricOptions"
        placeholder="by..."
        @input="updateMetric"
      />
      <!-- Select method of presenting the data of the chart -->
      <template v-if="dashboard.metric">
        <label>Chart presentation</label>
        <div class="dashboard-view">
          <template v-for="view in availableViews">
            <input
              :id="view"
              :key="view"
              v-model="dashboardView"
              type="radio"
              :value="view"
            >
            <label
              :for="view"
              class="type-label"
            >
              <svg-icon
                :name="`symbol/${view}`"
                :original="true"
                height="24"
              />
            </label>
          </template>
        </div>
        <component
          :is="dashboard.metric"
          v-model="dashboard.config"
          :entities="entityOptions"
          :views="views"
          :chartView="dashboard.view"
          class="grid-span2"
          @state="nextWizardState"
          @validate="configValid = $event"
          ref="dashboardRef"
        />
      </template>

      <!-- Last name to appear as a title above the chart -->
      <label for="chart_name">Chart Title</label>
      <input
        id="chart_name"
        v-model="dashboard.name"
        type="text"
        @input="nameDashboard"
      >
      <div
        v-if="message"
        class="grid-span2 error-text"
      >{{ message }}</div>
    </div>
  </x-feedback-modal>
</template>


<script>
  import xFeedbackModal from '../../neurons/popover/FeedbackModal.vue'
  import xSelect from '../../axons/inputs/Select.vue'

  import intersect from './charts/Intersect.vue'
  import compare from './charts/Compare.vue'
  import segment from './charts/Segment.vue'
  import abstract from './charts/Abstract.vue'
  import timeline from './charts/Timeline.vue'

  import viewsMixin from '../../../mixins/views'

  import { mapMutations, mapActions } from 'vuex'
  import { SAVE_DASHBOARD_PANEL, CHANGE_DASHBOARD_PANEL } from '../../../store/modules/dashboard'
  import { NEXT_TOUR_STATE, CHANGE_TOUR_STATE, UPDATE_TOUR_STATE } from '../../../store/modules/onboarding'

  const dashboard = {
    metric: '', view: '', name: '', config: null
  }
  export default {
    name: 'XChartWizard',
    components: { xFeedbackModal, xSelect, intersect, compare, segment, abstract, timeline },
    mixins: [viewsMixin],
    props: {
      space: {
        type: String,
        required: true
      },
      panel: {
        type: Object,
        default: () => {}
      }
    },
    data () {
      return {
        dashboard: { ...dashboard },
        configValid: false
      }
    },
    computed: {
      dashboardView: {
          get () {
              return this.dashboard.view
          },
          set (value) {
              this.dashboard.view = value
              this.updateView(this.dashboard.view)
          },
      },
      editMode () {
        return this.panel !== undefined && this.panel !== null && this.panel.data !== undefined
      },
      metricOptions () {
        return [
          { name: 'intersect', title: 'Query Intersection' },
          { name: 'compare', title: 'Query Comparison' },
          { name: 'segment', title: 'Field Segmentation' },
          { name: 'abstract', title: 'Field Summary' },
          { name: 'timeline', title: 'Query Timeline' }
        ]
      },
      availableViews () {
        if (this.dashboard.metric === 'compare' || this.dashboard.metric === 'segment') {
          return ['histogram', 'pie']
        }
        if (this.dashboard.metric === 'intersect') {
          return ['pie']
        }
        if (this.dashboard.metric === 'timeline') {
          return ['line']
        }
        return ['summary']
      },
      isDisabled () {
        return (!this.dashboard.name || !this.dashboard.metric || !this.dashboardView || !this.configValid)
      },
      message () {
        if (!this.isDisabled) return ''
        return 'Missing required configuration'
      },
      note () {
        if (!this.dashboard.updated) return ''
        let dateTime = new Date(this.dashboard.updated)
        dateTime.setMinutes(dateTime.getMinutes() - dateTime.getTimezoneOffset())
        return `Last edited on ${dateTime.toISOString().replace(/(T|Z)/g, ' ').split('.')[0]}`
      }
    },
    created () {
      if (this.editMode) {
        this.dashboard = { ...this.panel.data }
        this.configValid = true
      }
    },
    methods: {
      ...mapMutations({
        nextState: NEXT_TOUR_STATE, changeState: CHANGE_TOUR_STATE, updateState: UPDATE_TOUR_STATE
      }),
      ...mapActions({
        saveDashboard: SAVE_DASHBOARD_PANEL, changeDashboard: CHANGE_DASHBOARD_PANEL
      }),
      updateMetric (metric) {
        this.dashboard.metric = metric
        this.dashboard.config = null
        this.$nextTick(() => {
          if (!this.availableViews.includes(this.dashboardView)) {
            this.dashboardView = this.availableViews[0]
          }
        })
      },
      nameDashboard () {
        this.changeState({name: 'wizardSave'})
      },
      saveNewDashboard () {
        if (this.panel && this.panel.uuid) {
          return this.changeDashboard({
            uuid: this.panel.uuid,
            data: this.dashboard
          })
        }
        return this.saveDashboard({
          data: this.dashboard,
          space: this.space
        }).then(response => {
          if (response.status === 200 && response.data) {
            this.updateState({
              name: 'dashboardChart',
              id: response.data
            })
            this.$nextTick(this.nextWizardState)
          }
        })
      },
      finishNewDashboard () {
        this.$emit('close')
      },
      nextWizardState () {
        this.nextState('dashboardWizard')
      },
      updateView(view) {
        this.$refs.dashboardRef.updateView(view)
      },
    }
  }
</script>

<style lang="scss">
    .x-chart-wizard {
        display: grid;
        grid-template-columns: 160px auto;
        grid-gap: 16px 8px;

        .dashboard-view {
            display: flex;
            align-items: center;

            .type-label {
                cursor: pointer;
                margin-right: 24px;
                margin-bottom: 0;

                .svg-icon {
                    margin-left: 8px;

                    .svg-fill {
                        fill: $grey-4;
                    }

                    .svg-stroke {
                        stroke: $grey-4;
                    }
                }

                &:hover {
                    .svg-fill {
                        fill: $theme-black;
                    }
                }
            }

            input {
                cursor: pointer;
            }
        }

        .x-chart-metric {
            display: grid;
            grid-template-columns: 160px auto 20px;
            grid-gap: 16px 8px;
            min-width: 0;
        }

        .x-select {
            text-transform: capitalize;
        }

        .link {
            margin: auto;
        }
    }

</style>
