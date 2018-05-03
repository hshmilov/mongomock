<template>
    <x-page title="axonius dashboard" class="dashboard">
        <div slot="action">
            <a class="x-btn link" @click="exportPDF">Export PDF</a>
        </div>
        <div class="dashboard-charts">
            <x-coverage-card v-for="item in dashboard.coverage.data" :key="item.title"
                             :portion="item.portion" :title="item.title" :description="item.description"
                             @click-one="runCoverageFilter(item.properties, $event)" />
            <x-card title="Data Discovery">
                <x-counter-chart :data="adapterDevicesCounterData"/>
            </x-card>
            <x-card title="Devices per Adapter">
                <x-histogram-chart :data="adapterDevicesCount" @click-one="runAdapterFilter" :sort="true" type="logo"/>
            </x-card>
            <x-card v-for="chart, chartInd in dashboard.charts.data" v-if="chart.data" :key="chart.name"
                    :title="chart.name" :removable="true" @remove="removeDashboard(chart.uuid)">
                <components :is="chart.type" :data="chart.data" @click-one="runChartFilter(chartInd, $event)" />
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
        <dashboard-wizard-container ref="wizard" />
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

	import {
		FETCH_LIFECYCLE, FETCH_ADAPTER_DEVICES, FETCH_DASHBOARD_COVERAGE,
        FETCH_DASHBOARD, REMOVE_DASHBOARD
	} from '../../store/modules/dashboard'
    import { UPDATE_DATA_VIEW } from '../../store/mutations'

	import { mapState, mapMutations, mapActions } from 'vuex'

	export default {
		name: 'x-dashboard',
		components: {
			xPage, xCard, xCoverageCard, xCounterChart, xHistogramChart,
            compare, intersect, xCycleChart, DashboardWizardContainer
		},
		computed: {
			...mapState({
				dashboard (state) {
					return state['dashboard']
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
		methods: {
			...mapMutations({updateView: UPDATE_DATA_VIEW}),
			...mapActions({
				fetchLifecycle: FETCH_LIFECYCLE, fetchAdapterDevices: FETCH_ADAPTER_DEVICES,
				fetchDashboard: FETCH_DASHBOARD, removeDashboard: REMOVE_DASHBOARD,
				fetchDashboardCoverage: FETCH_DASHBOARD_COVERAGE
			}),
			getDashboardData () {
				this.fetchAdapterDevices()
				this.fetchDashboard()
                this.fetchDashboardCoverage()
			},
			runAdapterFilter (index) {
				this.runFilter(`adapters == '${this.adapterDevicesCount[index].name}'`, 'device')
			},
            runCoverageFilter(properties, covered) {
				if (!properties || !properties.length) return
                if (covered) {
                    this.runFilter(`specific_data.adapter_properties in ['${properties.join("','")}']`, 'device')
                } else {
					this.runFilter(properties.map((property) => {
						return `specific_data.adapter_properties != '${property}'`
                    }).join(' and '), 'device')
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
				this.$router.push({path: module})
            },
            createNewDashboard() {
				if (!this.$refs.wizard) return
                this.$refs.wizard.activate()
            },
            exportPDF() {
				window.print()
            }
		},
		created () {
			this.getDashboardData()
			this.interval = setInterval(function () {
				this.getDashboardData()
			}.bind(this), 10000)
		},
		beforeDestroy () {
			clearInterval(this.interval)
		}
	}
</script>


<style lang="scss">

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