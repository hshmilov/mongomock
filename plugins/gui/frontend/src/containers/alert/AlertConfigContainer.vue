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
                            <input class="form-control" id="alertName" v-model="alert.name">
                        </div>
                        <div class="form-group col-6">
                            <label class="form-label" for="alertQuery">Select Saved Query:</label>
                            <select class="form-control" id="alertQuery" v-model="alert.query">
                                <option v-for="query in currentQueryOptions" :value="query.value"
                                        :selected="query.value === alert.query">{{query.name}}</option>
                            </select>
                        </div>
                    </div>
                    <div class="row row-divider">
                        <!-- Section for defining the condition which match of will trigger the alert -->
                        <div class="form-group col-6">
                            <div class="form-group-header">
                                <i class="icon-equalizer2"></i>
                                <span class="form-group-title">Alert Trigger</span>
                            </div>
                            <div>Monitor selected query and test whether devices number...</div>
                            <checkbox class="ml-4 mt-2" label="Increased" v-model="alert.triggers.increase"></checkbox>
                            <div class="form-inline" v-show="alert.triggers.increase">
                                <label for="TriggerAbove">Above:</label>
                                <input id="TriggerAbove" type="number" class="ml-4" v-model="alert.triggers.above"  min="0">
                            </div>
                            <checkbox class="ml-4" label="Decrease" v-model="alert.triggers.decrease"></checkbox>
                            <div class="form-inline" v-show="alert.triggers.decrease">
                                <label for="TriggerBelow">Below:</label>
                                <input id="TriggerBelow" type="number" class="ml-4" v-model="alert.triggers.below" min="0">
                            </div>
                            <checkbox class="ml-4" label="Not Changed" v-model="alert.triggers.noChange"></checkbox>
                        </div>
                        <div class="form-group col-6">
                            <div class="form-group-header">
                                <i class="icon-exclamation-triangle"></i>
                                <span class="form-group-title">Alert Severity</span>
                            </div>
                            <div class="col-4 mt-2 ml-4">
                                <div>
                                    <input id="SeverityInfo" type="radio" value="info" v-model="alert.severity">
                                    <label for="SeverityInfo"><status-icon value="info"></status-icon>Info</label>
                                </div>
                                <div>
                                    <input id="SeverityWarning" type="radio" value="warning" v-model="alert.severity">
                                    <label for="SeverityWarning"><status-icon value="warning"></status-icon>Warning</label>
                                </div>
                                <div>
                                    <input id="SeverityError" type="radio" value="error" v-model="alert.severity">
                                    <label for="SeverityError"><status-icon value="error"></status-icon>Error</label>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="row row-divider">
                        <!-- group for defining what action will occur upon trigger -->
                        <div class="form-group col-6">
                            <div class="form-group-header">
                                <i class="icon-bell-o"></i><span class="form-group-title">Action</span>
                            </div>
                            <checkbox class="ml-4 mt-2" label="Push a system notification" v-model="actions.notification"></checkbox>
                            <checkbox class="ml-4 mt-2 inline" label="Send an Email" v-model="actions.mail"></checkbox>
                            <template v-if="actions.mail">
                                <vm-select v-model="mailList" multiple filterable allow-create
                                           no-data-text="Type mail addresses..." placeholder=""></vm-select>
                            </template>
                            <template v-if="alert.triggers.increase">
                                <checkbox class="ml-4 mt-2 inline" label="Tag Devices" v-model="actions.tag"></checkbox>
                                <template v-if="actions.tag">
                                    <input class="form-control" id="tagName" v-model="tagName">
                                </template>
                            </template>
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
		components: {
            ScrollablePage, Card, Checkbox, StatusIcon },
		computed: {
            ...mapState({
                alertData: state => state.alert.alertDetails.data
			}),
            ...mapGetters([ 'savedQueryOptions' ]),
            currentQueryOptions() {
            	return this.savedQueryOptions.filter((query) => {
            		return !query.inUse || this.alertData.query === query.value
                })
            }
        },
        data() {
			return {
                /* Control of the criteria parameter with the use of two conditions */
                alert: { },
                actions: {
                	notification: false, mail: false, tag: false
                },
                mailList: [],
                tagName: ''
            }
		},
        watch: {
			alertData(newAlertData) {
				this.fillAlert(newAlertData)
            }
        },
        methods: {
            ...mapMutations({ setAlert: SET_ALERT }),
            ...mapActions({ fetchQueries: FETCH_SAVED_QUERIES, updateAlert: UPDATE_ALERT }),
            fillAlert(alert) {
				this.alert = { ...alert }
				this.alert.actions.forEach((action) => {
					switch (action.type) {
						case 'create_notification':
							this.actions.notification = true
							break
						case 'send_emails':
							this.actions.mail = true
							this.mailList = action.data
							break
                        case 'tag_device':
                            this.actions.tag = true
                            this.tagName = action.data
					}
				})
            },
			saveAlert() {
            	/* Validation */
                if (!this.alert.name) return
                if (!this.alert.query) return

                if (this.actions.notification) {
                	this.alert.actions.push({
                        type: 'create_notification'
                    })
                }
                if (this.actions.mail) {
                	this.alert.actions.push({
                        type: 'send_emails', data: this.mailList
                    })
                }
                if (this.actions.tag) {
                    this.alert.actions.push({
                        type: 'tag_device', data: this.tagName
                    })
                }
                /* Save and return to alerts page */
                this.updateAlert(this.alert)
				this.returnToAlerts()
            },
            returnToAlerts() {
				this.$router.push({name: 'Alerts'})
            }
        },
        created() {
			this.fillAlert(this.alertData)
			/*
			    If no alert from controls source, try and fetch it.
			    Otherwise, if alert from controls source has correct id, update local alert controls with its values
			 */
            if (!this.alertData || !this.alertData.id || (this.$route.params.id !== this.alertData.id)) {
                this.setAlert(this.$route.params.id)
            }

			/* Fetch all saved queries for offering user to base alert upon */
			if (!this.savedQueryOptions || !this.savedQueryOptions.length) {
				this.fetchQueries({})
            }
        }
	}
</script>

<style lang="scss">
    .alert-config {
        .checkbox.inline.checked {
            display: inline;
        }
        #tagName {
        width: 150px;
        }
    }
</style>