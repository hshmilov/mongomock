<template>
    <x-page title="Settings" class="x-settings">
        <x-tabs ref="tabs" @click="determineState">
            <x-tab title="Lifecycle Settings" id="research-settings-tab" :selected="true">
                <div class="tab-settings">
                    <template v-if="schedulerSettings">
                        <x-form :schema="schedulerSettings.schema" v-model="schedulerSettings.config"
                                @validate="updateSchedulerValidity" :read-only="isReadOnly"
                                api-upload="plugins/system_scheduler"/>
                        <div class="place-right">
                            <x-button :disabled="isResearchDisabled" id="research-settings-save" @click="saveSchedulerSettings">Save</x-button>
                        </div>
                    </template>
                </div>
            </x-tab>
            <x-tab title="Global Settings" id="global-settings-tab" ref="global">
                <div class="tab-settings">
                    <template v-if="coreSettings">
                        <x-form :schema="coreSettings.schema" @validate="updateCoreValidity"
                                :read-only="isReadOnly" v-model="coreSettings.config" api-upload="plugins/core"/>
                        <div class="footer">
                            <x-maintenance :read-only="isReadOnly" v-if="$refs.global && $refs.global.isActive"/>
                            <x-button :disabled="!coreComplete || isReadOnly" @click="saveGlobalSettings" id="global-settings-save">Save</x-button>
                        </div>
                    </template>
                </div>
            </x-tab>
            <x-tab title="GUI Settings" id="gui-settings-tab">
                <div class="tab-settings">
                    <template v-if="guiSettings">
                        <x-form :schema="guiSettings.schema" @validate="updateGuiValidity" :read-only="isReadOnly"
                                v-model="guiSettings.config" api-upload="plugins/gui"/>
                        <div class="place-right">
                            <x-button :disabled="!guiComplete || isReadOnly" id="gui-settings-save" @click="saveGuiSettings">Save</x-button>
                        </div>
                    </template>
                </div>
            </x-tab>
            <x-tab title="Feature flags" id="feature-flags-tab" v-if="isAxonius">
                <div class="tab-settings">
                    <template v-if="featureFlags">
                        <x-form :schema="featureFlags.schema" :read-only="isReadOnly"
                                v-model="featureFlags.config" api-upload="plugins/gui"/>
                        <div class="place-right">
                            <x-button :disabled="isReadOnly" id="feature-flags-save" @click="saveFeatureFlags">Save</x-button>
                        </div>
                    </template>
                </div>
            </x-tab>
            <x-tab title="Manage Users" id="user-settings-tab" v-if="isAdmin">
                <x-users-roles :read-only="isReadOnly" @toast="message = $event"/>
            </x-tab>
            <x-tab title="About" id="about-settings-tab">
                <div class="tab-settings">
                    <x-custom :data="systemInfo" :vertical="true"/>
                </div>
            </x-tab>
        </x-tabs>
        <x-toast v-if="message" :message="message" @done="removeToast"/>
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xTabs from '../axons/tabs/Tabs.vue'
    import xTab from '../axons/tabs/Tab.vue'
    import xButton from '../axons/inputs/Button.vue'
    import xToast from '../axons/popover/Toast.vue'
    import xForm from '../neurons/schema/Form.vue'
    import xCustom from '../neurons/schema/Custom.vue'
    import xUsersRoles from '../networks/config/UsersRoles.vue'
    import xMaintenance from '../networks/config/Maintenance.vue'

    import {mapState, mapActions, mapMutations} from 'vuex'
    import {SAVE_PLUGIN_CONFIG, LOAD_PLUGIN_CONFIG, CHANGE_PLUGIN_CONFIG} from '../../store/modules/settings'
    import {UPDATE_SYSTEM_CONFIG} from '../../store/mutations'
    import {REQUEST_API, START_RESEARCH_PHASE, STOP_RESEARCH_PHASE} from '../../store/actions'
    import {CHANGE_TOUR_STATE} from '../../store/modules/onboarding'

    export default {
        name: 'x-settings',
        components: {
            xPage, xTabs, xTab, xButton, xToast, xForm, xCustom, xUsersRoles, xMaintenance
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
                featureFlags(state) {
                    if (!state.settings.configurable.gui) return null
                    return state.settings.configurable.gui.FeatureFlags
                },
                users(state) {
                    return state.auth.allUsers.data
                },
                isAdmin(state) {
                    return state.auth.currentUser.data &&
                        (state.auth.currentUser.data.admin || state.auth.currentUser.data.role_name === 'Admin')
                },
                isAxonius(state) {
                    return state.auth.currentUser.data.user_name === '_axonius'
                }
            }),
            validResearchRate() {
                if (!this.schedulerSettings.config) return 12
                return this.validNumber(this.schedulerSettings.config.discovery_settings.system_research_rate)
            },
            isResearchDisabled() {
                return !this.schedulerComplete || !this.validResearchRate || this.isReadOnly
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
            saveFeatureFlags() {
                this.updatePluginConfig({
                    pluginId: 'gui',
                    configName: 'FeatureFlags',
                    config: this.featureFlags.config
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
            }
        },
        created() {
            this.loadPluginConfig({
                pluginId: 'gui',
                configName: 'GuiService'
            })
            this.loadPluginConfig({
                pluginId: 'gui',
                configName: 'FeatureFlags'
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
    .x-settings {
        .x-tabs {
            max-width: 840px;
        }

        .tab-settings .x-form .x-array-edit {
            grid-template-columns: 1fr;
        }

        .global-settings-tab {
            .footer {
                display: flex;
                align-items: flex-start;

                .md-card {
                    width: 80%;
                    flex: 1 0 auto;
                }

                > .x-button {
                    margin-top: 4px;
                }
            }
        }

        .research-settings-tab .tab-settings .x-form > .x-array-edit {
            display: grid;
        }

        label {
            margin-bottom: 0;
        }
    }
</style>
