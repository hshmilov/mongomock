<template>
    <scrollable-page title="axonius dashboard" class="dashboard">
        <card title="Devices per Adapter">
            <x-histogram :data="adapterDevices"></x-histogram>
        </card>
        <card title="System Lifecycle">
            <x-progress-cycle :complete="cyclePortionComplete" :parts="lifecycle.stages"
                              :remaining="lifecycle.current_status"></x-progress-cycle>
        </card>
    </scrollable-page>
</template>


<script>
    import ScrollablePage from '../../components/ScrollablePage.vue'
    import Card from '../../components/Card.vue'
    import xProgressCycle from '../../components/charts/ProgressCycle.vue'
    import xHistogram from '../../components/charts/Histogram.vue'
    import { FETCH_LIFECYCLE, FETCH_ADAPTER_DEVICES } from '../../store/modules/dashboard'
    import { mapState, mapActions } from 'vuex'

    export default {
        name: 'x-dashboard',
        components: { ScrollablePage, Card, xProgressCycle, xHistogram },
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
            cyclePortionComplete() {
                if (!this.lifecycle || !this.lifecycle.stages || !this.lifecycle.stages.length) return 0
                if (!this.lifecycle.current_stage) return 100

                const currentPhase = this.lifecycle.stages.indexOf(this.lifecycle.current_stage)
                let completed = (currentPhase / this.lifecycle.stages.length) * 100
                if (this.lifecycle.current_status) {
                	completed += parseInt(100 / (this.lifecycle.stages.length * 2))
                }
                return completed
            }
        },
        methods: {
            ...mapActions({fetchLifecycle: FETCH_LIFECYCLE, fetchAdapterDevices: FETCH_ADAPTER_DEVICES}),
            getDashboardData() {
            	this.fetchLifecycle()
                this.fetchAdapterDevices()
            }
        },
        created() {
        	this.getDashboardData()
            this.interval = setInterval(function () {
				this.getDashboardData()
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
                }
            }
        }
    }
</style>