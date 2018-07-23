<template>
    <feedback-modal :launch="isActive" :handle-save="saveNewDashboard" :disabled="saveDisabled" approve-id="chart_save"
                    @change="finishNewDashboard" @enter="nextWizardState">
        <h3>Create a Dashboard Chart</h3>
        <div class="x-grid dashboard-wizard">
            <label>Chart Metric</label>
            <x-select :options="[{name: 'query', title: 'Query'}, {name: 'field', title: 'Query Field'}]"
                      v-model="dashboard.metric" @input="onUpdateMetric" placeholder="by..." size="md" />
            <div></div>
            <!-- First row - select type -->
            <label>Chart Type</label>
            <div class="grid-span2 dashboard-types">
                <template v-for="type in chartTypes">
                    <input :id="type.value" type="radio" :value="type.value" v-model="dashboard.type" @change="changeType"/>
                    <label :for="type.value" class="type-label">
                        <svg-icon :name="`symbol/${type.name}`" :original="true" height="24"></svg-icon>
                    </label>
                </template>
            </div>

            <template v-if="isQueryChart">
                <!-- Query rows for query chart -->
                <template v-if="dashboard.type === 'compare'">
                    <h5 class="grid-span3">Select up to 5 queries for comparison:</h5>
                    <template v-for="query, index in dashboard.config.views">
                        <x-select-symbol :options="moduleOptions" v-model="query.module" type="icon" placeholder="module..."/>
                        <x-select :options="views[query.module] || []" v-model="query.name" placeholder="query..." size="md"/>
                        <div @click="removeQuery(index)" class="link" v-if="index > 1">x</div>
                        <div v-else></div>
                    </template>
                </template>
                <template v-else-if="dashboard.type === 'intersect'">
                    <label>Module for chart:</label>
                    <x-select-symbol :options="moduleOptions" v-model="parentQuery.module" type="icon"
                                     placeholder="module..." id="module" @input="nextWizardState" />
                    <div></div>

                    <label>Main Query:</label>
                    <x-select :options="views[parentQuery.module]" v-model="parentQuery.name"
                              placeholder="query (or empty for all)" size="md" id="parent" />
                    <div></div>

                    <template v-for="query, index in dashboard.config.views.slice(1)">
                        <label>Intersecting Query:</label>
                        <x-select :options="views[parentQuery.module]" v-model="query.name" placeholder="query..."
                                  size="md" :id="`child${index}`" @input="nextWizardState" />
                        <div @click="removeQuery(index)" class="link" v-if="index > 0">x</div>
                        <div v-else></div>
                    </template>
                </template>
                <a @click="addQuery" class="x-btn light" :class="{disabled: isQueryMax}"
                   :title="isQueryMax? `Limited to ${dashboard.config.views.length} queries` : ''">+</a>
                <div class="grid-span2"></div>
            </template>
            <template v-else >
                <x-select-symbol :options="moduleOptions" v-model="dashboard.config.module" type="icon" placeholder="module..."/>
                <x-select :options="views[dashboard.config.module] || []" v-model="dashboard.config.view"
                          placeholder="query..." size="md" class="grid-span" />
                <div></div><div></div>
                <x-select-typed-field :fields="fields[dashboard.config.module]" v-model="dashboard.config.field" class="grid-span" />
                <div></div>
            </template>

            <!-- Last Row - select name -->
            <label for="chart_name">Chart Title</label>
            <input id="chart_name" type="text" v-model="dashboard.name" @input="nameDashboard">
            <div></div> <!-- Empty to align with query lines -->
            <div v-if="message" class="grid-span2 error-text">{{ message }}</div>
        </div>
    </feedback-modal>
</template>


