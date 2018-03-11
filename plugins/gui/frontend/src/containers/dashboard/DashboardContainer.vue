<template>
    <scrollable-page title="axonius dashboard" class="dashboard">
        <card title="Data Collection">
            <x-counter :data="adapterDevicesCounterData"></x-counter>
        </card>
        <card title="Devices per Adapter">
            <x-histogram :data="adapterDevicesCount" @click-bar="runAdapterDevicesFilter"></x-histogram>
        </card>
        <card title="System Lifecycle" class="lifecycle">
            <x-cycle-chart :data="lifecycle.subPhases"></x-cycle-chart>
            <div class="cycle-time">Next cycle starts in<div class="blue">{{ nextRunTime }}</div></div>
        </card>
    </scrollable-page>
</template>


<script>
    import ScrollablePage from '../../components/ScrollablePage.vue'
    import Card from '../../components/Card.vue'

    import xCounter from '../../components/charts/Counter.vue'
    import xHistogram from '../../components/charts/Histogram.vue'
    import xCycleChart from '../../components/charts/Cycle.vue'

    import { FETCH_LIFECYCLE, FETCH_ADAPTER_DEVICES } from '../../store/modules/dashboard'
    import { UPDATE_NEW_QUERY } from '../../store/modules/query'
    import { mapState, mapMutations, mapActions } from 'vuex'

    export default {
        name: 'x-dashboard',
        components: {
			ScrollablePage, Card, xCounter, xHistogram, xCycleChart },
        computed: {
            ...mapState(['dashboard']),
            lifecycle() {
				if (!this.dashboard.lifecycle.data) return {}

				return this.dashboard.lifecycle.data
            },
            adapterDevices() {
            	if (!this.dashboard.adapterDevices.data) return {}

            	return this.dashboard.adapterDevices.data
            },
            adapterDevicesCount() {
            	return this.adapterDevices.adapter_count
            },
            adapterDevicesCounterData() {
            	return [
                    {count: this.adapterDevices.total_gross, title: 'Managed Devices Collected', highlight: true},
					{count: this.adapterDevices.total_net, title: 'Actual Devices Discovered'},
                ]
            },
            nextRunTime() {
				let leftToRun = new Date(parseInt(this.lifecycle.nextRunTime) * 1000) - Date.now()
                let thresholds = [1000, 60 * 1000, 60 * 60 * 1000, 24 * 60 * 60 * 1000]
                let units = ['seconds', 'minutes', 'hours', 'days']
                for (let i = 1; i < thresholds.length; i++) {
					if (leftToRun < thresholds[i]) {
						return `${parseInt(leftToRun / thresholds[i - 1])} ${units[i-1]}`
					}
                }
				return `${parseInt(leftToRun / thresholds[thresholds.length])} ${units[units.length]}`
			}
        },
        methods: {
			...mapMutations({ updateQuery: UPDATE_NEW_QUERY}),
			...mapActions({ fetchLifecycle: FETCH_LIFECYCLE, fetchAdapterDevices: FETCH_ADAPTER_DEVICES }),
            getDashboardData() {
            	this.fetchLifecycle()
                this.fetchAdapterDevices()
            },
			runAdapterDevicesFilter(adapterName) {
                this.updateQuery({filter: `adapters == '${adapterName}'`})
				this.$router.push({name: 'Devices'})
            }
        },
        created() {
        	this.getDashboardData()
            this.interval = setInterval(function () {
				this.fetchLifecycle()
			}.bind(this), 500)
		},
		beforeDestroy() {
        	clearInterval(this.interval)
		}
    }
</script>


<style lang="scss">

    .dashboard {
        .page-body {
            display: flex;
            flex-wrap: wrap;
            .card {
                width: 360px;
                margin-right: 24px;
                &.lifecycle .card-body {
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    .cycle {
                        flex: 100%;
                    }
                    .cycle-time {
                        font-size: 14px;
                        .blue {
                            display: inline-block;
                            margin-left: 8px;
                        }
                    }
                }
                &.patches {
                    .info {
                        font-size: 20px;
                        margin-bottom: 8px;
                    }
                    .row {
                        margin-left: 0;
                        .col-4 {
                            text-align: center;
                            font-size: 20px;
                        }
                    }
                }
            }
        }
    }
</style>