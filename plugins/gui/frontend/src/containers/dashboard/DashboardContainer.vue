<template>
    <x-page title="axonius dashboard">
        <template v-if="isEmptySystem === null"></template>
        <template v-else-if="isEmptySystem">
            <x-empty-system/>
        </template>
        <template v-else>
            <x-insights-search @click="onClickInsights" />
            <div class="dashboard-charts">
                <x-data-discovery-card :data="deviceDiscovery" module="devices"
                                       :filter="isDevicesRestricted? undefined: runFilter" />
                <x-data-discovery-card :data="dashboard.dataDiscovery.users.data" module="users"
                                       :filter="isUsersRestricted? undefined: runFilter" />
                <x-coverage-card v-for="item in dashboard.coverage.data" v-if="item.portion" :key="item.title" :data="item"
                                 @click-one="runCoverageFilter(item.properties, $event)" :read-only="isDevicesRestricted"/>
                <x-card v-for="(chart, chartInd) in charts" v-if="chart.data" :key="chart.name" :title="chart.name"
                        :removable="!isReadOnly" @remove="removeDashboard(chart.uuid)" :id="getId(chart.name)">
                    <div class="card-history" v-if="chart.metric !== 'timeline'">
                        <x-historical-date-picker v-model="chartsCurrentlyShowing[chart.uuid]"
                                                  @input="confirmPickDate(chart.uuid, chart.name)"
                                                  @clear="clearDate(chart.uuid)" :minimal="true">
                        </x-historical-date-picker>
                    </div>
                    <components :is="`x-${chart.view}`" :data="chart.data" @click-one="runChartFilter(chartInd, $event)" />
                </x-card>
                <x-card title="System Lifecycle" class="chart-lifecycle print-exclude">
                    <x-cycle-chart :data="lifecycle.subPhases"/>
                    <div class="cycle-time">Next cycle starts in <div class="blue">{{ nextRunTime }}</div>
                    </div>
                </x-card>
                <x-card title="New Chart" class="chart-new print-exclude">
                    <div class="x-btn link" :class="{disabled: isReadOnly}" @click="createNewDashboard" id="dashboard_wizard">+</div>
                </x-card>
            </div>
            <dashboard-wizard-container ref="wizard" />
        </template>
        <x-toast v-if="message" :message="message" @done="removeToast"/>
    </x-page>
</template>


