<template>
    <x-page title="axonius dashboard">
        <template v-if="isEmptySystem === null"></template>
        <template v-else-if="isEmptySystem">
            <x-empty-system/>
        </template>
        <template v-else>
            <x-search-insights @click="onClickInsights"/>
            <div class="dashboard-charts">
                <x-data-discovery-card :data="deviceDiscovery" module="devices"
                                       :filter="isDevicesRestricted? undefined: runFilter"/>
                <x-data-discovery-card :data="dashboard.dataDiscovery.users.data" module="users"
                                       :filter="isUsersRestricted? undefined: runFilter"/>
                <x-card v-for="(chart, chartInd) in charts" :key="chart.name" :title="chart.name"
                        :removable="!isReadOnly" @remove="removeDashboard(chart.uuid)" :id="getId(chart.name)">
                    <div class="card-history" v-if="chart.metric !== 'timeline'">
                        <x-historical-date v-model="chartsCurrentlyShowing[chart.uuid]" @clear="clearDate(chart.uuid)"
                                           @input="confirmPickDate(chart.uuid, chart.name)" />
                    </div>
                    <component :is="`x-${chart.view}`" :data="chart.data" @click-one="runChartFilter(chartInd, $event)" :id="getId(chart.name) + '_view'"/>
                </x-card>
                <x-card title="System Lifecycle" class="chart-lifecycle print-exclude">
                    <x-cycle :data="lifecycle.subPhases"/>
                    <div class="cycle-time">Next cycle starts in
                        <div class="blue">{{ nextRunTime }}</div>
                    </div>
                </x-card>
                <x-card title="New Chart" class="chart-new print-exclude">
                    <x-button link :disabled="isReadOnly" @click="createNewDashboard" id="dashboard_wizard">+</x-button>
                </x-card>
            </div>
            <x-wizard v-if="wizardActivated" @done="wizardActivated = false" />
        </template>
        <x-toast v-if="message" v-model="message" />
    </x-page>
</template>


<script>
    import xPage from '../axons/layout/Page.vue'
    import xCard from '../axons/layout/Card.vue'
    import xDataDiscoveryCard from '../neurons/cards/DataDiscoveryCard.vue'
    import xHistogram from '../axons/charts/Histogram.vue'
    import xPie from '../axons/charts/Pie.vue'
    import xSummary from '../axons/charts/Summary.vue'
    import xLine from '../axons/charts/Line.vue'
    import xCycle from '../axons/charts/Cycle.vue'
    import xWizard from '../networks/charts/Wizard.vue'
    import xEmptySystem from '../networks/onboard/EmptySystem.vue'
    import xModal from '../axons/popover/Modal.vue'
    import xButton from '../axons/inputs/Button.vue'
    import xToast from '../axons/popover/Toast.vue'
    import xSearchInsights from '../neurons/inputs/SearchInsights.vue'
    import xHistoricalDate from '../neurons/inputs/HistoricalDate.vue'

    import {
        FETCH_DISCOVERY_DATA, FETCH_DASHBOARD, REMOVE_DASHBOARD,
        FETCH_HISTORICAL_SAVED_CARD, FETCH_DASHBOARD_FIRST_USE
    } from '../../store/modules/dashboard'
    import {IS_EXPIRED} from '../../store/getters'
    import {UPDATE_DATA_VIEW} from '../../store/mutations'
    import {FETCH_DATA_VIEWS, SAVE_VIEW} from '../../store/actions'
    import {CHANGE_TOUR_STATE, NEXT_TOUR_STATE} from '../../store/modules/onboarding'
    import {mapState, mapGetters, mapMutations, mapActions} from 'vuex'

    export default {
        name: 'x-dashboard',
        components: {
            xPage, xCard, xDataDiscoveryCard, xHistogram, xPie, xSummary, xLine,
            xCycle, xWizard, xEmptySystem, xModal, xButton, xToast, xSearchInsights, xHistoricalDate
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
                                let historical_card = this.cardHistoricalData[chart.uuid]
                                if (historical_card) {
                                    let historical_card_view = historical_card[item.name]
                                    if (!historical_card_view) return null
                                    return {
                                        ...item,
                                        value: historical_card[item.name].value,
                                        showingHistorical: historical_card[item.name].accurate_for_datetime
                                    }
                                }
                                return item
                            }).filter(x => x)
                        }
                    })
                    // filter out charts without data or with hide_empty and remainder 100%
                    .filter(chart => chart && chart.data && !(chart.hide_empty && [0, 1].includes(chart.data[0].value)))
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
            ...mapGetters({
                isExpired: IS_EXPIRED
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
                return `${Math.round(leftToRun / thresholds[thresholds.length - 1])} ${units[units.length - 1]}`
            },
            isEmptySystem() {
                if (this.deviceDiscovery.seen === undefined || this.dashboardFirstUse === null) return null

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
                fetchDiscoveryData: FETCH_DISCOVERY_DATA,
                fetchDashboardFirstUse: FETCH_DASHBOARD_FIRST_USE,
                fetchDashboard: FETCH_DASHBOARD, removeDashboard: REMOVE_DASHBOARD,
                fetchHistoricalCard: FETCH_HISTORICAL_SAVED_CARD,
                fetchViews: FETCH_DATA_VIEWS, saveView: SAVE_VIEW
            }),
            runChartFilter(chartInd, queryInd) {
                let query = this.charts[chartInd].data[queryInd]
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
                this.wizardActivated = true
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
            onClickInsights() {
                this.$router.push({name: 'Insights Explorer'})
            }
        },
        created() {
            this.fetchDashboardFirstUse()
            const getDashboardData = () => {
                return Promise.all([
                    this.fetchDiscoveryData({module: 'devices'}), this.fetchDiscoveryData({module: 'users'}),
                    this.fetchDashboard()
                ]).then(() => {
                    if (this._isDestroyed) return
                    this.timer = setTimeout(getDashboardData, 30000)
                })
            }
            getDashboardData().then(() => {
                if (this._isDestroyed || this.isExpired) return
                if (!this.isEmptySystem) this.nextState('dashboard')
                if (this.isDevicesRestricted) return
                this.fetchViews({module: 'devices', type: 'saved'}).then(() => {
                    if (this.devicesViewsList.length && this.devicesViewsList.find((item) => item.name.includes('DEMO'))) return
                    // If DEMO view was not yet added, add it now, according to the adapters' devices count
                    if (this.seenDevices && this.isDevicesEdit) {
                        let adapter = this.deviceDiscovery.counters.find((item) => !item.name.includes('active_directory'))
                        let name = ''
                        let filter = ''
                        if (adapter) {
                            // Found an adapters other than Active Directory - view will filter it
                            name = adapter.name.split('_').join(' ')
                            filter = `adapters == '${adapter.name}'`
                        } else {
                            // Active Directory is the only adapters - view will filter for Windows 10
                            name = 'Windows 10'
                            filter = 'specific_data.data.os.distribution == "10"'
                        }
                        this.saveView({
                            name: `DEMO - ${name}`, module: 'devices', predefined: true, view: {
                                ...this.devicesView, query: {filter}
                            }
                        })
                    }
                })
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
        padding: 8px;
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
