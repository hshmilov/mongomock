<template>
    <scrollable-page :title="`alerts > ${alertData.name? alertData.name : 'new'} alert`">
        <card title="alert configuration" class="alert-config">
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
                            <div class="form-section-header">
                                <i class="icon-equalizer2"></i><span class="form-section-title">Alert Condition</span>
                            </div>
                            <checkbox label="Increase in devices number" v-model="alertCondition.increase"
                                      @change="updateCriteria()"></checkbox>
                            <checkbox label="Decrease in devices number" v-model="alertCondition.decrease"
                                      @change="updateCriteria()"></checkbox>
                        </div>
                        <div class="form-group col-6">
                            <div class="form-section-header">
                                <i class="icon-dashboard"></i><span class="form-section-title">Trigger Action</span>
                            </div>
                            <select class="form-select" :disabled="true">
                                <option :disabled="true" :selected="true">Select Plugin...</option>
                            </select>
                        </div>
                    </div>
                    <div class="row row-divider">
                        <!-- Section for defining what action will occur upon trigger -->
                        <div class="form-group col-6">
                            <div class="form-section-header">
                                <i class="icon-bell-o"></i><span class="form-section-title">Share and Notify</span>
                            </div>
                            <checkbox label="Add a system notification" v-model="alertData.notification"></checkbox>
                            <checkbox label="Send an email" :disabled="true"></checkbox>
                            <checkbox label="Add to Dashboard" :disabled="true"></checkbox>
                        </div>
                        <div class="form-group col-6 action-group">
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
    import { FETCH_ALERT, INSERT_ALERT } from '../../store/modules/alert'

	export default {
		components: { ScrollablePage, Card, Checkbox },
		name: 'alert-config-container',
        computed: {
            ...mapState([ 'alert', 'query' ]),
            ...mapGetters([ 'savedQueryOptions' ]),
            alertData() {
            	return this.alert.currentAlert.data
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
            ...mapActions({ fetchAlert: FETCH_ALERT, fetchQueries: FETCH_SAVED_QUERIES, insertAlert: INSERT_ALERT }),
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
                this.insertAlert(this.alertData)
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
    @import '../../scss/config';

    .alert-config {
        .row {
            position: relative;
            .form-group {
                padding: 12px 24px;
                .form-section-header {
                    color: $color-theme;
                    font-size: 20px;
                    .form-section-title {
                        margin-left: 8px;
                    }
                }
                .form-select, .checkbox {
                    margin: 12px 24px;
                }
                &.action-group {
                    text-align: right;
                    line-height: 160px;
                }
            }
        }
    }
</style>