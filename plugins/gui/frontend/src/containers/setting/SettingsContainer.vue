<template>
    <x-page title="Settings" class="settings">
        <tabs ref="tabs" @click="determineState">
            <tab title="Lifecycle Settings" id="research-settings-tab" :selected="true">
                <h3>Discovery Phase</h3>
                <div class="grid grid-col-2">
                    <label for="research_time" class="label">Next Scheduled Time:</label>
                    <div id="research_time">
                        <x-date-edit :value="nextResearchStart" @input="scheduleResearch" :limit="limit"/>
                    </div>
                </div>
                <div class="tab-settings">
                    <template v-if="configurable.system_scheduler">
                        <x-schema-form :schema="configurable.system_scheduler.SystemSchedulerService.schema" @validate="updateSystemSchedulerValidity"
                                       v-model="configurable.system_scheduler.SystemSchedulerService.config" api-upload="adapters/system_scheduler"/>
                        <div class="place-right">
                            <button class="x-btn" :class="{disabled: !coreComplete}" @click="saveSystemSchedulerSettings">Save</button>
                        </div>
                    </template>
                </div>
            </tab>
            <tab title="Global Settings" id="global-settings-tab">
                <div class="tab-settings">
                    <template v-if="configurable.core">
                        <x-schema-form :schema="configurable.core.CoreService.schema" @validate="updateCoreValidity"
                                       v-model="configurable.core.CoreService.config" api-upload="adapters/core"/>
                        <div class="place-right">
                            <button class="x-btn" :class="{disabled: !coreComplete}" @click="saveGlobalSettings">Save</button>
                        </div>
                    </template>
                </div>
            </tab>
            <tab title="GUI Settings" id="gui-settings-tab">
                <div class="tab-settings">
                    <template v-if="configurable.gui">
                        <x-schema-form :schema="configurable.gui.GuiService.schema" @validate="updateGuiValidity"
                                       v-model="configurable.gui.GuiService.config" api-upload="adapters/gui"/>
                        <div class="place-right">
                            <button class="x-btn" :class="{disabled: !guiComplete}" @click="saveGuiSettings">Save</button>
                        </div>
                    </template>
                </div>
            </tab>
            <tab title="Change admin password" id="change-admin-password">
                <div class="tab-settings">
                    <x-schema-form :schema="{type:'array','items':[
                        {
                            name: 'currentPassword',
                            title: 'Current password',
                            type: 'string',
                            format: 'password'
                        },
                        {
                            name: 'newPassword',
                            title: 'New password',
                            type: 'string',
                            format: 'password'
                        },
                        {
                            name: 'confirmNewPassword',
                            title: 'Confirm new password',
                            type: 'string',
                            format: 'password'
                        },
                     ], required: ['currentPassword', 'newPassword', 'confirmNewPassword']}"
                                   v-model="adminChangePassword"
                                   @validate="updateChangePassValidity"/>
                    <div class="place-right">
                        <button class="x-btn" :class="{disabled: !adminChangePasswordComplete}" @click="doChangePassword">
                            Save
                        </button>
                    </div>
                </div>
            </tab>
            <tab title="About" id="about-settings-tab">
                <div class="tab-settings">
                    <x-custom-data :data="system_info" :vertical="true"/>
                </div>
            </tab>
        </tabs>
        <x-toast v-if="message" :message="message" @done="removeToast" />
    </x-page>
</template>

