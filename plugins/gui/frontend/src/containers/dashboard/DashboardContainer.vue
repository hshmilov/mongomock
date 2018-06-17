<template>
    <x-page title="axonius dashboard">
        <template v-if="isEmptySystem === null">

        </template>
        <template v-else-if="isEmptySystem">
            <x-empty-system />
        </template>
        <template v-else>
            <div class="dashboard-charts">
                <x-coverage-card v-for="item in dashboard.coverage.data" :key="item.title" :data="item"
                                 @click-one="runCoverageFilter(item.properties, $event)" />
                <x-card title="Data Discovery">
                    <x-counter-chart :data="adapterDevicesCounterData"/>
                </x-card>
                <x-card title="Devices per Adapter">
                    <x-histogram-chart :data="adapterDevicesCount" @click-one="runAdapterFilter" type="logo"/>
                </x-card>
                <x-card v-for="chart, chartInd in charts" v-if="chart.data" :key="chart.name" :title="chart.name"
                        :removable="true" @remove="removeDashboard(chart.uuid)" :id="getId(chart.name)">
                    <components :is="chart.type" :data="chart.data" @click-one="runChartFilter(chartInd, $event)" />
                </x-card>
                <x-card title="System Lifecycle" class="chart-lifecycle print-exclude">
                    <x-cycle-chart :data="lifecycle.subPhases"/>
                    <div class="cycle-time">Next cycle starts in
                        <div class="blue">{{ nextRunTime }}</div>
                    </div>
                </x-card>
                <x-card title="New Chart" class="chart-new print-exclude">
                    <div class="link" @click="createNewDashboard" id="dashboard_wizard">+</div>
                </x-card>
            </div>
            <dashboard-wizard-container ref="wizard" />
        </template>
    </x-page>
</template>


