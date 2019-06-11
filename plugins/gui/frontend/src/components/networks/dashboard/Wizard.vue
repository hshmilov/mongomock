<template>
  <x-feedback-modal
    :launch="true"
    :handle-save="saveNewDashboard"
    :disabled="isDisabled"
    approve-id="chart_save"
    @change="finishNewDashboard"
    @enter="nextWizardState"
  >
    <h3>Create a Dashboard Chart</h3>
    <div class="x-chart-wizard">
      <!-- Select metric to be tested by chart -->
      <label>Chart metric</label>
      <x-select
        id="metric"
        v-model="dashboard.metric"
        :options="metricOptions"
        placeholder="by..."
        @input="advanceState = true"
      />
      <!-- Select method of presenting the data of the chart -->
      <template v-if="dashboard.metric">
        <label>Chart presentation</label>
        <div class="dashboard-view">
          <template v-for="view in availableViews">
            <input
              :id="view"
              :key="view"
              v-model="dashboard.view"
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
          :views="views"
          :entities="entityOptions"
          class="grid-span2"
          @state="nextWizardState"
          @validate="configValid = $event"
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

  import { mapState, mapMutations, mapActions } from 'vuex'
  import { SAVE_DASHBOARD_PANEL } from '../../../store/modules/dashboard'
  import { NEXT_TOUR_STATE, CHANGE_TOUR_STATE, UPDATE_TOUR_STATE } from '../../../store/modules/onboarding'

  const dashboard = {
    metric: '', view: '', name: '', config: {}
  }
  export default {
    name: 'XChartWizard',
    components: { xFeedbackModal, xSelect, intersect, compare, segment, abstract, timeline },
    mixins: [viewsMixin],
    props: {
      space: {
        type: String,
        required: true
      }
    },
    data () {
      return {
        dashboard: { ...dashboard },
        message: '',
        advanceState: false,
        configValid: false
      }
    },
    computed: {
      ...mapState({
        dashboards (state) {
          return state['dashboard']
        }
      }),
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
        if (!this.dashboard.name) return true
        if (this.dashboards.spaces.data.some(e => e.name === this.dashboard.name)) {
          this.message = 'A Chart With That Name Already Exists, Please Choose A Different Name.'
          return true
        }
        if (!this.dashboard.metric || !this.dashboard.view) return true
        return !this.configValid
      }
    },
    watch: {
      availableViews: {
        handler (newAvailableViews) {
          this.dashboard.view = newAvailableViews[0]
        },
        deep: true
      }
    },
    methods: {
      ...mapMutations({
        nextState: NEXT_TOUR_STATE, changeState: CHANGE_TOUR_STATE, updateState: UPDATE_TOUR_STATE
      }),
      ...mapActions({
        saveDashboard: SAVE_DASHBOARD_PANEL
      }),
      nameDashboard () {
        this.message = ''
        this.changeState({name: 'wizardSave'})
      },
      saveNewDashboard () {
        return this.saveDashboard({
          data: this.dashboard,
          space: this.space
        }).then(response => {
          if (response.status === 200 && response.data) {
            this.updateState({
              name: 'dashboardChart',
              id: this.dashboard.name.split(' ').join('_').toLowerCase()
            })
            this.advanceState = true
          }
        })
      },
      finishNewDashboard () {
        this.$emit('done')
      },
      nextWizardState () {
        this.nextState('dashboardWizard')
      }
    },
    updated () {
      if (this.advanceState) {
        this.nextWizardState()
        this.advanceState = false
      }
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