<template>
    <scrollable-page :breadcrumbs="[
    	{ title: 'alerts', path: {name: 'Alerts'}},
    	{ title: (alertData.name? alertData.name : 'new alert')}
    ]">
        <card title="configure" class="alert-config">
            <template slot="cardContent">
                <form @keyup.enter="saveAlert">
                    <div class="row">
                        <!-- Section for alert name and query to run by -->
                        <div class="form-group col-6">
                            <label class="form-label" for="alertName">Alert Name:</label>
                            <input class="form-control" id="alertName" v-model="alertData.name">
                        </div>
                        <div class="form-group col-6">
                            <label class="form-label" for="alertQuery">Select Saved Query:</label>
                            <select class="form-control" id="alertQuery" v-model="alertData.query">
                                <option v-for="query in savedQueryOptions" :value="query.value"
                                        :selected="query.value === alertData.query">{{query.name}}</option>
                            </select>
                        </div>
                    </div>
                    <div class="row row-divider">
                        <!-- Section for defining the condition which match of will trigger the alert -->
                        <div class="form-group col-6">
                            <div class="form-group-header">
                                <i class="icon-equalizer2"></i><span class="form-group-title">Alert Condition</span>
                            </div>
                            <checkbox class="ml-4 mt-2" label="Increase in devices number" v-model="alertCondition.increase"
                                      @change="updateCriteria()"></checkbox>
                            <checkbox class="ml-4" label="Decrease in devices number" v-model="alertCondition.decrease"
                                      @change="updateCriteria()"></checkbox>
                        </div>
                    </div>
                    <div class="row row-divider">
                        <!-- Section for defining how often conditions will be tested and how to present results -->
                        <div class="form-group col-6">
                            <div class="form-group-header">
                                <i class="icon-calendar"></i><span class="form-group-title">Schedule</span>
                            </div>
                            <select class="custom-select col-4 mt-2 ml-4" :disabled="true">
                                <option :disabled="true" :selected="true">Always</option>
                            </select>
                        </div>
                        <div class="form-group col-6">
                            <div class="form-group-header">
                                <i class="icon-graph"></i><span class="form-group-title">Presentation</span>
                            </div>
                            <select class="custom-select col-4 mt-2 ml-4" :disabled="true">
                                <option :disabled="true" :selected="true">Select report type...</option>
                            </select>
                        </div>
                    </div>
                    <div class="row row-divider">
                        <!-- group for defining what action will occur upon trigger -->
                        <div class="form-group col-6">
                            <div class="form-group-header">
                                <i class="icon-bell-o"></i><span class="form-group-title">Share and Notify</span>
                            </div>
                            <checkbox class="ml-4 mt-2" label="Add a system notification" v-model="alertData.notification"></checkbox>
                            <checkbox class="ml-4" label="Send an email" :disabled="true"></checkbox>
                            <checkbox class="ml-4" label="Add to Dashboard" :disabled="true"></checkbox>
                        </div>
                        <div class="form-group col-6">
                            <div class="form-group-header">
                                <i class="icon-dashboard"></i><span class="form-group-title">Trigger Action</span>
                            </div>
                            <select class="custom-select col-4 mt-2 ml-4" :disabled="true">
                                <option :disabled="true" :selected="true">Select Plugin...</option>
                            </select>
                        </div>
                    </div>
                    <div class="row">
                        <div class="form-group place-right">
                            <a class="btn btn-inverse" @click="returnToAlerts">cancel</a>
                            <a class="btn" @click="saveAlert">save</a>
                        </div>
                    </div>
                </form>
            </template>
        </card>
    </scrollable-page>
</template>

<script>
	import ScrollablePage from '../../components/ScrollablePage.vue'
    import Card from '../../components/Card.vue'
    import Checkbox from '../../components/Checkbox.vue'

    import { mapState, mapGetters, mapActions } from 'vuex'
    import { FETCH_SAVED_QUERIES } from '../../store/modules/query'
    import { FETCH_ALERT, UPDATE_ALERT } from '../../store/modules/alert'

	export default {
		name: 'alert-config-container',
		components: { ScrollablePage, Card, Checkbox },
		computed: {
            ...mapState([ 'alert', 'query' ]),
            ...mapGetters([ 'savedQueryOptions' ]),
            alertData() {
            	return this.alert.alertDetails.data
            }
        },
        data() {
			return {
                /* Control of the criteria parameter with the use of two conditions */
                alertCondition: {
					increase: false,
                    decrease: false
                }
            }
		},
        watch: {
			alertData: function(newAlertData) {
				this.updateCondition()
            }
        },
        methods: {
            ...mapActions({ fetchAlert: FETCH_ALERT, fetchQueries: FETCH_SAVED_QUERIES, updateAlert: UPDATE_ALERT }),
            updateCriteria() {
            	/* Update the matching criteria value, according to the conditions' values */
				if (this.alertCondition.increase && this.alertCondition.decrease) {
					this.alertData.criteria = 0
				}
				if (this.alertCondition.increase && !this.alertCondition.decrease) {
					this.alertData.criteria = 1
				}
				if (!this.alertCondition.increase && this.alertCondition.decrease) {
					this.alertData.criteria = -1
				}
            },
            updateCondition() {
            	/* Update the conditions' values according to current criteria value */
            	if (this.alertData.criteria <= 0) {
					this.alertCondition.decrease = true
                }
				if (this.alertData.criteria >= 0) {
					this.alertCondition.increase = true
				}
            },
			saveAlert() {
            	/* Validation */
				if (this.alertData.criteria === undefined) {
					return
                }
                if (!this.alertData.name) {
					return
                }
                if (!this.alertData.query) {
					return
                }
                /* Save and return to alerts page */
                this.updateAlert(this.alertData)
				this.returnToAlerts()
            },
            returnToAlerts() {
				this.$router.push({name: 'Alerts'})
            }
        },
        created() {
			/*
			    If no alert from data source, try and fetch it.
			    Otherwise, if alert from data source has correct id, update local alert data with its values
			 */
            if (!this.alertData || !this.alertData.id || (this.$route.params.id !== this.alertData.id)) {
                this.fetchAlert(this.$route.params.id)
            }
			/* Fetch all saved queries for offering user to base alert upon */
			if (!this.savedQueryOptions || !this.savedQueryOptions.length) {
				this.fetchQueries({})
            }
        }
	}
</script>

<style lang="scss">

</style>