<template>
    <scrollable-page title="axonius dashboard" class="dashboard">
        <card title="Data Collection">
            <x-counter :data="adapterDevicesCounterData"></x-counter>
        </card>
        <card title="Devices per Adapter">
            <x-histogram :data="adapterDevicesCount" @click-bar="runAdapterDevicesFilter"></x-histogram>
        </card>
        <card title="System Lifecycle">
            <x-progress-cycle :complete="cyclePortionComplete" :parts="lifecycle.stages"
                              :remaining="lifecycle.current_status"></x-progress-cycle>
            <div class="cycle-time">Next cycle starts in<div class="blue">{{ nextRunTime }}</div></div>
        </card>
    </scrollable-page>
</template>


<script>
    import ScrollablePage from '../../components/ScrollablePage.vue'
    import Card from '../../components/Card.vue'

    import xCounter from '../../components/charts/Counter.vue'
    import xHistogram from '../../components/charts/Histogram.vue'
    import xProgressCycle from '../../components/charts/ProgressCycle.vue'

    import { FETCH_LIFECYCLE, FETCH_ADAPTER_DEVICES } from '../../store/modules/dashboard'
    import { UPDATE_NEW_QUERY } from '../../store/modules/query'
    import { mapState, mapMutations, mapActions } from 'vuex'

    export default {
        name: 'x-dashboard',
        components: { ScrollablePage, Card, xCounter, xHistogram, xProgressCycle },
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
            cyclePortionComplete() {
                if (!this.lifecycle || !this.lifecycle.stages || !this.lifecycle.stages.length) return 0
                if (!this.lifecycle.current_stage) return 100

                const currentPhase = this.lifecycle.stages.indexOf(this.lifecycle.current_stage)
                let completed = (currentPhase / this.lifecycle.stages.length) * 100
                if (this.lifecycle.current_status) {
                	completed += parseInt(100 / (this.lifecycle.stages.length * 2))
                }
                return completed
            },
            nextRunTime() {
				let leftToRun = new Date(parseInt(this.lifecycle.next_run_time) * 1000) - Date.now()
                let thresholds = [1000, 60 * 1000, 60 * 60 * 1000, 24 * 60 * 60 * 1000]
                let units = ['seconds', 'minutes', 'hours', 'days']
                for (var i = 1; i < thresholds.length; i++) {
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
			}.bind(this), 1000)
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
            .card {
                width: 360px;
                margin-right: 24px;
                .card-body {
                    text-align: center;
                    .cycle-time {
                        margin-top: 16px;
                        font-size: 14px;
                        .blue {
                            display: inline-block;
                            margin-left: 8px;
                        }
                    }
                }
            }
        }
    }
</style>