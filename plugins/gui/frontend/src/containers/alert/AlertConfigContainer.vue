<template>
    <x-page :breadcrumbs="[
    	{ title: 'alerts', path: {name: 'Alerts'}},
    	{ title: (alertData.name? alertData.name : 'new alert')}
    ]">
        <x-box class="alert-config">
            <form @keyup.enter="saveAlert">
                    <!-- Section for alert name and query to run by -->
                <div class="x-grid">
                    <label for="alertName">Alert Name:</label>
                    <input id="alertName" v-model="alert.name">
                    <label for="alertQuery">Select Saved Query:</label>
                    <select id="alertQuery" v-model="currentQuery">
                        <option v-for="query in currentQueryOptions" :value="query"
                                :selected="query.name === alert.query">{{query.title || query.name}}</option>
                    </select>
                </div>
                <!-- Section for defining the condition which match of will trigger the alert -->
                <div class="configuration">
                    <div class="header">Alert Trigger</div>
                    <div>Monitor selected query and test whether devices number...</div>
                    <div class="content">
                        <x-checkbox :class="{'grid-span2': !alert.triggers.increase}" label="Increased"
                                  v-model="alert.triggers.increase"/>
                        <div class="form-inline" v-if="alert.triggers.increase">
                            <label for="TriggerAbove">Above:</label>
                            <input id="TriggerAbove" type="number" v-model="alert.triggers.above"  min="0">
                        </div>
                        <x-checkbox :class="{'grid-span2': !alert.triggers.decrease}" label="Decrease"
                                  v-model="alert.triggers.decrease" />
                        <div class="form-inline" v-if="alert.triggers.decrease">
                            <label for="TriggerBelow">Below:</label>
                            <input id="TriggerBelow" type="number" v-model="alert.triggers.below" min="0">
                        </div>
                        <x-checkbox class="grid-span2" label="Not Changed" v-model="alert.triggers.no_change"/>
                    </div>
                </div>
                <div class="configuration">
                    <div class="header">Alert Severity</div>
                    <div class="content">
                        <div class="grid-span2">
                            <input id="SeverityInfo" type="radio" value="info" v-model="alert.severity">
                            <label for="SeverityInfo" class="ml-2">
                                <svg-icon name="symbol/info" :original="true" height="16"></svg-icon>Info</label>
                        </div>
                        <div class="grid-span2">
                            <input id="SeverityWarning" type="radio" value="warning" v-model="alert.severity">
                            <label for="SeverityWarning" class="ml-2">
                                <svg-icon name="symbol/warning" :original="true" height="16"></svg-icon>Warning</label>
                        </div>
                        <div class="grid-span2">
                            <input id="SeverityError" type="radio" value="error" v-model="alert.severity">
                            <label for="SeverityError" class="ml-2">
                                <svg-icon name="symbol/error" :original="true" height="16"></svg-icon>Error</label>
                        </div>
                    </div>
                </div>
                <!-- group for defining what action will occur upon trigger -->
                <div class="configuration">
                    <div class="header">Action</div>
                    <div class="content">
                        <x-checkbox class="grid-span2" label="Push a system notification" v-model="actions.notification"/>
                        <x-checkbox class="grid-span2" label="Create ServiceNow Incident" v-model="actions.servicenow"/>
                        <x-checkbox class="grid-span2" label="Notify Syslog" v-model="actions.syslog" @change="checkSyslogSettings"/>
                        <x-checkbox :class="{'grid-span2': !actions.mail}" label="Send an Email"
                                    v-model="actions.mail" @change="checkMailSettings"/>
                        <template v-if="actions.mail">
                            <vm-select v-model="mailList" multiple filterable allow-create placeholder=""
                                   no-data-text="Type mail addresses..." :default-first-option="true"/>
                        </template>
                        <template v-if="alert.triggers.increase">
                            <x-checkbox :class="{'grid-span2': !actions.tag}" label="Tag Entities" v-model="actions.tag"/>
                            <template v-if="actions.tag">
                                <input class="form-control" id="tagName" v-model="tagName">
                            </template>
                        </template>
                    </div>
                </div>
                <div class="footer">
                    <div class="error-text">{{ error || '&nbsp;' }}</div>
                    <div class="actions">
                        <a class="x-btn link" @click="returnToAlerts">Cancel</a>
                        <a class="x-btn" :class="{disabled: !complete}" @click="saveAlert">Save</a>
                    </div>
                </div>
            </form>
        </x-box>
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
    import xBox from '../../components/layout/Box.vue'
    import xCheckbox from '../../components/inputs/Checkbox.vue'
    import Modal from '../../components/popover/Modal.vue'

    import { mapState, mapMutations, mapActions } from 'vuex'
	import { FETCH_DATA_QUERIES } from '../../store/actions'
    import { UPDATE_EMPTY_STATE } from '../../store/modules/onboarding'
    import { SET_ALERT, UPDATE_ALERT, FETCH_ALERTS } from '../../store/modules/alert'

	export default {
		name: 'alert-config-container',
		components: {
            xPage, xBox, xCheckbox, Modal },
		computed: {
            ...mapState({
                alertData: state => state.alert.current.data,
                alerts: state => state.alert.content.data,
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
                },
                globalSettings(state) {
					return state.configurable.core.CoreService.config
                }
			}),
            complete() {
            	if (!this.alert.name || !this.currentQuery.name) return false

            	if ((this.actions.mail && this.emptySettings['mail'])
                    || (this.actions.syslog && this.emptySettings['syslog'])) return false

                if ((this.alertData.id === "new" || this.alert.name !== this.alertData.name)
					&& this.alerts.some(e => e.name === this.alert.name)) {
					this.error = 'An Alert with that name already exists, please choose a different one.'
					return false
                }
                this.error = ''
                return true
            }
        },
        data() {
			return {
                /* Control of the criteria parameter with the use of two conditions */
                alert: { triggers: {}, actions: [] },
                currentQuery: {},
                actions: {
                	notification: false, mail: false, tag: false, syslog: false, servicenow: false
                },
                mailList: [],
                tagName: '',
                error: '',
				emptySettings: {
                	'mail': false,
                    'syslog': false
                }
            }
		},
        watch: {
			alertData(newAlertData) {
				this.fillAlert(newAlertData)
            }
        },
        methods: {
            ...mapMutations({ setAlert: SET_ALERT, updateEmptyState: UPDATE_EMPTY_STATE }),
            ...mapActions({
                fetchQueries: FETCH_DATA_QUERIES, updateAlert: UPDATE_ALERT, fetchAlerts: FETCH_ALERTS
            }),
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
                            break
                        case 'notify_syslog':
                            this.actions.syslog = true
                            break
                        case 'create_service_now_incident':
                            this.actions.servicenow = true
					}
				})
				this.alert = { ...alert,
                    triggers: { ...alert.triggers },
                    actions: []
                }
            },
			saveAlert() {
            	/* Validation */
                if (!this.complete) return

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
                if (this.actions.syslog) {
                    this.alert.actions.push({
                        type: 'notify_syslog'
                    })
                }
                if (this.actions.servicenow) {
                    this.alert.actions.push({
                        type: 'create_service_now_incident'
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
            checkMailSettings(on) {
            	if (!on) {
					this.updateEmptyState({ mailSettings: false})
				} else if (!this.globalSettings.email_settings.enabled) {
					this.updateEmptyState({ mailSettings: true})
					this.updateEmptyState({ syslogSettings: false})
					this.emptySettings['mail'] = true
				}
            },
            checkSyslogSettings(on) {
				if (!on) {
					this.updateEmptyState({ syslogSettings: false})
				} else if (!this.globalSettings.syslog_settings.enabled) {
					this.updateEmptyState({ syslogSettings: true })
					this.updateEmptyState({ mailSettings: false})
					this.emptySettings['syslog'] = true
				}
            }
        },
        created() {
			/*
			    If no alert from controls source, try and fetch it.
			    Otherwise, if alert from controls source has correct id, update local alert controls with its values
			 */
            if (!this.alerts.length || !this.alertData || !this.alertData.id || (this.$route.params.id !== this.alertData.id)) {
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
        .x-grid {
            width: 600px;
            grid-template-columns: 1fr 2fr;
            grid-gap: 8px;
            label {
                white-space: nowrap;
            }
        }
        .checkbox.inline.checked {
            display: inline;
        }
        .footer {
            display: flex;
            .error-text {
                flex: 1 0 auto;
            }
        }
        .configuration {
            margin: 24px 0;
            .header {
                color: $theme-orange;
                font-size: 18px;
            }
            .content {
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
                .svg-icon {
                    margin-right: 8px;
                }
            }
        }
    }
</style>