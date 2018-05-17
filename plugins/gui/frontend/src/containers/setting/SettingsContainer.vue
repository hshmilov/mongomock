<template>
    <x-page title="Settings" class="settings">
        <tabs>
            <tab title="Lifecycle Settings" id="research-settings-tab" selected="true">
                <h3>Discovery Phase</h3>
                <div class="grid grid-col-2">
                    <label for="schedule" class="label">Next Scheduled Time:</label>
                    <x-date-edit id="schedule" :value="nextResearchStart" @input="scheduleResearch" :limit="limit"/>
                    <label for="research_rate" class="label">Schedule Rate (hours)</label>
                    <div class="grid-item">
                        <input id="research_rate" type="number" min="0" v-model="lifecycle.researchRate">
                        <a class="btn set" @click="setResearchRate">Set</a>
                    </div>
                </div>
                <h3>Execution</h3>
                <toggle-button id="toggle" :value="lifecycle.executionEnabled" color="#FF7D46" :sync="true"
                               :labels="true" @change="toggleExecution"/>
            </tab>
            <tab title="Email Settings" id="email-settings-tab">
                <h3>Mail Server</h3>
                <div class="grid grid-col-2">
                    <x-schema-form :schema="schema" v-model="smtpSettings" @validate="updateValidity"
                                   @submit="setEmailServer" api-upload="email_server"/>
                    <div/><button class="x-btn" :class="{'disabled':!complete}" @click="setEmailServer">Save</button>
                </div>
            </tab>
            <tab title="System Settings" id="system-settings-tab">
                <h3>Data Tables</h3>
                <div class="grid grid-col-2">
                    <label for="refresh-rate">Auto-Refresh Rate (seconds)</label>
                    <input id="refresh-rate" type="number" min="0" v-model="refreshRate">

                    <label for="single-adapter">Use Single Adapter View</label>
                    <checkbox id="single-adapter" v-model="singleAdapter"/>

                    <label for="multi-line">Use Table Multi Line View</label>
                    <checkbox id="multi-line" v-model="multiLine"/>

                    <label for="default-sort">Sort by Number of Adapters in Default View</label>
                    <checkbox id="default-sort" v-model="defaultSort"/>
                    <div/>
                    <button class="btn confirm" @click="saveSystemSettings">save</button>
                </div>
                <div class="row">
                </div>
            </tab>
            <tab title="Okta Settings" id="okta-settings-tab">
                <h3>Okta enabled</h3>
                    <toggle-button id="toggle" :value="okta.okta_enabled" color="#FF7D46" :sync="true" :labels="true"
                    @change="okta.okta_enabled = !okta.okta_enabled"/>

                <div class="grid grid-col-2" v-if="okta.okta_enabled">
                    <label for="okta-client-id">Client ID</label>
                    <input id="okta-client-id" type="text" min="0" v-model="okta.okta_client_id">

                    <label for="okta-client-secret">Client Secret</label>
                    <input id="okta-client-secret" type="text" min="0" v-model="okta.okta_client_secret">

                    <label for="okta-url">Okta server URL</label>
                    <input id="okta-url" type="text" min="0" v-model="okta.okta_url">

                    <label for="app-url">GUI URL</label>
                    <input id="app-url" type="text" min="0" v-model="okta.gui_url">
                    <div/>
                </div>
                <div class="row">
                </div>
                <button class="btn confirm" @click="saveOktaSettings">save</button>
            </tab>
        </tabs>
        <modal v-if="message">
            <div slot="body">
                <div class="show-space">{{message}}</div>
            </div>
            <button class="x-btn" slot="footer" @click="closeModal">OK</button>
        </modal>
    </x-page>
</template>

