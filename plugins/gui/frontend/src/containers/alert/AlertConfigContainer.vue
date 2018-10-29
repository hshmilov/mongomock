<template>
    <x-page :breadcrumbs="[
    	{ title: 'alerts', path: {name: 'Alerts'}},
    	{ title: (alertData.name? alertData.name : 'New alert')}
    ]">
        <x-box class="alert-config">
            <div class="v-spinner-bg" v-if="loading"></div>
            <pulse-loader :loading="loading" color="#FF7D46" />
            <form @keyup.enter="saveAlert">
                <!-- Section for alert name and query to run by -->
                <div class="x-grid">
                    <label for="alert_name">Alert name:</label>
                    <input id="alert_name" v-model="alert.name" @input="tour('alertQuery')">
                    <label for="alert_query">Select saved query:</label>
                    <x-select :options="currentQueryOptions" v-model="currentQuery" placeholder="query..."
                              :searchable="true" id="alert_query" @input="tour('alertIncreased')" />
                </div>

                <!-- Section for defining the condition which match of will trigger the alert -->
                <div class="configuration">
                    <div class="header">Alert period</div>
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
                            <label for="EveryPhasePeriod" class="ml-2">Every discovery phase</label>
                        </div>
                    </div>
                </div>
                <div class="configuration">
                    <div class="header">Alert trigger</div>
                    <div>Monitor selected query and raise alert whether...</div>
                    <div class="content">
                        <x-checkbox class="grid-span2" label="Every discovery cycle" v-model="alert.triggers.every_discovery" 
                                    title="Trigger alert for each discovery cycle, regardless of results" />
                        <x-checkbox class="grid-span2" label="New entities were added to query results" v-model="alert.triggers.new_entities"
                                    title="For each discovery cycle, trigger alert if the given saved query discovered an entity that wasn't discovered for the same saved query in the previous cycle" />
                        <x-checkbox class="grid-span2" label="Previous entities were subtracted from query results" v-model="alert.triggers.previous_entities"
                                    title="For each discovery cycle, trigger alert if the given saved query didn't discover an entity that was discovered for the same saved query in the previous cycle" />
                        <x-checkbox label="The number of query results is above" v-model="alert.triggers.increase" id="alert_increased"
                                    title="Trigger alert if the number of entities that was discovered from the given saved query is above the given threshold"
                                    @change="tour('alertAbove')" />
                        <div class="form-inline" >
                            <input id="alert_above" type="number" v-model="alert.triggers.above" min="0" v-on:keypress="isNumber($event)" @input="tour('alertAction')" :disabled="!alert.triggers.increase" >
                        </div>
                        <x-checkbox label="The number of query results is below" v-model="alert.triggers.decrease"
                                    title="Trigger alert if the number of entities that was discovered from the given saved query is below the given threshold" />
                        <div class="form-inline" >
                            <input id="TriggerBelow" type="number" v-model="alert.triggers.below" min="0" v-on:keypress="isNumber($event)" :disabled="!alert.triggers.decrease">
                        </div>
                    </div>
                </div>
                <div class="configuration">
                    <div class="header">Alert severity</div>
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
                        <x-checkbox class="grid-span2" label="Create ServiceNow incident" v-model="actions.servicenowIncident"/>
                        <x-checkbox class="grid-span2" label="Create ServiceNow computer" v-model="actions.servicenowComputer"/>
                        <x-checkbox class="grid-span2" label="Create FreshService incident" v-model="actions.freshserviceIncident"/>
                        <div v-if="actions.freshserviceIncident" class="x-grid">
                            <label for="ticket_email">Email for Fresh Service Ticket:</label>
                            <input id="ticket_email" v-model="ticketEmail">
                        </div>
                        <div v-if="!actions.freshserviceIncident"></div>
                        <x-checkbox class="grid-span2" label="Isolate CB response devices" v-model="actions.cbIsolate"/>
                        <x-checkbox class="grid-span2" label="Unisolate CB response devices" v-model="actions.cbUnisolate"/>
                        <!-- SYSLOG -->
                        <x-checkbox label="Notify syslog" v-model="actions.syslog" @change="checkSyslogSettings"/>
                        <x-checkbox v-if="actions.syslog" label="Send Device Data To Syslog" v-model="sendAllDevicesToSyslog"/>
                        <div v-if="!actions.syslog"></div>
                        <!-- SYSLOG -->
                        <!-- MAIL -->
                        <x-checkbox label="Send an Email" v-model="actions.mail" @change="checkMailSettings"/>
                        <x-checkbox v-if="actions.mail" label="Attach Entity Data CSV" v-model="sendDevicesCSVToEmail"/>
                        <vm-select v-if="actions.mail" v-model="mailList" no-data-text="Type mail addresses..."
                                   placeholder="" multiple filterable allow-create :default-first-option="true" />
                        <div v-if="!actions.mail"></div>
                        <!-- MAIL -->
                        <!-- TAGS -->
                        <x-checkbox class="grid-span2" label="Tag all entities" v-model="actions.tagAll"/>
                        <input class="form-control" id="tagAllName" v-model="tagAllName" v-if="actions.tagAll">
                        <div v-if="!actions.tagAll"></div>
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
                        <button class="x-btn link" @click.prevent="returnToAlerts">Cancel</button>
                        <button class="x-btn" :class="{disabled: !complete}" @click.prevent="saveAlert">Save</button>
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
	import PulseLoader from 'vue-spinner/src/PulseLoader.vue'

    import {mapState, mapMutations, mapActions} from 'vuex'
    import {FETCH_DATA_VIEWS} from '../../store/actions'
    import {UPDATE_EMPTY_STATE} from '../../store/modules/onboarding'
    import {SET_ALERT, UPDATE_ALERT, FETCH_ALERTS} from '../../store/modules/alert'
    import { CHANGE_TOUR_STATE } from '../../store/modules/onboarding'
    import { entities } from '../../constants/entities'

    export default {
        name: 'alert-config-container',
        components: {
            xSelect, xPage, xBox, xCheckbox, Modal, PulseLoader
        },
        computed: {
            ...mapState({
                alertData: state => state.alert.current.data,
                alerts: state => state.alert.content.data,
                availableModules(state) {
                    if (!state.auth.currentUser.data) return {}
                    let permissions = state.auth.currentUser.data.permissions
                    return entities.filter(entity => {
                        return permissions[entity.name] !== 'Restricted'
                    }).map(module => module.name)
                },
                currentQueryOptions(state) {
                    let queries = []
                    this.availableModules.forEach(entity => {
                        queries.push(...state[entity].views.saved.data.map((item) => {
                            return { ...item, entity }
                        }))
                    })
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
                    if (!state.configuration || !state.configuration.data || !state.configuration.data.global) return
                    return state.configuration.data.global
                },
                selectedOption() {
				    if (!this.currentQuery) return undefined
				    return this.currentQueryOptions.find(option => (option.name === this.currentQuery))
                }
            }),
            complete() {
                if (!this.alert.name) {
                    this.error = 'Please specify alert name.'
                    return false
                }

                if ((this.alertData.id === "new" || this.alert.name !== this.alertData.name)
                    && this.alerts.some(e => e.name === this.alert.name)) {
                    this.error = 'An Alert with that name already exists, please choose a different one.'
                    return false
                }

                if (!this.currentQuery) {
                    this.error = 'Please select the saved query.'
                    return false
                }

                if (!this.alert.triggers.every_discovery && !this.alert.triggers.new_entities && !this.alert.triggers.previous_entities &&
                    !this.alert.triggers.increase && !this.alert.triggers.decrease) {
                    this.error = 'Please select one or more triggers.'
                    return false
                }

                if ((this.actions.mail && this.emptySettings['mail'])
                    || (this.actions.syslog && this.emptySettings['syslog'])) return false

                if (this.alert.triggers.increase) {
                    if (isNaN(this.alert.triggers.above) || !(typeof this.alert.triggers.above === 'number') || (this.alert.triggers.above <= 0)) {
                        this.error = 'Please enter a positive number for above field.'
                        return false
                    }
                }

                if (this.alert.triggers.decrease) {
                    if (isNaN(this.alert.triggers.below) || !(typeof this.alert.triggers.below === 'number') || (this.alert.triggers.below <= 0)) {
                        this.error = 'Please enter a positive number for below field.'
                        return false
                    }
                }

                this.error = ''
                return true
            },
            triggerAbove() {
            	return this.alert.triggers.above
            },
			triggerBelow() {
				return this.alert.triggers.below
			},
            triggerIncrease() {
                return this.alert.triggers.increase
            },
            triggerDecrease() {
                return this.alert.triggers.decrease
            },
            loading() {
            	return this.fetching.alert || this.fetching.views
            }
		},
        // Todo: do my fields have to be added to alert
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
                	notification: false, mail: false, tag: false, tagAll: false, syslog: false, servicenowIncident: false, servicenowComputer: false, cbIsolate: false, cbUnisolate: false, freshserviceIncident: false
                },
                mailList: [],
                tagName: '',
                tagAllName: '',
                ticketEmail: '',
                sendAllDevicesToSyslog: false,
                sendDevicesCSVToEmail: false,
                error: '',
                emptySettings: {
                    'mail': false,
                    'syslog': false
                },
                fetching: {
                	alert: false, views: false
                }
            }
        },
        watch: {
            alertData(newAlertData) {
                this.fillAlert(newAlertData)
            },
            triggerAbove(newAbove) {
            	if (newAbove) {
            		this.alert.triggers.above = parseInt(this.alert.triggers.above)
                }
            },
			triggerBelow(newBelow) {
				if (newBelow) {
            		this.alert.triggers.below = parseInt(this.alert.triggers.below)
				}
			},
            triggerIncrease(newIncrease) {
                if (!newIncrease) {
                    this.alert.triggers.above = 0
                }
            },
            triggerDecrease(newDecrease) {
                if (!newDecrease) {
                    this.alert.triggers.below = 0
                }
            },
        },
        methods: {
            ...mapMutations({
                setAlert: SET_ALERT, updateEmptyState: UPDATE_EMPTY_STATE, changeState: CHANGE_TOUR_STATE
            }),
            ...mapActions({
                fetchViews: FETCH_DATA_VIEWS, updateAlert: UPDATE_ALERT, fetchAlerts: FETCH_ALERTS
            }),
            isNumber: function(evt) {
                evt = (evt) ? evt : window.event;
                var charCode = (evt.which) ? evt.which : evt.keyCode;
                if (charCode > 31 && (charCode < 48 || charCode > 57)) {
                    evt.preventDefault();;
              } else {
                    return true;
              }
            },
            fillAlert(alert) {
                alert.actions.forEach((action) => {
                    switch (action.type) {
                        case 'create_notification':
                            this.actions.notification = true
                            break
                        case 'send_emails':
                            this.actions.mail = true
                            this.mailList = action.data.emailList
                            this.sendDevicesCSVToEmail = action.data.sendDeviceCSV
                            break
                        case 'tag_entities':
                            this.actions.tag = true
                            this.tagName = action.data
                            break
                        case 'tag_all_entities':
                            this.actions.tagAll = true
                            this.tagAllName = action.data
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
                        case 'create_fresh_service_incident':
                            this.actions.freshserviceIncident = true
                            this.ticketEmail = action.data
                            break
                        case 'carbonblack_isolate':
                            this.actions.cbIsolate = true
                            break
                        case 'carbonblack_unisolate':
                            this.actions.cbUnisolate = true
                            break
					}
				})
                if (alert.triggers.below) {
                    alert.triggers.decrease = true;
                }
                if (alert.triggers.above) {
                    alert.triggers.increase = true;
                }
                // Todo: do my fields have to be added to alert
				this.alert = { ...alert,
                    triggers: { ...alert.triggers },
                    actions: []
                }
            },
            fillView() {
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
                        type: 'send_emails', data: { emailList: this.mailList, sendDeviceCSV: this.sendDevicesCSVToEmail}
                    })
                }
                if (this.actions.tag) {
                    this.alert.actions.push({
                        type: 'tag_entities', data: this.tagName
                    })
                }
                if (this.actions.tagAll) {
                    this.alert.actions.push({
                        type: 'tag_all_entities', data: this.tagAllName
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
                if (this.actions.freshserviceIncident) {
                    this.alert.actions.push({
                        type: 'create_fresh_service_incident', data: this.ticketEmail
                    })
                }
                if (this.actions.cbIsolate) {
                    this.alert.actions.push({
                        type: 'carbonblack_isolate'
                    })
                }
                if (this.actions.cbUnisolate) {
                    this.alert.actions.push({
                        type: 'carbonblack_unisolate'
                    })
                }

                this.alert.view = this.currentQuery
                this.alert.viewEntity = this.currentQueryOptions.find(item => item.name === this.currentQuery).entity
                /* Save and return to alerts page */


                /* Don't ever send increase and decrease */
                delete this.alert.triggers.increase
                delete this.alert.triggers.decrease

                this.updateAlert(this.alert)
                this.returnToAlerts()
            },
            returnToAlerts() {
                this.$router.push({name: 'Alerts'})
            },
            checkMailSettings(on) {
            	if (!on) {
					this.updateEmptyState({ mailSettings: false})
				} else if (!this.globalSettings.mail) {
					this.updateEmptyState({ mailSettings: true})
					this.updateEmptyState({ syslogSettings: false})
					this.emptySettings['mail'] = true
				}
            },
            checkSyslogSettings(on) {
				if (!on) {
					this.updateEmptyState({ syslogSettings: false})
				} else if (!this.globalSettings.syslog) {
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
            	this.fetching.alert = true
                this.fetchAlerts({}).then(() => {
                    this.setAlert(this.$route.params.id)
                    this.fetching.alert = false
                })
            } else {
                this.fillAlert(this.alertData)
            }
            this.tour('alertName')

            /* Fetch all saved queries for offering user to base alert upon */
            this.fetching.views = true
            Promise.all(this.availableModules.map(module => this.fetchViews({module, type: 'saved'}))).then(() => {
                    this.fillView()
                    this.fetching.views = false
                }
            )
        }
    }
</script>

<style lang="scss">
    .alert-config {
        position: relative;
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