<script>
    import xSchemaForm from '../../components/schema/SchemaForm.vue'
    import xCustomData from '../../components/schema/CustomData.vue'
    import xPage from '../../components/layout/Page.vue'
    import Tabs from '../../components/tabs/Tabs.vue'
    import Tab from '../../components/tabs/Tab.vue'
    import xDateEdit from '../../components/controls/string/DateEdit.vue'
    import xCheckbox from '../../components/inputs/Checkbox.vue'
    import xToast from '../../components/popover/Toast.vue'

    import { mapState, mapActions, mapMutations } from 'vuex'
    import { SAVE_PLUGIN_CONFIG, LOAD_PLUGIN_CONFIG, CHANGE_PLUGIN_CONFIG } from "../../store/modules/configurable";
    import { REQUEST_API, START_RESEARCH_PHASE, STOP_RESEARCH_PHASE } from '../../store/actions'
    import { CHANGE_TOUR_STATE } from '../../store/modules/onboarding'
    import { CHANGE_PASSWORD } from "../../store/modules/auth";

	export default {
        name: 'settings-container',
        components: { xPage, Tabs, Tab, xDateEdit, xCheckbox, xSchemaForm, xToast, xCustomData },
        computed: {
            ...mapState({
                nextResearchStart(state) {
					let tempDate = new Date(parseInt(state.dashboard.lifecycle.data.nextRunTime) * 1000)
					return `${tempDate.toLocaleDateString()} ${tempDate.toLocaleTimeString()}`
                },
                configurable(state) {
                    return state.configurable
                },
                userName(state) {
                	return state.auth.data.user_name
                }
            }),
            limit() {
            	let now = new Date()
                // now.setDate(now.getDate() - 1)
                return [{
                    type: 'fromto',
                    from: now
                }]
            },
            scheduleConfig: {
                get() {
                    if (!this.configurable.system_scheduler || !this.configurable.system_scheduler.SystemSchedulerService) {
                    	return null
					}
                    return this.configurable.system_scheduler.SystemSchedulerService.config
                }
            },
			validResearchRate() {
				return this.validNumber(this.scheduleConfig.system_research_rate)
            }
        },
        data() {
            return {
                coreComplete: true,
                guiComplete: true,
                message: '',
                system_info: {},
                adminChangePassword: {
                    currentPassword: null,
                    newPassword: null,
                    confirmNewPassword: null
                },
                adminChangePasswordComplete: false,
            }
        },
        methods: {
            ...mapMutations({
                changePluginConfig: CHANGE_PLUGIN_CONFIG, changeState: CHANGE_TOUR_STATE
            }),
            ...mapActions({
                fetchData: REQUEST_API,
                startResearch: START_RESEARCH_PHASE,
                stopResearch: STOP_RESEARCH_PHASE,
                updatePluginConfig: SAVE_PLUGIN_CONFIG,
                loadPluginConfig: LOAD_PLUGIN_CONFIG,
                changePassword: CHANGE_PASSWORD
            }),
            validNumber(value) {
				if (value === undefined || isNaN(value) || value <= 0) {
					return false
				}
				return true
            },
            scheduleResearch(scheduleDate) {
                this.fetchData({
                    rule: `research_phase`,
                    method: 'POST',
                    data: {timestamp: scheduleDate}
                }).then((response) => {
                	this.createToast(response)
				})
            },
            saveGlobalSettings() {
                if (!this.coreComplete) return
                this.updatePluginConfig({
                    pluginId: 'core',
                    configName: 'CoreService',
                    config: this.configurable.core.CoreService.config
                }).then(response => {
                    this.createToast(response)
                }).catch(error => {
                	if (error.response.status === 400) {
                		this.message = error.response.data.message
                    }
                })
            },
            saveSystemSchedulerSettings() {
                if (!this.system_schedulerComplete || !this.validResearchRate) return
                this.updatePluginConfig({
                    pluginId: 'system_scheduler',
                    configName: 'SystemSchedulerService',
                    config: this.scheduleConfig
                }).then(response => {
                    this.createToast(response)
                }).catch(error => {
                    if (error.response.status === 400) {
                		this.message = error.response.data.message
                    }
                })
            },
            updateSystemSchedulerValidity(valid) {
                this.system_schedulerComplete = valid
            },
            updateCoreValidity(valid) {
                this.coreComplete = valid
            },
            updateGuiValidity(valid) {
                this.guiComplete = valid
            },
            updateChangePassValidity(valid) {
                this.adminChangePasswordComplete = valid
            },
            doChangePassword() {
                if (!this.adminChangePasswordComplete) return
                if (this.adminChangePassword.newPassword !== this.adminChangePassword.confirmNewPassword) {
                    this.message = "Passwords don't match"
                    return
                }
                this.changePassword({
                    'user_name': this.userName,
                    'old_password': this.adminChangePassword.currentPassword,
                    'new_password': this.adminChangePassword.newPassword
                }).then(() => {
                    this.message = "Password changed"
                    this.adminChangePassword.currentPassword = null
                    this.adminChangePassword.newPassword = null
                    this.adminChangePassword.confirmNewPassword = null
                    this.adminChangePassword = {...this.adminChangePassword}
                }).catch(error => {
                    this.message = JSON.parse(error.request.response).message
			    })
            },
            saveGuiSettings() {
            	if (!this.guiComplete) return
                this.updatePluginConfig({
                    pluginId: 'gui',
                    configName: 'GuiService',
                    config: this.configurable.gui.GuiService.config
                }).then(response => {
					this.createToast(response)
                })
            },
            removeToast() {
                this.message = ''
            },
            createToast(response) {
				if (response.status === 200) {
					this.message = 'Saved Successfully.'
				} else {
					this.message = response.data.message
				}
            },
            determineState(tabId) {
            	this.changeState({ name: tabId})
            }
        },
        created() {
            this.loadPluginConfig({
                pluginId: 'system_scheduler',
                configName: 'SystemSchedulerService'
            })
            this.fetchData({
                rule: `metadata`
            }).then((response) => {
                if (response.status === 200) {
                    this.system_info = response.data
                }
            })

            this.changeState({ name: 'research-settings-tab' })
        },
        mounted() {
            if (this.$route.hash) {
				this.$refs.tabs.selectTab(this.$route.hash.slice(1))
            }
        }
    }
</script>

<style lang="scss">
    .settings {
        .grid {
            display: grid;
            grid-row-gap: 12px;
            align-items: center;
            grid-auto-rows: auto;
            margin-bottom: 24px;
            margin-right: 15px;
            &.grid-col-2 {
                grid-template-columns: 2fr 3fr;
            }
            &.grid-col-4 {
                width: 300px;
                grid-template-columns: 2fr 3fr;
            }
            .grid-item {
                text-align: right;
            }
            .x-btn {
                justify-self: end;
            }
        }
        .tab-settings .schema-form {
            > .array {
                display: block;
            }
            .x-btn {
                justify-self: end;
            }
        }
        .research-settings-tab .tab-settings .schema-form > .array {
            display: grid;
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
    }
</style>
