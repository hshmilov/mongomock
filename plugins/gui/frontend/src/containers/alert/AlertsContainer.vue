<template>
    <x-page title="alerts">
        <x-data-table module="alert" title="Alerts" @click-row="configAlert" id-field="uuid" v-model="selected">
            <template slot="actions">
                <div v-if="selected && selected.length" @click="removeAlerts" class="x-btn link">Remove</div>
                <div @click="createAlert" class="x-btn" id="alert_new">+ New Alert</div>
            </template>
        </x-data-table>
    </x-page>
</template>


<script>
	import xPage from '../../components/layout/Page.vue'
    import xDataTable from '../../components/tables/DataTable.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_ALERTS, SET_ALERT, ARCHIVE_ALERTS } from '../../store/modules/alert'
    import { CHANGE_TOUR_STATE } from '../../store/modules/onboarding'

	export default {
        name: 'alert-container',
        components: { xPage, xDataTable },
		computed: {
            ...mapState({
                tourAlerts(state) {
                    return state.onboarding.tourStates.queues.alerts
                }
			})
		},
        data() {
        	return {
                selected: []
            }
        },
        methods: {
            ...mapMutations({ setAlert: SET_ALERT, changeState: CHANGE_TOUR_STATE }),
			...mapActions({ fetchAlerts: FETCH_ALERTS, archiveAlerts: ARCHIVE_ALERTS }),
            configAlert(alertId) {
				/*
                    Fetch the requested alert configuration and navigate to configuration page with the id, to load it
				 */
				if (!alertId) { return }
                this.setAlert(alertId)
				this.$router.push({path: `alert/${alertId}`})
            },
            createAlert() {
				this.setAlert('new')
				this.$router.push({path: '/alert/new'});
            },
            removeAlerts() {
            	this.archiveAlerts(this.selected)
            }
        },
        created() {
        	if (this.tourAlerts && this.tourAlerts.length) {
			    this.changeState({ name: this.tourAlerts[0] })
            }
        }
    }
</script>


<style lang="scss">

</style>