<template>
    <x-page title="Settings" class="settings">
        <tabs ref="tabs" @click="determineState">
            <tab title="Lifecycle Settings" id="research-settings-tab" :selected="true">
                <div class="tab-settings">
                    <template v-if="schedulerSettings">
                        <x-schema-form :schema="schedulerSettings.schema" v-model="schedulerSettings.config"
                                       @validate="updateSchedulerValidity" :read-only="isReadOnly"
                                       api-upload="adapters/system_scheduler"/>
                        <div class="place-right">
                            <button class="x-btn" id="research-settings-save"
                                    :class="{ disabled: !schedulerComplete || !validResearchRate || isReadOnly }"
                                    @click="saveSchedulerSettings">Save</button>
                        </div>
                    </template>
                </div>
            </tab>
            <tab title="Global Settings" id="global-settings-tab">
                <div class="tab-settings">
                    <template v-if="coreSettings">
                        <x-schema-form :schema="coreSettings.schema" @validate="updateCoreValidity"
                                       :read-only="isReadOnly" v-model="coreSettings.config" api-upload="adapters/core"/>
                        <div class="place-right">
                            <button class="x-btn" id="global-settings-save" :class="{ disabled: !coreComplete || isReadOnly }"
                                    @click="saveGlobalSettings">Save</button>
                        </div>
                        <h4>Remote Support Control</h4>
                        <div class="global-settings-access">
                            <label for="support_access">Temporary Remote Support (hours):</label>
                            <input type="number" v-model="supportAccess.duration" id="support_access"
                                   :disabled="isReadOnly"/>
                            <button @click="startSupportAccess" class="x-btn right" :class="{ disabled: isReadOnly }">Start</button>
                            <template v-if="supportAccessEndTime">
                                <div>Will stop at:</div>
                                <div>{{ supportAccessEndTime.toISOString().replace(/(T|Z)/g, ' ') }}
                                </div>
                                <!--button @click="stopSupportAccess" class="x-btn link">Stop Now</button-->
                            </template>
                            <div v-else class="grid-span3"/>
                        </div>
                    </template>
                </div>
            </tab>
            <tab title="GUI Settings" id="gui-settings-tab">
                <div class="tab-settings">
                    <template v-if="guiSettings">
                        <x-schema-form :schema="guiSettings.schema" @validate="updateGuiValidity"
                                       :read-only="isReadOnly"
                                       v-model="guiSettings.config" api-upload="adapters/gui"/>
                        <div class="place-right">
                            <button class="x-btn" id="gui-settings-save" :class="{ disabled: !guiComplete || isReadOnly }"
                                    @click="saveGuiSettings">Save</button>
                        </div>
                    </template>
                </div>
            </tab>
            <tab title="Manage Users" id="user-settings-tab" v-if="isAdmin">
                <x-user-role-container :read-only="isReadOnly" @toast="message = $event" />
            </tab>
            <tab title="About" id="about-settings-tab">
                <div class="tab-settings">
                    <x-custom-data :data="systemInfo" :vertical="true"/>
                </div>
            </tab>
        </tabs>
        <x-toast v-if="message" :message="message" @done="removeToast"/>
    </x-page>
</template>