<script>
    import xPage from '../../components/layout/Page.vue'
    import xCard from '../../components/cards/Card.vue'
    import xCoverageCard from '../../components/cards/CoverageCard.vue'
	import xDataDiscoveryCard from '../../components/cards/DataDiscoveryCard.vue'
    import xHistogram from '../../components/charts/Histogram.vue'
    import xPie from '../../components/charts/Pie.vue'
    import xSummary from '../../components/charts/Summary.vue'
    import xLine from '../../components/charts/Line.vue'
    import xCycleChart from '../../components/charts/Cycle.vue'
    import DashboardWizardContainer from './wizard/DashboardWizardContainer.vue'
    import xEmptySystem from '../../components/onboard/empty_states/EmptySystem.vue'
    import Modal from '../../components/popover/Modal.vue'
    import xToast from '../../components/popover/Toast.vue'
    import xInsightsSearch from './explorer/ExplorerSearch.vue'
    import xHistoricalDatePicker from '../../components/inputs/HistoricalDatePicker.vue'

    import {
        FETCH_DISCOVERY_DATA, FETCH_DASHBOARD_COVERAGE, FETCH_DASHBOARD, REMOVE_DASHBOARD,
        FETCH_HISTORICAL_SAVED_CARD, FETCH_HISTORICAL_SAVED_CARD_MIN, FETCH_DASHBOARD_FIRST_USE
    } from '../../store/modules/dashboard'
    import { UPDATE_DATA_VIEW } from '../../store/mutations'
    import { SAVE_VIEW } from '../../store/actions'
    import { CHANGE_TOUR_STATE, NEXT_TOUR_STATE } from '../../store/modules/onboarding'
    import { mapState, mapMutations, mapActions } from 'vuex'

    export default {
        name: 'x-dashboard',
        components: {
            xPage, xCard, xCoverageCard, xDataDiscoveryCard, xHistogram, xPie, xSummary, xLine,
            xCycleChart, DashboardWizardContainer, xEmptySystem, Modal, xToast, xInsightsSearch, xHistoricalDatePicker
        },
        computed: {
            ...mapState({
                dashboard(state) {
                    return state.dashboard
                },
                charts(state) {
                    return state.dashboard.charts.data.map(chart => {
                        if (chart.metric === 'timeline') return chart
                    	return {
                            ...chart, showingHistorical: this.dateChosen[chart.uuid],
                            data: chart.data.map(item => {
                                var historical_card = this.cardHistoricalData[chart.uuid]
								if (historical_card) {
                                    var historical_card_view = historical_card[item.name]
									if (!historical_card_view) return null
									return { ...item,
                                        value: historical_card[item.name].value,
                                        showingHistorical: historical_card[item.name].accurate_for_datetime
                                    }
								}
								return item
                            }).filter(x => x)
                        }
                    })
                },
                devicesView(state) {
					return state.devices.view
                },
                devicesViewsList(state) {
					return state.devices.views.saved.data
                },
                dashboardFirstUse(state) {
                    return state.dashboard.firstUse.data
                },
                isReadOnly(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Dashboard === 'ReadOnly'
                },
                isDevicesEdit(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Devices === 'ReadWrite' || user.admin
                },
                isDevicesRestricted(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Devices === 'Restricted'
                },
                isUsersRestricted(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Users === 'Restricted'
                }
            }),
            lifecycle() {
                if (!this.dashboard.lifecycle.data) return {}
                return this.dashboard.lifecycle.data
            },
            deviceDiscovery() {
            	return this.dashboard.dataDiscovery.devices.data
            },
            seenDevices() {
            	return (this.deviceDiscovery && this.deviceDiscovery.seen)
            },
            nextRunTime() {
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
                if (this.deviceDiscovery.seen === undefined) return null

                if (this.seenDevices || !this.dashboardFirstUse) {
                    return false
                }
                return true
            }

        },
        data() {
            return {
                newChart: '',
                wizardActivated: false,
                dateChosen: {},
                pendingDateChosen: null,
                cardHistoricalData: {},
                chartsCurrentlyShowing: {},
                message: ''
            }
        },
        watch: {
            charts(newCharts, oldCharts) {
                if (newCharts && newCharts.length && (!oldCharts || oldCharts.length < newCharts.length)) {
                    this.newChart = this.getId(newCharts[newCharts.length - 1].name)
                }
            }
        },
        methods: {
            ...mapMutations({
                updateView: UPDATE_DATA_VIEW, changeState: CHANGE_TOUR_STATE, nextState: NEXT_TOUR_STATE
            }),
            ...mapActions({
                fetchDiscoveryData: FETCH_DISCOVERY_DATA, fetchDashboardCoverage: FETCH_DASHBOARD_COVERAGE,
                fetchDashboardFirstUse: FETCH_DASHBOARD_FIRST_USE, saveView: SAVE_VIEW,
                fetchDashboard: FETCH_DASHBOARD, removeDashboard: REMOVE_DASHBOARD,
                fetchHistoricalCard: FETCH_HISTORICAL_SAVED_CARD
            }),
            runCoverageFilter(properties, covered) {
                if (!properties || !properties.length) return
                if (covered === 2) {
                    this.runFilter(`specific_data.adapter_properties in ['${properties.join("','")}']`, 'devices')
                } else {
                    this.runFilter(properties.map((property) => {
                        return `specific_data.adapter_properties != '${property}'`
                    }).join(' and '), 'devices')
                }
            },
            runChartFilter(chartInd, queryInd) {
                let query = this.dashboard.charts.data[chartInd].data[queryInd]
                if ((query.module === 'devices' && this.isDevicesRestricted)
                    || (query.module === 'users' && this.isUsersRestricted)) {
                    return
                }
                if (query.view === undefined || query.view === null
                    || query.module === undefined || query.module === null) return
				this.updateView({
					module: query.module, view: query.view
				})
				this.$router.push({path: query.module})
            },
            runFilter(filter, module) {
                this.updateView({
                    module, view: {
                        page: 0, query: {filter, expressions: []}
                    }
                })
                this.$router.push({path: module})
            },
            createNewDashboard() {
                if (!this.$refs.wizard || this.isReadOnly) return
                this.wizardActivated = true
                this.$refs.wizard.activate()
            },
            getId(name) {
                return name.split(' ').join('_').toLowerCase()
            },
            clearDate(cardUuid) {
                this.dateChosen = {...this.dateChosen, [cardUuid]: null}
                this.cardHistoricalData = {...this.cardHistoricalData, [cardUuid]: null}
                this.chartsCurrentlyShowing[cardUuid] = undefined
            },
            confirmPickDate(cardUuid, cardName) {
                let pendingDateChosen = this.chartsCurrentlyShowing[cardUuid]
                if (!pendingDateChosen) {
                    this.clearDate(cardUuid)
                    return
                }
                this.fetchHistoricalCard({
                    cardUuid: cardUuid,
                    date: pendingDateChosen
                }).then(response => {
                    if (_.isEmpty(response.data)) {
                        this.message = `Can't gather any data from ${pendingDateChosen} for '${cardName}'`
                        this.clearDate(cardUuid)
                    } else {
                        this.dateChosen = {...this.dateChosen, [cardUuid]: pendingDateChosen}
                        this.cardHistoricalData = {...this.cardHistoricalData, [cardUuid]: response.data}
                    }
                })
            },
            removeToast() {
                this.message = ''
            },
            onClickInsights() {
                this.$router.push({name: 'Insights Explorer'})
            }
        },
        created() {
            this.fetchDashboardFirstUse()
            const getDashboardData = () => {
                return Promise.all([
                	this.fetchDiscoveryData({module: 'devices'}), this.fetchDiscoveryData({module: 'users'}),
                    this.fetchDashboard(), this.fetchDashboardCoverage()
                ]).then(() => {
                    if (this._isDestroyed) return
                    this.timer = setTimeout(getDashboardData, 10000)
                })
            }
            getDashboardData().then(() => {
                if (this._isDestroyed) return
            	if (!this.isEmptySystem) this.nextState('dashboard')
                if (this.devicesViewsList && this.devicesViewsList.find((item) => item.name.includes('DEMO'))) return
                // If DEMO view was not yet added, add it now, according to the adapters' devices count
				if (this.seenDevices && this.isDevicesEdit) {
					let adapter = this.deviceDiscovery.counters.find((item) => !item.name.includes('active_directory'))
					let name = ''
					let filter = ''
					if (adapter) {
						// Found an adapter other than Active Directory - view will filter it
						name = adapter.name.split('_').join(' ')
						filter = `adapters == '${adapter.name}'`
					} else {
						// Active Directory is the only adapter - view will filter for Windows 10
						name = 'Windows 10'
						filter = 'specific_data.data.os.distribution == "10"'
					}
					this.saveView({
						name: `DEMO - ${name}`, module: 'devices', predefined: true, view: {
							...this.devicesView, query: { filter }
						}
					})
				}
			})
		},
        updated() {
            if (this.wizardActivated && this.newChart) {
                this.changeState({name: 'dashboardChart', id: this.newChart})
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
            min-height: 300px;
            .card-history {
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
                line-height: 200px;
            }
        }
    }
</style>