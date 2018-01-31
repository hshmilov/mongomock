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
                                <option v-for="query in currentQueryOptions" :value="query.value"
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
                        <div class="form-group col-6">
                            <div class="form-group-header">
                                <i class="icon-exclamation-triangle"></i><span class="form-group-title">Alert Severity</span>
                            </div>
                            <select class="custom-select col-4 mt-2 ml-4" v-model="alertData.severity">
                                <option :selected="true" value="info">
                                    <status-icon value="info"></status-icon>Info</option>
                                <option :selected="true" value="warning">
                                    <status-icon value="warning"></status-icon>Warning</option>
                                <option :selected="true" value="error">
                                    <status-icon value="error"></status-icon>Error</option>
                            </select>
                        </div>
                    </div>
                    <div class="row row-divider">
                        <!-- Section for defining how often conditions will be tested and how to present results -->
                        <div class="form-group col-6">
                            <div class="form-group-header disabled-text">
                                <i class="icon-calendar"></i><span class="form-group-title">Schedule</span>
                            </div>
                            <select class="custom-select col-4 mt-2 ml-4" :disabled="true">
                                <option :disabled="true" :selected="true">Always</option>
                            </select>
                        </div>
                        <div class="form-group col-6">
                            <div class="form-group-header disabled-text">
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
                            <checkbox class="ml-4 mt-2" label="Add a system notification" v-model="alertType.notification"></checkbox>
                        </div>
                        <div class="form-group col-6">
                            <div class="form-group-header disabled-text">
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
    import StatusIcon from '../../components/StatusIcon.vue'

    import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
    import { FETCH_SAVED_QUERIES } from '../../store/modules/query'
    import { SET_ALERT, UPDATE_ALERT } from '../../store/modules/alert'

	export default {
		name: 'alert-config-container',
		components: { ScrollablePage, Card, Checkbox, StatusIcon },
		computed: {
            ...mapState([ 'alert', 'query' ]),
            ...mapGetters([ 'savedQueryOptions' ]),
            alertData() {
            	return this.alert.alertDetails.data
            },
            currentQueryOptions() {
            	return this.savedQueryOptions.filter((query) => {
            		return !query.inUse || this.alertData.query === query.value
                })
            }
        },
        data() {
			return {
                /* Control of the criteria parameter with the use of two conditions */
                alertCondition: {
					increase: false,
                    decrease: false
                },
                alertType: {
                	notification: false
                }
            }
		},
        watch: {
			alertData: function() {
				this.prepareForm()
            }
        },
        methods: {
            ...mapMutations({ setAlert: SET_ALERT }),
            ...mapActions({ fetchQueries: FETCH_SAVED_QUERIES, updateAlert: UPDATE_ALERT }),
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
            prepareForm() {
				this.updateCondition()
				this.alertData['alert_types'].forEach((alertType) => {
					if (alertType.type === "notification") {
						this.alertType.notification = true
					}
				})
            },
			saveAlert() {
            	/* Validation */
				if (this.alertData.criteria === undefined) { return }
                if (!this.alertData.name) { return }
                if (!this.alertData.query) {return }

                this.alertData['alert_types'] = []
                Object.keys(this.alertType).forEach((alertType) => {
					if (!this.alertType[alertType]) { return }
					let name = ''
                    this.currentQueryOptions.forEach((query) => {
						if (this.alertData.query === query.value) {
							name = query.name
                        }
                    })
					let diff = 'changed'
                    if (this.alertData.criteria === 1) {
						diff = 'increased'
                    } else if (this.alertData.criteria === -1) {
						diff = 'decreased'
                    }
					this.alertData['alert_types'].push({
                        type: alertType,
                        title: `Query "${name}" result changed`,
                        message: `Amount of devices returned for the query has ${diff}`
                    })
                })
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
			    If no alert from controls source, try and fetch it.
			    Otherwise, if alert from controls source has correct id, update local alert controls with its values
			 */
            if (!this.alertData || !this.alertData.id || (this.$route.params.id !== this.alertData.id)) {
                this.setAlert(this.$route.params.id)
            } else {
				this.prepareForm()
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