<script>
	import xPage from '../../components/layout/Page.vue'
	import xCard from '../../components/cards/Card.vue'
    import xCoverageCard from '../../components/cards/CoverageCard.vue'
	import xCounterChart from '../../components/charts/Counter.vue'
	import xHistogramChart from '../../components/charts/Histogram.vue'
    import compare from '../../components/charts/customized/Compare.vue'
    import intersect from '../../components/charts/customized/Intersect.vue'
	import xCycleChart from '../../components/charts/Cycle.vue'
    import DashboardWizardContainer from './DashboardWizardContainer.vue'
    import xEmptySystem from '../../components/onboard/empty_states/EmptySystem.vue'

	import {
		FETCH_ADAPTER_DEVICES, FETCH_DASHBOARD_COVERAGE, FETCH_DASHBOARD, REMOVE_DASHBOARD
	} from '../../store/modules/dashboard'
    import { FETCH_ADAPTERS } from '../../store/modules/adapter'
	import { CLEAR_DATA_CONTENT, UPDATE_DATA_VIEW } from '../../store/mutations'
    import { SAVE_VIEW } from '../../store/actions'
	import { CHANGE_TOUR_STATE, NEXT_TOUR_STATE } from '../../store/modules/onboarding'
	import { mapState, mapMutations, mapActions } from 'vuex'

	export default {
		name: 'x-dashboard',
		components: {
			xPage, xCard, xCoverageCard, xCounterChart, xHistogramChart,
            compare, intersect, xCycleChart, DashboardWizardContainer, xEmptySystem
		},
		computed: {
			...mapState({
				dashboard (state) {
					return state.dashboard
				},
                charts (state) {
					return state.dashboard.charts.data
                },
                adapterList(state) {
					return state.adapter.adapterList.data
                },
                devicesView(state) {
					return state.devices.view
                }
			}),
			lifecycle () {
				if (!this.dashboard.lifecycle.data) return {}
				return this.dashboard.lifecycle.data
			},
			adapterDevices () {
				if (!this.dashboard.adapterDevices.data) return {}
				return this.dashboard.adapterDevices.data
			},
			adapterDevicesCount () {
				if (!this.adapterDevices || !this.adapterDevices.adapter_count) return []
				return this.adapterDevices.adapter_count.sort((first, second) => second.count - first.count)
			},
			adapterDevicesCounterData () {
				let totalSeen = this.adapterDevices.total_gross || 0
				return [
					{count: totalSeen, title: 'Seen Devices', highlight: true},
					{count: Math.min(this.adapterDevices.total_net || 0, totalSeen), title: 'Unique Devices'},
				]
			},
			nextRunTime () {
				let leftToRun = new Date(parseInt(this.lifecycle.nextRunTime) * 1000) - Date.now()
				let thresholds = [1000, 60 * 1000, 60 * 60 * 1000, 24 * 60 * 60 * 1000]
				let units = ['seconds', 'minutes', 'hours', 'days']
				for (let i = 1; i < thresholds.length; i++) {
					if (leftToRun < thresholds[i]) {
						return `${Math.round(leftToRun / thresholds[i - 1])} ${units[i - 1]}`
					}
				}
				return `${Math.round(leftToRun / thresholds[thresholds.length])} ${units[units.length]}`
			},
            isEmptySystem() {
				if (!this.adapterDevicesCount || !this.adapterList.length) return null

				if (this.adapterDevicesCount.length || this.adapterList.some(item => item.status !== '')) {
					return false
				}

                return true
            }
		},
        data() {
			return {
				newChart: '',
				wizardActivated: false
            }
        },
        watch: {
			adapterDevicesCount(newCount) {
				if (newCount.length) {
                    let adapter = newCount.find((item) => !item.name.includes('active_directory'))
                    let name = ''
                    let filter = ''
                    if (adapter) {
                    	name = adapter.name.split('_').join(' ')
                        filter = `adapters == '${adapter.name}'`
                    } else {
                        name = 'Windows 10'
                        filter = 'specific_data.data.os.distribution == "10"'
                    }
                    this.saveView({
                        name: `DEMO - ${name}`, module: 'devices', view: {
                            ...this.devicesView, query: { filter }
                        }
                    })
                }
            },
            charts(newCharts, oldCharts) {
				if (oldCharts && !oldCharts.length && newCharts && newCharts.length === 1) {
					this.newChart = this.getId(newCharts[0].name)
                }
            }
        },
		methods: {
			...mapMutations({
                updateView: UPDATE_DATA_VIEW, clearDataContent: CLEAR_DATA_CONTENT,
                changeState: CHANGE_TOUR_STATE, nextState: NEXT_TOUR_STATE
			}),
			...mapActions({
				fetchAdapterDevices: FETCH_ADAPTER_DEVICES, fetchDashboardCoverage: FETCH_DASHBOARD_COVERAGE,
                fetchDashboard: FETCH_DASHBOARD, removeDashboard: REMOVE_DASHBOARD, fetchAdapters: FETCH_ADAPTERS,
                saveView: SAVE_VIEW
			}),
			runAdapterFilter (index) {
				this.runFilter(`adapters == '${this.adapterDevicesCount[index].name}'`, 'devices')
			},
            runCoverageFilter(properties, covered) {
				if (!properties || !properties.length) return
                if (covered) {
                    this.runFilter(`specific_data.adapter_properties in ['${properties.join("','")}']`, 'devices')
                } else {
					this.runFilter(properties.map((property) => {
						return `specific_data.adapter_properties != '${property}'`
                    }).join(' and '), 'devices')
                }
            },
            runChartFilter(chartInd, queryInd) {
				let query = this.dashboard.charts.data[chartInd].data[queryInd]
				if (!query.filter) return
				this.runFilter(query.filter, query.module)
            },
            runFilter(filter, module) {
				this.updateView({module, view: {
						page: 0, query: { filter, expressions: [] }
					}})
                this.clearDataContent({module})
				this.$router.push({path: module})
            },
            createNewDashboard() {
				if (!this.$refs.wizard) return
                this.wizardActivated = true
                this.$refs.wizard.activate()
            },
            getId(name) {
				return name.split(' ').join('_').toLowerCase()
            }
		},
		created () {
			this.fetchAdapters()
			const getDashboardData = () => {
            	return Promise.all([this.fetchAdapterDevices(), this.fetchDashboard(), this.fetchDashboardCoverage()])
                    .then(() => this.timer = setTimeout(getDashboardData, 10000))
            }
            getDashboardData().then(() => this.nextState('dashboard'))
		},
        updated() {
			if (this.wizardActivated && this.newChart) {
                this.changeState({ name: 'dashboardChart', id: this.newChart })
                this.newChart = ''
            }
        },
        beforeDestroy() {
			clearTimeout(this.timer)
        }
	}
</script>


<style lang="scss">

    .dashboard-charts {
        display: grid;
        grid-template-columns: repeat(auto-fill, 344px);
        grid-gap: 12px;
        width: 100%;
        .x-card {
            width: 320px;
            height: 320px;
        }
        .chart-lifecycle {
            display: flex;
            flex-direction: column;
            .cycle {
                flex: 100%;
            }
            .cycle-time {
                font-size: 12px;
                text-align: right;
                .blue {
                    display: inline-block;
                }
            }
        }
        .chart-new {
            .link {
                font-size: 144px;
                text-align: center;
            }
        }
    }
</style>