<script>
    import FeedbackModal from '../../components/popover/FeedbackModal.vue'
    import xSelectSymbol from '../../components/inputs/SelectSymbol.vue'
    import xSelect from '../../components/inputs/Select.vue'
    import xSelectTypedField from '../../components/inputs/SelectTypedField.vue'

	import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
    import { FETCH_DATA_VIEWS, FETCH_DATA_FIELDS } from '../../store/actions'
    import { SAVE_DASHBOARD } from '../../store/modules/dashboard'
    import { NEXT_TOUR_STATE, CHANGE_TOUR_STATE } from '../../store/modules/onboarding'
    import { GET_DATA_FIELD_BY_PLUGIN } from '../../store/getters'

	const modules = ['devices', 'users']
	const dashboardQuery = { name: '', module: ''}
	const dashboard = {
		metric: 'query', type: 'compare', name: '', config: {}
	}

	export default {
		name: 'dashboard-wizard-container',
        components: { FeedbackModal, xSelectSymbol, xSelect, xSelectTypedField },
        props: {},
        computed: {
			...mapState({
				views (state) {
					return modules.reduce((map, module) => {
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
            fields () {
				return modules.reduce((map, module) => {
					map[module] = this.getDataFieldsByPlugin(module)
					return map
				}, {})
            },
            isQueryChart() {
				return this.dashboard.metric === 'query'
            },
            chartTypes() {
				return [{ value: 'compare', name: 'histogram' },
                    { value: 'intersect', name: 'pie' }]
            },
            moduleOptions() {
				return modules.map((module) => {
					return { name: module, title: module}
                })
            },
            queryMax() {
				return (this.dashboard.type === 'compare') ? 5 : 3
            },
            isQueryMax() {
				return this.dashboard.config.views.length === this.queryMax
            },
            parentQuery() {
				if (!this.dashboard.config.views || !this.dashboard.config.views.length) return ''
                return this.dashboard.config.views[0]
            },
            saveDisabled() {
                if (this.dashboards.charts.data.some(e => e.name === this.dashboard.name)) {
                    this.message = 'A Chart With That Name Already Exists, Please Choose A Different Name.'
                    return true
                }
				if (!this.dashboard.name) return true
				let complete = true
                if (this.isQueryChart) {
                	if (this.dashboard.config.views.length < 2) return true
                    this.dashboard.config.views.forEach((query, index) => {
                        if (!index && this.dashboard.type === 'intersect') return
                        if (!query.name) complete = false
                    })
                }
				return !complete
            }
        },
        data() {
			return {
                isActive: false,
				dashboard: { ...dashboard, config: this.getQueryChartConfig() },
                message: '',
                advanceState: false
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
            getQueryChartConfig() {
            	return { views: [{ ...dashboardQuery }, { ...dashboardQuery }]}
            },
            getFieldChartConfig() {
				return { module: '', view: '', field: '' }
            },
            onUpdateMetric() {
            	if (this.isQueryChart) {
            		this.dashboard.config = this.getQueryChartConfig()
                } else {
					this.dashboard.config = this.getFieldChartConfig()
				}
            },
            changeType(event) {
            	if (!this.isQueryChart) return
				if (event.target.value === 'intersect') {
					this.dashboard.config.views.splice(0, 3)
					while (this.dashboard.config.views.length < 3) {
						this.dashboard.config.views.push({ name: '',  module: '' })
					}
					this.advanceState = true
				}
            },
            addQuery() {
            	if (this.isQueryMax) return
                this.dashboard.config.views.push({ name: '',  module: '' })
            },
            removeQuery(index) {
            	this.dashboard.config.views = this.dashboard.config.views.filter((item, i) => i !== index)
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
				this.dashboard = { ...dashboard, config: this.getQueryChartConfig() }
			},
            nextWizardState() {
            	this.nextState('dashboardWizard')
            },
            changeTourState(name) {
            	this.changeState({ name })
            }
        },
        created() {
			modules.forEach(module => {
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
        grid-template-columns: 160px 480px 20px;
        grid-column-gap: 8px;
        .dashboard-types {
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
        .x-select {
            text-transform: capitalize;
        }
        .link {
            margin: auto;
        }
    }

</style>