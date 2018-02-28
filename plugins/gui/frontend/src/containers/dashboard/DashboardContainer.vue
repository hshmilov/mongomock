<template>
    <scrollable-page title="axonius dashboard" class="dashboard">
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
    import { FETCH_LIFECYCLE } from '../../store/modules/dashboard'
    import { mapState, mapActions } from 'vuex'

    export default {
        name: 'x-dashboard',
        components: { ScrollablePage, Card, xProgressCycle },
        computed: {
            ...mapState(['dashboard']),
            lifecycle() {
				if (!this.dashboard.lifecycle.data) return {}

				return this.dashboard.lifecycle.data
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
            ...mapActions({fetchLifecycle: FETCH_LIFECYCLE})
        },
        created() {
        	this.fetchLifecycle()
			this.interval = setInterval(function () {
				this.fetchLifecycle()
			}.bind(this), 1000);
		},
		beforeDestroy() {
			clearInterval(this.interval);
		}
    }
</script>


<style lang="scss">
    .dashboard {
        .card {
            width: 360px;
            .card-body {
                text-align: center;
            }
        }
    }
</style>