<script>
    import xSchemaForm from '../../components/schema/SchemaForm.vue'
	import xPage from '../../components/layout/Page.vue'
	import Card from '../../components/Card.vue'
	import Tabs from '../../components/tabs/Tabs.vue'
	import Tab from '../../components/tabs/Tab.vue'
	import xDateEdit from '../../components/controls/string/DateEdit.vue'
	import Checkbox from '../../components/Checkbox.vue'
    import Modal from '../../components/popover/Modal.vue'

	import { FETCH_LIFECYCLE } from '../../store/modules/dashboard'
	import {
		UPDATE_REFRESH_RATE,
		UPDATE_SINGLE_ADAPTER,
		UPDATE_MULTI_LINE,
        DEFAULT_SORT_SETTINGS,
		SAVE_SETTINGS
	} from '../../store/modules/settings'
	import { REQUEST_API, START_RESEARCH_PHASE, STOP_RESEARCH_PHASE } from '../../store/actions'
	import { mapState, mapMutations, mapActions } from 'vuex'
    import {SAVE_PLUGIN_CONFIG, LOAD_PLUGIN_CONFIG} from "../../store/modules/plugin";

	export default {
		name: 'settings-container',
		components: {xPage, Card, Tabs, Tab, xDateEdit, Checkbox, xSchemaForm, Modal},
		computed: {
			...mapState(['dashboard', 'settings']),
			limit () {
				return [{
					type: 'fromto',
					from: `${new Date().toDateString()} ${new Date().toTimeString()}`
				}]
			},
            schema() {
                return {
                    type: 'array', items: [
                        {name: 'smtpHost', title: 'Host', type: 'string'},
                        {name: 'smtpPort', title: 'Port', type: 'string'},
                        {name: 'smtpUser', title: 'User Name', type: 'string'},
                        {name: 'smtpPassword', title: 'Password', type: 'string', format: 'password'},
                        {name: 'smtpKey', title: 'TLS 1.2 Key File', description: 'The binary contents of the key file', type: 'file'},
                        {name: 'smtpCert', title: 'TLS 1.2 Cert File', description: 'The binary contents of the cert file', type: 'file'}
                    ], required: ['smtpHost', 'smtpPort']
                }
            },
			nextResearchStart () {
				let tempDate = new Date(parseInt(this.dashboard.lifecycle.data.nextRunTime) * 1000)
				return `${tempDate.toLocaleDateString()} ${tempDate.toLocaleTimeString()}`
			},
			refreshRate: {
				get () {
					return this.settings.data.refreshRate
				},
				set (refreshRate) {
					this.updateRefreshRate(parseInt(refreshRate))
				}
			},
			singleAdapter: {
				get () {
					return this.settings.data.singleAdapter
				},
				set (singleAdapter) {
					this.updateSingleAdapter(singleAdapter)
				}
			},
			multiLine: {
				get () {
					return this.settings.data.multiLine
				},
				set (multiLine) {
                    this.updateMultiLine(multiLine)
				}
			},
			defaultSort: {
				get () {
					return this.settings.data.defaultSort
				},
				set (defaultSort) {
                    this.updateDefaultSort(defaultSort)
				}
			}
		},
		data () {
			return {
			    smtpSettings: {
                    smtpHost: '',
                    smtpPort: '',
                    smtpUser: '',
                    smtpPassword: '',
                    smtpCert: '',
                    smtpKey: ''
                },
				lifecycle: {
					executionEnabled: false,
					researchRate: 0
				},
                okta: {
			        okta_enabled: false,
                    okta_client_id: null,
                    okta_client_secret: null,
                    okta_url: null,
                    gui_url: null,
                },
                complete: false,
                message: ''
			}
		},
		methods: {
			...mapMutations({
				updateRefreshRate: UPDATE_REFRESH_RATE,
				updateSingleAdapter: UPDATE_SINGLE_ADAPTER,
                updateMultiLine: UPDATE_MULTI_LINE,
                updateDefaultSort: DEFAULT_SORT_SETTINGS
			}),
			...mapActions({
				fetchLifecycle: FETCH_LIFECYCLE,
				fetchData: REQUEST_API,
				saveSettings: SAVE_SETTINGS,
                startResearch: START_RESEARCH_PHASE,
                stopResearch: STOP_RESEARCH_PHASE,
                updatePluginConfig: SAVE_PLUGIN_CONFIG,
                loadPluginConfig: LOAD_PLUGIN_CONFIG
			}),
			toggleExecution (executionEnabled) {
				let param = `enable`
				if (!executionEnabled.value) {
					param = `disable`
				}
				this.fetchData({
					rule: `execution/${param}`,
					method: 'POST'
				})
				this.executionEnabled = executionEnabled.value
			},
			scheduleResearch (scheduleDate) {
				this.fetchData({
					rule: `research_phase`,
					method: 'POST',
					data: {timestamp: scheduleDate}
				})
			},
			setResearchRate () {
                if (!this.lifecycle.researchRate || this.lifecycle.researchRate <= 0) {
                    this.message = 'The Inserted Auto-Refresh Rate is invalid, please insert a number larger than 0.'
                    return
                }

				this.fetchData({
					rule: `dashboard/lifecycle_rate`,
					method: 'POST',
					data: {system_research_rate: this.lifecycle.researchRate * 60 * 60}
				}).then((response) => {
                    if (response.status === 200) {
                        this.message = 'Saved Successfully.'
                    }

                })
			},
			setEmailServer () {
                if (!this.complete) return
				this.fetchData({
					rule: `email_server`,
					method: 'POST',
					data: this.smtpSettings
				}).then((response) => {
                    if (response.status === 201) {
                        this.message = 'Saved Successfully.'
                    }

                })
			},
            updateValidity(valid) {
                this.complete = valid
            },
            saveSystemSettings() {
			    if (!this.refreshRate || this.refreshRate <= 0) {
			        this.message = 'The Inserted Auto-Refresh Rate is invalid, please insert a number larger than 0.'
                    return
                }

			    this.saveSettings().then((response) => {
                    if (response.status === 200) {
                        this.message = 'Saved Successfully.'
                    }
                })
            },
            saveOktaSettings() {
                this.updatePluginConfig({
                    pluginId: 'gui',
                    config_name: 'GuiService',
                    config: this.okta
                }).then(response =>{
                    if (response.status === 200) {
                        this.message = 'Saved Successfully.'
                    }

                })
            },
            closeModal() {
                this.message = ''
            }
		},
		created () {
			this.fetchLifecycle()
			this.fetchData({
				rule: 'execution'
			}).then((response) => {
				this.lifecycle.executionEnabled = (response.data === 'enabled')
			})
			this.fetchData({
				rule: 'dashboard/lifecycle_rate'
			}).then((response) => {
				this.lifecycle.researchRate = response.data / 60 / 60
			})
			this.fetchData({
				rule: 'email_server'
			}).then((response) => {
			    if (response.data) this.smtpSettings = response.data
			})
            this.loadPluginConfig({
                pluginId: 'gui',
                configName: 'GuiService'
            }).then((response) => {
                this.okta = response.data.config
            })
		}
	}
</script>

<style lang="scss">
    .settings {
        .grid {
            display: grid;
            grid-row-gap: 12px;
            width: 600px;
            align-items: center;
            grid-auto-rows: auto;
            margin-bottom: 24px;
            &.grid-col-2 {
                grid-template-columns: 2fr 3fr;
            }
            .grid-item {
                text-align: right;
            }
        }
        .btn {
            width: auto;
        }
        #research_rate {
            width: 80px;
        }
        input.cov-datepicker {
            width: 100%;
        }
        label {
            margin-bottom: 0;
        }
        .btn.confirm {
            justify-self: end;
        }
    }
</style>
