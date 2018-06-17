<template>
    <feedback-modal :launch="isActive" :handle-save="saveNewDashboard" :disabled="saveDisabled" approve-id="chart_save"
                    @change="finishNewDashboard" @enter="nextWizardState">
        <h3>Create a Dashboard Chart</h3>
        <div class="x-grid dashboard-wizard">
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

            <!-- Query rows -->
            <template v-if="dashboard.type === 'compare'">
                <h5 class="grid-span3">Select up to 5 queries for comparison:</h5>
                <template v-for="query, index in dashboard.views">
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

                <template v-for="query, index in dashboard.views.slice(1)">
                    <label>Intersecting Query:</label>
                    <x-select :options="views[parentQuery.module]" v-model="query.name" placeholder="query..."
                              size="md" :id="`child${index}`" @input="nextWizardState" />
                    <div @click="removeQuery(index)" class="link" v-if="index > 0">x</div>
                    <div v-else></div>
                </template>
            </template>
            <a @click="addQuery" class="x-btn light" :class="{disabled: isQueryMax}"
               :title="isQueryMax? `Limited to ${dashboard.views.length} queries` : ''">+</a>
            <div class="grid-span2"></div>

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

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_DATA_VIEWS } from '../../store/actions'
    import { SAVE_DASHBOARD } from '../../store/modules/dashboard'
    import { NEXT_TOUR_STATE, CHANGE_TOUR_STATE } from '../../store/modules/onboarding'

	const modules = ['devices', 'users']
	const dashboardQuery = { name: '', module: ''}

	export default {
		name: 'dashboard-wizard-container',
        components: { FeedbackModal, xSelectSymbol, xSelect },
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
				if (this.dashboard.type === 'compare') {
					return 5
                } else {
					return 3
                }
            },
            isQueryMax() {
				return this.dashboard.views.length === this.queryMax
            },
            parentQuery() {
				if (!this.dashboard.views || !this.dashboard.views.length) return ''
                return this.dashboard.views[0]
            },
            saveDisabled() {
                if (this.dashboards.charts.data.some(e => e.name === this.dashboard.name)) {
                    this.message = 'A Chart With That Name Already Exists, Please Choose A Different Name.'
                    return true
                }
				if (!this.dashboard.name || this.dashboard.views.length < 2) return true
				let complete = true
				this.dashboard.views.forEach((query, index) => {
					if (!index && this.dashboard.type === 'intersect') return
					if (!query.name) complete = false
				})
				return !complete
            }
        },
        data() {
			return {
                isActive: false,
				dashboard: {
					type: 'compare', name: '', views: [{ ...dashboardQuery }, { ...dashboardQuery }]
				},
                message: '',
                advanceState: false
			}
        },
        methods: {
            ...mapMutations({ nextState: NEXT_TOUR_STATE, changeState: CHANGE_TOUR_STATE }),
            ...mapActions({fetchView: FETCH_DATA_VIEWS, saveDashboard: SAVE_DASHBOARD}),
			activate() {
				this.isActive = true
                this.message = ''
            },
            changeType(event) {
				if (event.target.value === 'intersect') {
					this.dashboard.views.splice(0, 3)
					while (this.dashboard.views.length < 3) {
						this.dashboard.views.push({ ...dashboardQuery })
					}
					this.advanceState = true
				}
            },
            addQuery() {
            	if (this.isQueryMax) return
                this.dashboard.views.push({ ...dashboardQuery })
            },
            removeQuery(index) {
            	this.dashboard.views = this.dashboard.views.filter((item, i) => i !== index)
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
				this.dashboard = {
					type: 'compare', name: '', views: [{ ...dashboardQuery }, { ...dashboardQuery }]
				}
			},
            nextWizardState() {
            	this.nextState('dashboardWizard')
            },
            changeTourState(name) {
            	this.changeState({ name })
            }
        },
        created() {
			modules.forEach(module => this.fetchView({module, type: 'saved'}))
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
        grid-template-columns: 160px 360px 20px;
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