<script>
    import xPage from '../../components/layout/Page.vue'
    import xSchemaForm from '../../components/schema/SchemaForm.vue'
    import xCustomData from '../../components/schema/CustomData.vue'
    import Tabs from '../../components/tabs/Tabs.vue'
    import Tab from '../../components/tabs/Tab.vue'
    import xDateEdit from '../../components/controls/string/DateEdit.vue'
    import xToast from '../../components/popover/Toast.vue'
    import xUserRoleContainer from './UserRoleContainer.vue'

    import { mapState, mapActions, mapMutations } from 'vuex'
    import {SAVE_PLUGIN_CONFIG, LOAD_PLUGIN_CONFIG, CHANGE_PLUGIN_CONFIG} from "../../store/modules/configurable";
    import {REQUEST_API, START_RESEARCH_PHASE, STOP_RESEARCH_PHASE} from '../../store/actions'
    import {CHANGE_TOUR_STATE} from '../../store/modules/onboarding'

    export default {
        name: 'settings-container',
        components: {
            xPage, Tabs, Tab, xUserRoleContainer,
            xDateEdit, xSchemaForm, xCustomData, xToast
        },
        computed: {
            ...mapState({
                isReadOnly(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Settings === 'ReadOnly'
                },
                schedulerSettings(state) {
                    if (!state.configurable.system_scheduler) return null
                    return state.configurable.system_scheduler.SystemSchedulerService
                },
                coreSettings(state) {
                    if (!state.configurable.core) return null
                    return state.configurable.core.CoreService
                },
                guiSettings(state) {
                    if (!state.configurable.gui) return null
                    return state.configurable.gui.GuiService
                },
                users(state) {
                    return state.auth.allUsers.data
                },
                isAdmin(state) {
                    return state.auth.currentUser.data &&
                        (state.auth.currentUser.data.admin || state.auth.currentUser.data.role_name === 'Admin')
                }
            }),
            validResearchRate() {
                if (!this.schedulerSettings.config) return 12
                return this.validNumber(this.schedulerSettings.config.discovery_settings.system_research_rate)
            },
            supportAccessEndTime() {
                if (!this.coreSettings.config || !this.coreSettings.config.maintenance_settings.analytics) {
                    return null
                }
                return this.supportAccess.endTime
            }
        },
        data() {
            return {
                coreComplete: true,
                guiComplete: true,
                schedulerComplete: true,
                message: '',
                systemInfo: {},
                supportAccess: {
                    duration: 24,
                    endTime: null
                },
                createUserActive: false,
                userForm: {
                    user_name: '',
                    password: '',
                    first_name: '',
                    last_name: ''
                },
                userToRemove: null
            }
        },
        methods: {
            ...mapMutations({
                changePluginConfig: CHANGE_PLUGIN_CONFIG, changeState: CHANGE_TOUR_STATE
            }),
            ...mapActions({
                fetchData: REQUEST_API,
                startResearch: START_RESEARCH_PHASE, stopResearch: STOP_RESEARCH_PHASE,
                updatePluginConfig: SAVE_PLUGIN_CONFIG, loadPluginConfig: LOAD_PLUGIN_CONFIG
            }),
            validNumber(value) {
                if (value === undefined || isNaN(value) || value <= 0) {
                    return false
                }
                return true
            },
            saveGlobalSettings() {
                if (!this.coreComplete || this.isReadOnly) return
                this.updatePluginConfig({
                    pluginId: 'core',
                    configName: 'CoreService',
                    config: this.coreSettings.config
                }).then(response => {
                    this.createToast(response)
                    this.getSupportAccess()
                }).catch(error => {
                    if (error.response.status === 400) {
                        this.message = error.response.data.message
                    }
                })
            },
            saveSchedulerSettings() {
                if (!this.schedulerComplete || !this.validResearchRate || this.isReadOnly) return
                this.updatePluginConfig({
                    pluginId: 'system_scheduler',
                    configName: 'SystemSchedulerService',
                    config: this.schedulerSettings.config
                }).then(response => {
                    this.createToast(response)
                }).catch(error => {
                    if (error.response.status === 400) {
                        this.message = error.response.data.message
                    }
                })
            },
            updateSchedulerValidity(valid) {
                this.schedulerComplete = valid
            },
            updateCoreValidity(valid) {
                this.coreComplete = valid
            },
            updateGuiValidity(valid) {
                this.guiComplete = valid
            },
            saveGuiSettings() {
                if (!this.guiComplete || this.isReadOnly) return
                this.updatePluginConfig({
                    pluginId: 'gui',
                    configName: 'GuiService',
                    config: this.guiSettings.config
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
                    this.message = 'Error: ' + response.data.message
                }
            },
            determineState(tabId) {
                this.changeState({name: tabId})
            },
            startSupportAccess() {
                if (this.isReadOnly) return
                this.fetchData({
                    rule: 'support_access',
                    method: 'POST',
                    data: {duration: this.supportAccess.duration}
                }).then(() => {
                    this.message = `Support Access Started for ${this.supportAccess.duration} hours`
                    this.getSupportAccess()
                    this.loadPluginConfig({
                        pluginId: 'core',
                        configName: 'CoreService'
                    })
                }).catch(error => {
                    if (error.response.status === 400) {
                        this.message = error.response.data.message
                    }
                })
            },
            stopSupportAccess() {
                this.fetchData({
                    rule: 'support_access',
                    method: 'DELETE'
                }).then(() => {
                    this.message = `Support Access Ended`
                    this.getSupportAccess()
                    this.loadPluginConfig({
                        pluginId: 'core',
                        configName: 'CoreService'
                    })
                }).catch(error => {
                    if (error.response.status === 400) {
                        this.message = error.response.data.message
                    }
                })
            },
            getSupportAccess() {
                this.fetchData({
                    rule: `support_access`
                }).then((response) => {
                    if (response.status === 200 && response.data) {
                        // Date timestamp received in seconds and JS Date expects milliseconds
                        this.supportAccess.endTime = new Date(parseInt(response.data) * 1000)
                    } else {
                        this.supportAccess.endTime = null
                    }
                })
            }
        },
        created() {
            this.loadPluginConfig({
                pluginId: 'gui',
                configName: 'GuiService'
            })
            this.loadPluginConfig({
                pluginId: 'core',
                configName: 'CoreService'
            })
            this.loadPluginConfig({
                pluginId: 'system_scheduler',
                configName: 'SystemSchedulerService'
            })
            this.fetchData({
                rule: 'metadata'
            }).then((response) => {
                if (response.status === 200) {
                    this.systemInfo = response.data
                }
            })
            this.getSupportAccess()
            this.changeState({name: 'research-settings-tab'})
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
        .x-tabs {
            max-width: 840px;
        }
        .tab-settings .schema-form .array {
            grid-template-columns: 1fr;
        }
        .global-settings-access {
            display: grid;
            grid-template-columns: 1fr 1fr 120px;
            grid-gap: 8px 0;
            margin-bottom: 24px;
            align-items: center;
        }
        .research-settings-tab .tab-settings .schema-form > .array {
            display: grid;
        }
        input.cov-datepicker {
            width: 100%;
        }
        label {
            margin-bottom: 0;
        }
    }
</style>
