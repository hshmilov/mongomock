<template>
    <feedback-modal :launch="isActive" :handle-save="saveNewDashboard" :disabled="saveDisabled" approve-id="chart_save"
                    @change="finishNewDashboard" @enter="nextWizardState">
        <h3>Create a Dashboard Chart</h3>
        <div class="dashboard-wizard">
            <!-- Select metric to be tested by chart -->
            <label>Chart Metric</label>
            <x-select :options="metricOptions" v-model="dashboard.metric" placeholder="by..." id="metric"
                      @input="advanceState = true" />
            <!-- Select method of presenting the data of the chart -->
            <template v-if="dashboard.metric">
                <label>Chart Presentation</label>
                <div class="dashboard-view">
                    <template v-for="view in availableViews">
                        <input :id="view" type="radio" :value="view" v-model="dashboard.view" />
                        <label :for="view" class="type-label">
                            <svg-icon :name="`symbol/${view}`" :original="true" height="24"></svg-icon>
                        </label>
                    </template>
                </div>
                <component :is="dashboard.metric" v-model="dashboard.config" :views="views" :entities="entityOptions"
                           :fields="fields" class="grid-span2" @state="nextWizardState" @validate="configValid = $event" />
            </template>

            <!-- Last name to appear as a title above the chart -->
            <label for="chart_name">Chart Title</label>
            <input id="chart_name" type="text" v-model="dashboard.name" @input="nameDashboard">
            <div v-if="message" class="grid-span2 error-text">{{ message }}</div>
        </div>
    </feedback-modal>
</template>


<script>
    import FeedbackModal from '../../../components/popover/FeedbackModal.vue'
    import xSelect from '../../../components/inputs/Select.vue'

    import intersect from './ChartIntersect.vue'
    import compare from './ChartCompare.vue'
    import segment from './ChartSegment.vue'
    import abstract from './ChartAbstract.vue'
    import { entities } from '../../../constants/entities'

	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
    import { FETCH_DATA_VIEWS, FETCH_DATA_FIELDS } from '../../../store/actions'
    import { SAVE_DASHBOARD } from '../../../store/modules/dashboard'
    import { NEXT_TOUR_STATE, CHANGE_TOUR_STATE } from '../../../store/modules/onboarding'
    import { GET_DATA_FIELD_BY_PLUGIN } from '../../../store/getters'

	const dashboard = {
		metric: '', view: '', name: '', config: {}
	}
	export default {
		name: 'dashboard-wizard-container',
        components: { FeedbackModal, xSelect, intersect, compare, segment, abstract },
        props: {},
        computed: {
			...mapState({
				views (state) {
					return entities.reduce((map, module) => {
						map[module] = state[module].views.saved.data.map((view) => {
							return { name: view.name, title: view.name }
                        })
						return map
					}, {})
				},
                dashboards (state) {
                    return state['dashboard']
                }
			}),
			...mapGetters({ getDataFieldsByPlugin: GET_DATA_FIELD_BY_PLUGIN }),
            metricOptions() {
				return [
					{ name: 'intersect', title: 'Query Intersection' },
                    { name: 'compare', title: 'Query Comparison' },
					{ name: 'segment', title: 'Field Segmentation'},
                    { name: 'abstract', title: 'Field Summary' }
                ]
            },
			entityOptions() {
				return entities.map((module) => {
					return { name: module, title: module}
				})
			},
            fields () {
				return entities.reduce((map, module) => {
					map[module] = this.getDataFieldsByPlugin(module)
					return map
				}, {})
            },
            availableViews() {
				if (this.dashboard.metric === 'compare' || this.dashboard.metric === 'segment') {
					return ['histogram', 'pie']
				}
				if (this.dashboard.metric === 'intersect') {
					return ['pie']
                }
                return ['summary']
            },
            saveDisabled() {
				if (!this.dashboard.name) return true
				if (this.dashboards.charts.data.some(e => e.name === this.dashboard.name)) {
					this.message = 'A Chart With That Name Already Exists, Please Choose A Different Name.'
					return true
				}
				if (!this.dashboard.metric || !this.dashboard.view) return true
				return !this.configValid
            }
        },
        data() {
			return {
                isActive: false,
				dashboard: { ...dashboard },
                message: '',
                advanceState: false,
                configValid: false
			}
        },
        watch: {
			availableViews: {
				handler(newAvailableViews) {
                    this.dashboard.view = newAvailableViews[0]
                },
                deep: true
            }
        },
        methods: {
            ...mapMutations({ nextState: NEXT_TOUR_STATE, changeState: CHANGE_TOUR_STATE }),
            ...mapActions({
                fetchViews: FETCH_DATA_VIEWS, fetchFields: FETCH_DATA_FIELDS, saveDashboard: SAVE_DASHBOARD
            }),
			activate() {
				this.isActive = true
                this.message = ''
            },
            nameDashboard() {
				this.message = ''
				this.changeTourState('wizardSave')
            },
			saveNewDashboard () {
				return this.saveDashboard(this.dashboard)
			},
			finishNewDashboard () {
				this.isActive = false
				this.dashboard = { ...dashboard }
			},
            nextWizardState() {
            	this.nextState('dashboardWizard')
            },
            changeTourState(name) {
            	this.changeState({ name })
            }
        },
        created() {
			entities.forEach(module => {
				this.fetchViews({ module, type: 'saved' })
				this.fetchFields({ module })
			})
		},
        updated() {
			if (this.advanceState) {
				this.nextWizardState()
                this.advanceState = false
            }
        }
	}
</script>

<style lang="scss">
    .dashboard-wizard {
        display: grid;
        grid-template-columns: 160px 500px;
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
            grid-template-columns: 160px 480px 20px;
            grid-gap: 16px 8px;
        }
        .x-select {
            text-transform: capitalize;
        }
        .link {
            margin: auto;
        }
    }

</style>