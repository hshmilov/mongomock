<template>
    <x-page :breadcrumbs="[
    	{ title: 'alerts', path: {name: 'Alerts'}},
    	{ title: (alertData.name? alertData.name : 'new alert')}
    ]">
        <x-box class="alert-config">
            <form @keyup.enter="saveAlert">
                <!-- Section for alert name and query to run by -->
                <div class="x-grid">
                    <label for="alert_name">Alert Name:</label>
                    <input id="alert_name" v-model="alert.name" @input="tour('alertQuery')">
                    <label for="alert_query">Select Saved Query:</label>
                    <x-select :options="currentQueryOptions" v-model="currentQuery" placeholder="query..."
                              :searchable="true" id="alert_query" @input="tour('alertIncreased')" />
                </div>

                <!-- Section for defining the condition which match of will trigger the alert -->
                <div class="configuration">
                    <div class="header">Alert Period</div>
                    <div>How often would you like to receive this alert?</div>
                    <div class="content">
                        <div class="grid-span2">
                            <input id="WeeklyPeriod" type="radio" value="weekly" v-model="alert.period">
                            <label for="WeeklyPeriod" class="ml-2">Weekly</label>
                        </div>
                        <div class="grid-span2">
                            <input id="DailyPeriod" type="radio" value="daily" v-model="alert.period">
                            <label for="DailyPeriod" class="ml-2">Daily</label>
                        </div>
                        <div class="grid-span2">
                            <input id="EveryPhasePeriod" type="radio" value="all" v-model="alert.period">
                            <label for="EveryPhasePeriod" class="ml-2">Every Research Phase</label>
                        </div>
                    </div>
                </div>
                <div class="configuration">
                    <div class="header">Alert Trigger</div>
                    <div>Monitor selected query and test whether devices number...</div>
                    <div class="content">
                        <x-checkbox label="Increased" v-model="alert.triggers.increase" id="alert_increased"
                                    @change="tour('alertAbove')" />
                        <div class="form-inline" v-show="alert.triggers.increase">
                            <label for="alert_above">Above:</label>
                            <input id="alert_above" type="number" v-model="alert.triggers.above" min="0" @input="tour('alertAction')">
                        </div><div v-if="!alert.triggers.increase"></div>
                        <x-checkbox label="Decreased" v-model="alert.triggers.decrease" />
                        <div class="form-inline" v-show="alert.triggers.decrease">
                            <label for="TriggerBelow">Below:</label>
                            <input id="TriggerBelow" type="number" v-model="alert.triggers.below" min="0" >
                        </div><div v-if="!alert.triggers.decrease"></div>
                        <x-checkbox class="grid-span2" label="Not Changed" v-model="alert.triggers.no_change"/>
                    </div>
                </div>
                <div class="configuration">
                    <div class="header">Alert Severity</div>
                    <div class="content">
                        <div class="grid-span2">
                            <input id="SeverityInfo" type="radio" value="info" v-model="alert.severity">
                            <label for="SeverityInfo" class="ml-2">
                                <svg-icon name="symbol/info" :original="true" height="16"></svg-icon>
                                Info</label>
                        </div>
                        <div class="grid-span2">
                            <input id="SeverityWarning" type="radio" value="warning" v-model="alert.severity">
                            <label for="SeverityWarning" class="ml-2">
                                <svg-icon name="symbol/warning" :original="true" height="16"></svg-icon>
                                Warning</label>
                        </div>
                        <div class="grid-span2">
                            <input id="SeverityError" type="radio" value="error" v-model="alert.severity">
                            <label for="SeverityError" class="ml-2">
                                <svg-icon name="symbol/error" :original="true" height="16"></svg-icon>
                                Error</label>
                        </div>
                    </div>
                </div>
                <!-- group for defining what action will occur upon trigger -->
                <div class="configuration">
                    <div class="header">Action</div>
                    <div class="content">
                        <x-checkbox label="Push a system notification" id="alert_notification"
                                    v-model="actions.notification" @change="tour('alertSave')" /><div></div>
                        <x-checkbox class="grid-span2" label="Create ServiceNow Incident" v-model="actions.servicenowIncident"/>
                        <x-checkbox class="grid-span2" label="Create ServiceNow Computer" v-model="actions.servicenowComputer"/>
                        <!-- SYSLOG -->
                        <x-checkbox label="Notify Syslog" v-model="actions.syslog" @change="checkSyslogSettings"/>
                        <x-checkbox v-if="actions.syslog" label="Send Device Data To Syslog" v-model="sendAllDevicesToSyslog"/>
                        <div v-if="!actions.syslog"></div>
                        <!-- SYSLOG -->
                        <!-- MAIL -->
                        <x-checkbox label="Send an Email" v-model="actions.mail" @change="checkMailSettings"/>
                        <vm-select v-if="actions.mail" v-model="mailList" no-data-text="Type mail addresses..."
                                   placeholder="" multiple filterable allow-create :default-first-option="true" />
                        <div v-if="!actions.mail"></div>
                        <!-- MAIL -->
                        <!-- TAGS -->
                        <template v-if="alert.triggers.increase">
                            <x-checkbox :class="{'grid-span2': !actions.tag}" label="Tag New Entities"
                                        v-model="actions.tag"/>
                            <input class="form-control" id="tagName" v-model="tagName" v-if="actions.tag">
                            <div v-if="!actions.tag"></div>
                        </template>
                        <!-- TAGS -->
                    </div>
                </div>
                <div class="footer">
                    <div class="error-text">{{ error || '&nbsp;' }}</div>
                    <div class="actions" id="alert_save">
                        <a class="x-btn link" @click="returnToAlerts">Cancel</a>
                        <a class="x-btn" :class="{disabled: !complete}" @click="saveAlert">Save</a>
                    </div>
                </div>
            </form>
        </x-box>
    </x-page>
