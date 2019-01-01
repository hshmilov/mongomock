<template>
    <x-page title="Settings" class="settings">
        <tabs ref="tabs" @click="determineState">
            <tab title="Lifecycle Settings" id="research-settings-tab" :selected="true">
                <div class="tab-settings">
                    <template v-if="schedulerSettings">
                        <x-schema-form :schema="schedulerSettings.schema" v-model="schedulerSettings.config"
                                       @validate="updateSchedulerValidity" :read-only="isReadOnly"
                                       api-upload="plugins/system_scheduler"/>
                        <div class="place-right">
                            <button class="x-btn" id="research-settings-save"
                                    :class="{ disabled: !schedulerComplete || !validResearchRate || isReadOnly }"
                                    @click="saveSchedulerSettings">Save</button>
                        </div>
                    </template>
                </div>
            </tab>
            <tab title="Global Settings" id="global-settings-tab" ref="global">
                <div class="tab-settings">
                    <template v-if="coreSettings">
                        <x-schema-form :schema="coreSettings.schema" @validate="updateCoreValidity"
                                       :read-only="isReadOnly" v-model="coreSettings.config" api-upload="plugins/core"/>
                        <div class="footer">
                            <x-maintenance-container :read-only="isReadOnly" v-if="$refs.global && $refs.global.isActive" />
                            <button class="x-btn" :class="{ disabled: !coreComplete || isReadOnly }"
                                    @click="saveGlobalSettings" id="global-settings-save">Save</button>
                        </div>
                    </template>
                </div>
            </tab>
            <tab title="GUI Settings" id="gui-settings-tab">
                <div class="tab-settings">
                    <template v-if="guiSettings">
                        <x-schema-form :schema="guiSettings.schema" @validate="updateGuiValidity"
                                       :read-only="isReadOnly"
                                       v-model="guiSettings.config" api-upload="plugins/gui"/>
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
    import xToast from '../../components/popover/Toast.vue'
    import xUserRoleContainer from './UserRoleContainer.vue'
    import xMaintenanceContainer from './MaintenanceContainer.vue'

    import { mapState, mapActions, mapMutations } from 'vuex'
    import {SAVE_PLUGIN_CONFIG, LOAD_PLUGIN_CONFIG, CHANGE_PLUGIN_CONFIG} from '../../store/modules/settings'
    import {UPDATE_SYSTEM_CONFIG} from '../../store/mutations'
    import {REQUEST_API, START_RESEARCH_PHASE, STOP_RESEARCH_PHASE} from '../../store/actions'
    import {CHANGE_TOUR_STATE} from '../../store/modules/onboarding'

    export default {
        name: 'settings-container',
        components: {
            xPage, Tabs, Tab, xUserRoleContainer, xSchemaForm, xCustomData, xToast, xMaintenanceContainer
        },
        computed: {
            ...mapState({
                isReadOnly(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Settings === 'ReadOnly'
                },
                schedulerSettings(state) {
                    if (!state.settings.configurable.system_scheduler) return null
                    return state.settings.configurable.system_scheduler.SystemSchedulerService
                },
                coreSettings(state) {
                    if (!state.settings.configurable.core) return null
                    return state.settings.configurable.core.CoreService
                },
                guiSettings(state) {
                    if (!state.settings.configurable.gui) return null
                    return state.settings.configurable.gui.GuiService
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
            }
        },
        data() {
            return {
                coreComplete: true,
                guiComplete: true,
                schedulerComplete: true,
                message: '',
                systemInfo: {},
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
                changePluginConfig: CHANGE_PLUGIN_CONFIG,
                updateSystemConfig: UPDATE_SYSTEM_CONFIG,
                changeState: CHANGE_TOUR_STATE
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
                    this.updateSystemConfig({
                        data: {
                            global: {
                                mail: this.coreSettings.config.email_settings.enabled,
                                syslog: this.coreSettings.config.syslog_settings.enabled
                            }
                        }
                    })
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
                    this.updateSystemConfig({
                        data: {
                            system: this.guiSettings.config.system_settings
                        }
                    })
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
            this.changeState({name: 'lifecycleRate'})
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
        .global-settings-tab {
            .footer {
                display: flex;
                align-items: start;
                .md-card {
                    width: 80%;
                    flex: 1 0 auto;
                }
                >.x-btn {
                    margin-top: 4px;
                }
            }
        }
        .research-settings-tab .tab-settings .schema-form > .array {
            display: grid;
        }
        label {
            margin-bottom: 0;
        }
    }
</style>
