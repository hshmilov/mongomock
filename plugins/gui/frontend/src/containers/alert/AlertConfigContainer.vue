<template>
    <x-page :breadcrumbs="[
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
                            <select class="form-control" id="alertQuery" v-model="currentQuery">
                                <option v-for="query in currentQueryOptions" :value="query"
                                        :selected="query.name === alert.query">{{query.title || query.name}}</option>
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
                            <div class="form-group-content">
                                <checkbox :class="{'grid-span2': !alert.triggers.increase}" label="Increased"
                                          v-model="alert.triggers.increase"/>
                                <div class="form-inline" v-if="alert.triggers.increase">
                                    <label for="TriggerAbove">Above:</label>
                                    <input id="TriggerAbove" type="number" v-model="alert.triggers.above"  min="0">
                                </div>
                                <checkbox :class="{'grid-span2': !alert.triggers.decrease}" label="Decrease"
                                          v-model="alert.triggers.decrease" />
                                <div class="form-inline" v-if="alert.triggers.decrease">
                                    <label for="TriggerBelow">Below:</label>
                                    <input id="TriggerBelow" type="number" v-model="alert.triggers.below" min="0">
                                </div>
                                <checkbox class="grid-span2" label="Not Changed" v-model="alert.triggers.no_change"/>
                            </div>
                        </div>
                        <div class="form-group col-6">
                            <div class="form-group-header">
                                <i class="icon-exclamation-triangle"></i>
                                <span class="form-group-title">Alert Severity</span>
                            </div>
                            <div class="form-group-content">
                                <div class="grid-span2">
                                    <input id="SeverityInfo" type="radio" value="info" v-model="alert.severity">
                                    <label for="SeverityInfo" class="ml-2"><status-icon value="info"/>Info</label>
                                </div>
                                <div class="grid-span2">
                                    <input id="SeverityWarning" type="radio" value="warning" v-model="alert.severity">
                                    <label for="SeverityWarning" class="ml-2"><status-icon value="warning"/>Warning</label>
                                </div>
                                <div class="grid-span2">
                                    <input id="SeverityError" type="radio" value="error" v-model="alert.severity">
                                    <label for="SeverityError" class="ml-2"><status-icon value="error"/>Error</label>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="row row-divider">
                        <!-- group for defining what action will occur upon trigger -->
                        <div class="form-group">
                            <div class="form-group-header">
                                <i class="icon-bell-o"></i><span class="form-group-title">Action</span>
                            </div>
                            <div class="form-group-content">
                                <checkbox class="grid-span2" label="Push a system notification" v-model="actions.notification"/>
                                <checkbox :class="{'grid-span2': !actions.mail}" label="Send an Email" v-model="actions.mail"/>
                                <template v-if="actions.mail">
                                    <vm-select v-model="mailList" multiple filterable allow-create placeholder=""
                                           no-data-text="Type mail addresses..." :default-first-option="true"/>
                                </template>
                                <template v-if="alert.triggers.increase">
                                    <checkbox :class="{'grid-span2': !actions.tag}" label="Tag Entities" v-model="actions.tag"/>
                                    <template v-if="actions.tag">
                                        <input class="form-control" id="tagName" v-model="tagName">
                                    </template>
                                </template>
                            </div>
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
        <modal v-if="error">
            <div slot="body">
                <div class="show-space">{{error}}</div>
            </div>
            <button class="x-btn" slot="footer" @click="closeError">OK</button>
        </modal>
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
    import Card from '../../components/Card.vue'
    import Checkbox from '../../components/Checkbox.vue'
    import StatusIcon from '../../components/StatusIcon.vue'
    import Modal from '../../components/popover/Modal.vue'

    import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_DATA_QUERIES } from '../../store/actions'
    import { SET_ALERT, UPDATE_ALERT, FETCH_ALERTS } from '../../store/modules/alert'

	export default {
		name: 'alert-config-container',
		components: {
            xPage, Card, Checkbox, StatusIcon, Modal },
		computed: {
            ...mapState({
                alertData: state => state.alert.alertDetails.data,
                alerts: state => state.alert.alertList.data,
                currentQueryOptions(state) {
                	let queries = [ ...state.devices.queries.saved.data.map((item) => {
                        return { ...item, entity: 'devices' }
                    }), ...state.users.queries.saved.data.map((item) => {
                        return { ...item, entity: 'users' }
                    }) ]
                	if (!queries || !queries.length) return []
                    if (this.alert && this.alert.query) {
                        let hasCurrent = false
                        queries.forEach((query) => {
                            if (query.name === this.alert.query) hasCurrent = true
                        })
                        if (!hasCurrent) {
                            queries.push({
                                name: this.alert.query, title: `${this.alert.query} (deleted)`
                            })
                        }
                    }
                    return queries
                }
			})
        },
        data() {
			return {
                /* Control of the criteria parameter with the use of two conditions */
                alert: { triggers: {}, actions: [] },
                currentQuery: {},
                actions: {
                	notification: false, mail: false, tag: false
                },
                mailList: [],
                tagName: '',
                error: ''
            }
		},
        watch: {
			alertData(newAlertData) {
				this.fillAlert(newAlertData)
            }
        },
        methods: {
            ...mapMutations({ setAlert: SET_ALERT }),
            ...mapActions({ fetchQueries: FETCH_DATA_QUERIES, updateAlert: UPDATE_ALERT, fetchAlerts: FETCH_ALERTS }),
            fillAlert(alert) {
				alert.actions.forEach((action) => {
					switch (action.type) {
						case 'create_notification':
							this.actions.notification = true
							break
						case 'send_emails':
							this.actions.mail = true
							this.mailList = action.data
							break
                        case 'tag_entities':
                            this.actions.tag = true
                            this.tagName = action.data
					}
				})
				this.alert = { ...alert,
                    triggers: { ...alert.triggers },
                    actions: []
                }
            },
			saveAlert() {
            	/* Validation */
                if (!this.alert.name) return
                if (!this.currentQuery.name) return
                if ((this.alertData.id === "new" || this.alert.name !== this.alertData.name) && this.alerts.some(e => e.name === this.alert.name)) {
                    this.error = 'An Alert with that name already exists, please choose a different one.'
                    return
                }

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
                        type: 'tag_entities', data: this.tagName
                    })
                }
                this.alert.query = this.currentQuery.name
                this.alert.queryEntity = this.currentQuery.entity
                /* Save and return to alerts page */
                this.updateAlert(this.alert)
				this.returnToAlerts()
            },
            returnToAlerts() {
				this.$router.push({name: 'Alerts'})
            },
            closeError() {
                this.error = ''
            }
        },
        created() {
			/*
			    If no alert from controls source, try and fetch it.
			    Otherwise, if alert from controls source has correct id, update local alert controls with its values
			 */
            if (!this.alertData || !this.alertData.id || (this.$route.params.id !== this.alertData.id)) {
                this.fetchAlerts({}).then(() => {
                    this.setAlert(this.$route.params.id)
                })
            } else {
			    this.fillAlert(this.alertData)
            }

			/* Fetch all saved queries for offering user to base alert upon */
            Promise.all([this.fetchQueries({module: 'devices', type: 'saved'}),
                         this.fetchQueries({module: 'users', type: 'saved'})]).then(() => {
                    if (this.alertData.query) {
                        let matching = this.currentQueryOptions.filter(item =>
                            (this.alertData.id === 'new' ? item.uuid : item.name) === this.alertData.query)
                        if (matching.length) {
                            this.currentQuery = matching[0]
                            this.alert.query = this.currentQuery.name
                            this.alert.queryEntity = this.currentQuery.entity
                        } else {
                            this.alert.query = ''
                        }
                    }
                }
            )
        }
	}
</script>

<style lang="scss">
    .alert-config {
        .checkbox.inline.checked {
            display: inline;
        }
    }
    .form-group {
        .form-group-content {
            display: grid;
            grid-template-columns: 1fr 2fr;
            align-items: center;
            grid-gap: 8px;
            margin-left: 24px;
            margin-top: 12px;
            .vm-select {
                .vm-select-input__inner {
                    width: 100%;
                }
            }
            .form-inline {
                display: grid;
                grid-template-columns: 1fr 3fr;
                align-items: center;
            }
            .status-icon {
                border-radius: 4px;
                margin-right: 4px;
            }
        }
    }
</style>