</template>

<script>
    import xSelect from '../../components/inputs/Select.vue'
    import xPage from '../../components/layout/Page.vue'
    import xBox from '../../components/layout/Box.vue'
    import xCheckbox from '../../components/inputs/Checkbox.vue'
    import Modal from '../../components/popover/Modal.vue'

    import {mapState, mapMutations, mapActions} from 'vuex'
    import {FETCH_DATA_VIEWS} from '../../store/actions'
    import {UPDATE_EMPTY_STATE} from '../../store/modules/onboarding'
    import {SET_ALERT, UPDATE_ALERT, FETCH_ALERTS} from '../../store/modules/alert'
    import { CHANGE_TOUR_STATE } from '../../store/modules/onboarding'

    export default {
        name: 'alert-config-container',
        components: {
            xSelect, xPage, xBox, xCheckbox, Modal
        },
        computed: {
            ...mapState({
                alertData: state => state.alert.current.data,
                alerts: state => state.alert.content.data,
                currentQueryOptions(state) {
                    let queries = [...state.devices.views.saved.data.map((item) => {
                        return {...item, entity: 'devices'}
                    }), ...state.users.views.saved.data.map((item) => {
                        return {...item, entity: 'users'}
                    })]
                    if (!queries || !queries.length) return []
                    if (this.alert && this.alert.view) {
                        let hasCurrent = queries.some(query => query.name === this.alert.view)
                        if (!hasCurrent) {
                            queries.push({
                                name: this.alert.view, title: `${this.alert.view} (deleted)`
                            })
                        }
                    }
                    return queries.map(q => {return {...q, title: q.title ? q.title : q.name}})
                },
                globalSettings(state) {
                    return state.configurable.core.CoreService.config
                },
                selectedOption() {
				    if (!this.currentQuery) return undefined
				    return this.currentQueryOptions.find(option => (option.name === this.currentQuery))
                }
            }),
            complete() {
                if (!this.alert.name || !this.currentQuery) return false

                if ((this.actions.mail && this.emptySettings['mail'])
                    || (this.actions.syslog && this.emptySettings['syslog'])) return false

                if ((this.alertData.id === "new" || this.alert.name !== this.alertData.name)
                    && this.alerts.some(e => e.name === this.alert.name)) {
                    this.error = 'An Alert with that name already exists, please choose a different one.'
                    return false
                }
                this.error = ''
                return true
            },
            triggerAbove() {
            	return this.alert.triggers.above
            },
			triggerBelow() {
				return this.alert.triggers.below
			}
		},
        data() {
            return {
                /* Control of the criteria parameter with the use of two conditions */
                alert: {
                	triggers: {
                		above: null, below: null
                    }, actions: []
                },
                currentQuery: null,
                actions: {
                	notification: false, mail: false, tag: false, syslog: false, servicenowIncident: false, servicenowComputer: false
                },
                mailList: [],
                tagName: '',
                sendAllDevicesToSyslog: false,
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
            },
            triggerAbove(newAbove) {
            	if (newAbove) {
            		this.alert.triggers.above = this.alert.triggers.above.replace('-', '').replace('e', '')
                }
            },
			triggerBelow(newBelow) {
				if (newBelow) {
					this.alert.triggers.below = this.alert.triggers.below.replace('-', '').replace('e', '')
				}
			}
        },
        methods: {
            ...mapMutations({
                setAlert: SET_ALERT, updateEmptyState: UPDATE_EMPTY_STATE, changeState: CHANGE_TOUR_STATE
            }),
            ...mapActions({
                fetchView: FETCH_DATA_VIEWS, updateAlert: UPDATE_ALERT, fetchAlerts: FETCH_ALERTS
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
                            this.sendAllDevicesToSyslog = action.data
                            break
                        case 'create_service_now_incident':
                            this.actions.servicenowIncident = true
                            break
                        case 'create_service_now_computer':
                            this.actions.servicenowComputer = true
                            break
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
                        type: 'notify_syslog', data: this.sendAllDevicesToSyslog
                    })
                }
                if (this.actions.servicenowIncident) {
                    this.alert.actions.push({
                        type: 'create_service_now_incident'
                    })
                }
                if (this.actions.servicenowComputer) {
                    this.alert.actions.push({
                        type: 'create_service_now_computer'
                    })
                }
                this.alert.view = this.currentQuery
                this.alert.viewEntity = this.currentQueryOptions.find(item => item.name === this.currentQuery).entity
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
            },
            tour(stateName) {
            	this.changeState({ name: stateName })
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
            this.tour('alertName')

            /* Fetch all saved queries for offering user to base alert upon */
            Promise.all([this.fetchView({module: 'devices', type: 'saved'}),
                this.fetchView({module: 'users', type: 'saved'})]).then(() => {
                    if (this.alertData.view) {
                        let matching = this.currentQueryOptions.filter(item =>
                            (this.alertData.id === 'new' ? item.uuid : item.name) === this.alertData.view)
                        if (matching.length) {
                            this.currentQuery = matching[0].name
                            this.alert.view = this.currentQuery
                            this.alert.viewEntity = this.selectedOption.entity
                        } else {
                            this.alert.view = ''
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