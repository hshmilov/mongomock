<template>
    <x-page title="axonius dashboard" class="dashboard">
        <div slot="action">
            <a class="x-btn link" @click="exportPDF">Export PDF</a>
        </div>
        <div class="dashboard-charts">
            <x-coverage-card v-for="item in dashboard.coverage.data" :key="item.title"
                             :portion="item.portion" :title="item.title" :description="item.description"
                             @click-slice="runCoverageFilter(item.properties, $event)" />
            <x-card title="Data Discovery">
                <x-counter-chart :data="adapterDevicesCounterData"/>
            </x-card>
            <x-card title="Devices per Adapter">
                <x-histogram-chart :data="adapterDevicesCount" @click-bar="runAdapterDevicesFilter"/>
            </x-card>
            <x-card v-for="chart in dashboard.charts.data" :title="chart.name" :key="chart.name" v-if="chart.data"
                    :removable="true" @remove="removeDashboard(chart.uuid)">
                <x-results-chart :data="chart.data"/>
            </x-card>
            <x-card title="System Lifecycle" class="chart-lifecycle print-exclude">
                <x-cycle-chart :data="lifecycle.subPhases"/>
                <div class="cycle-time">Next cycle starts in
                    <div class="blue">{{ nextRunTime }}</div>
                </div>
            </x-card>
            <x-card title="New Chart" class="chart-new print-exclude">
                <div class="link" @click="createNewDashboard">+</div>
            </x-card>
        </div>
        <feedback-modal :launch="newDashboard.isActive" :handle-save="saveNewDashboard" @change="finishNewDashboard">
            <h3>Create a Dashboard Chart</h3>
            <div class="x-grid x-grid-col-2">
                <label>Chart Title</label>
                <input type="text" v-model="newDashboard.data.name" />
                <template v-for="module in Object.keys(newDashboard.data.queries)">
                    <label>{{module}} Queries</label>
                    <vm-select v-model="newDashboard.data.queries[module]" multiple filterable
                               no-data-text="No saved queries" placeholder="Select queries...">
                        <vm-option v-for="query in queries[module]" :key="query.name" :value="query.name" :label="query.name"/>
                    </vm-select>
                </template>
            </div>
        </feedback-modal>
    </x-page>
</template>


<script>
	import xPage from '../../components/layout/Page.vue'
	import xCard from '../../components/cards/Card.vue'
	import FeedbackModal from '../../components/popover/FeedbackModal.vue'

	import xCounterChart from '../../components/charts/Counter.vue'
	import xHistogramChart from '../../components/charts/Histogram.vue'
	import xCycleChart from '../../components/charts/Cycle.vue'
	import xResultsChart from '../../components/charts/Results.vue'
    import xCoverageCard from '../../components/cards/CoverageCard.vue'

	import {
		FETCH_LIFECYCLE, FETCH_ADAPTER_DEVICES, FETCH_DASHBOARD_COVERAGE,
        FETCH_DASHBOARD, SAVE_DASHBOARD, REMOVE_DASHBOARD
	} from '../../store/modules/dashboard'
	import { FETCH_DATA_QUERIES } from '../../store/actions'
    import { UPDATE_DATA_VIEW } from '../../store/mutations'

	import { mapState, mapMutations, mapActions } from 'vuex'

    const newDashboardData = {
		name: '', queries: {device: [], user: []}
	}

	export default {
		name: 'x-dashboard',
		components: {
			xPage, xCard, FeedbackModal,
			xCounterChart, xHistogramChart, xCycleChart, xResultsChart, xCoverageCard
		},
		computed: {
			...mapState({
				dashboard (state) {
					return state['dashboard']
				},
				queries (state) {
					return Object.keys(this.newDashboard.data.queries).reduce((map, module) => {
						map[module] = state[module].queries.saved.data
                        return map
                    }, {})
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
				return this.adapterDevices.adapter_count
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
			}
		},
		data () {
			return {
				newDashboard: {
					isActive: false,
					data: { ...newDashboardData }
				},
			}
		},
		methods: {
			...mapMutations({updateView: UPDATE_DATA_VIEW}),
			...mapActions({
				fetchLifecycle: FETCH_LIFECYCLE, fetchAdapterDevices: FETCH_ADAPTER_DEVICES,
				fetchDashboard: FETCH_DASHBOARD, saveDashboard: SAVE_DASHBOARD, removeDashboard: REMOVE_DASHBOARD,
				fetchQueries: FETCH_DATA_QUERIES, fetchDashboardCoverage: FETCH_DASHBOARD_COVERAGE
			}),
			getDashboardData () {
				this.fetchAdapterDevices()
				this.fetchDashboard()
                this.fetchDashboardCoverage()
			},
			runAdapterDevicesFilter (adapterName) {
				this.runFilter(`adapters == '${adapterName}'`)
			},
            runCoverageFilter(properties, covered) {
				if (!properties || !properties.length) return
                if (covered) {
                    this.runFilter(`specific_data.adapter_properties in ['${properties.join("','")}']`)
                } else {
					this.runFilter(properties.map((property) => {
						return `specific_data.adapter_properties != '${property}'`
                    }).join(' and '))
                }
            },
			createNewDashboard () {
				this.newDashboard.isActive = true
			},
			saveNewDashboard () {
				return this.saveDashboard(this.newDashboard.data)
			},
			finishNewDashboard () {
				this.newDashboard.isActive = false
				this.newDashboard.data = { ...newDashboardData }
			},
            runFilter(filter) {
				this.updateView({module: 'device', view: {
						page: 0, query: { filter, expressions: [] }
					}})
				this.$router.push({name: 'Devices'})
            },
            exportPDF() {
				window.print()
            }
		},
		created () {
			this.fetchQueries({module: 'device', type: 'saved'})
			this.fetchQueries({module: 'user', type: 'saved'})

			this.getDashboardData()
			this.intervals = []
			this.intervals.push(setInterval(function () {
				this.fetchDashboard()
			}.bind(this), 1000))
			this.intervals.push(setInterval(function () {
				this.fetchAdapterDevices()
			}.bind(this), 10000))
			this.intervals.push(setInterval(function () {
				this.fetchDashboardCoverage()
			}.bind(this), 10000))
		},
		beforeDestroy () {
			this.intervals.forEach(interval => clearInterval(interval))
		}
	}
</script>


<style lang="scss">

    .dashboard {
        .modal-body {
            h3 {
                margin-bottom: 24px;
            }
            .vm-select {
                .vm-select-input__inner {
                    width: 100%;
                }
            }
            .x-grid {
                grid-template-columns: 1fr 2fr;
            }
        }
    }
    .dashboard-charts {
        display: grid;
        grid-template-columns: repeat(auto-fill, 320px);
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