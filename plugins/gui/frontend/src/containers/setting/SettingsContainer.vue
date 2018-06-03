<template>
    <x-page title="Settings" class="settings">
        <tabs ref="tabs">
            <tab title="Lifecycle Settings" id="research-settings-tab" selected="true">
                <h3>Discovery Phase</h3>
                <div class="grid grid-col-2">
                    <label for="schedule" class="label">Next Scheduled Time:</label>
                    <x-date-edit id="schedule" :value="nextResearchStart" @input="scheduleResearch" :limit="limit"/>
                    <template v-if="schedulerSettings && schedulerSettings.config">
                        <label for="research_rate" class="label">Schedule Rate (hours)</label>
                        <div class="grid-item">
                            <input id="research_rate" type="number" min="0" v-model="schedulerSettings.config.system_research_rate">
                            <a class="x-btn right" :class="{disabled: !validResearchRate}" @click="setResearchRate">Set</a>
                        </div>
                    </template>
                    <template v-else>Loading</template>
                </div>
            </tab>
            <tab title="Global Settings" id="global-settings-tab" v-if="configurable.core">
                <div class="tab-settings">
                    <x-schema-form :schema="configurable.core.CoreService.schema" @validate="updateCoreValidity"
                                   v-model="configurable.core.CoreService.config" api-upload="adapters/core"/>
                    <div class="place-right">
                        <button class="x-btn" :class="{disabled: !coreComplete}" @click="saveGlobalSettings">Save</button>
                    </div>
                </div>
            </tab>
            <tab title="GUI Settings" id="system-settings-tab" v-if="configurable.gui">
                <div class="tab-settings">
                    <x-schema-form :schema="configurable.gui.GuiService.schema" @validate="updateGuiValidity"
                                   v-model="configurable.gui.GuiService.config"/>
                    <div class="place-right">
                        <button class="x-btn" :class="{disabled: !guiComplete}" @click="saveGuiSettings">Save</button>
                    </div>
                </div>
            </tab>
        </tabs>
        <x-toast v-if="message" :message="message" @done="removeToast" />
    </x-page>
</template>

<script>
    import xSchemaForm from '../../components/schema/SchemaForm.vue'
    import xPage from '../../components/layout/Page.vue'
    import Tabs from '../../components/tabs/Tabs.vue'
    import Tab from '../../components/tabs/Tab.vue'
    import xDateEdit from '../../components/controls/string/DateEdit.vue'
    import xCheckbox from '../../components/inputs/Checkbox.vue'
    import xToast from '../../components/popover/Toast.vue'

    import { REQUEST_API, START_RESEARCH_PHASE, STOP_RESEARCH_PHASE } from '../../store/actions'
    import { mapState, mapActions, mapMutations } from 'vuex'
    import { SAVE_PLUGIN_CONFIG, LOAD_PLUGIN_CONFIG, CHANGE_PLUGIN_CONFIG } from "../../store/modules/configurable";

    export default {
        name: 'settings-container',
        components: { xPage, Tabs, Tab, xDateEdit, xCheckbox, xSchemaForm, xToast },
        computed: {
            ...mapState({
                dashboard(state) {
                    return state.dashboard
                },
                configurable(state) {
                    return state.configurable
                }
            }),
            limit() {
                return [{
                    type: 'fromto',
                    from: `${new Date().toDateString()} ${new Date().toTimeString()}`
                }]
            },
            nextResearchStart() {
                let tempDate = new Date(parseInt(this.dashboard.lifecycle.data.nextRunTime) * 1000)
                return `${tempDate.toLocaleDateString()} ${tempDate.toLocaleTimeString()}`
            },
            schedulerSettings: {
                get() {
                    if (!this.configurable.system_scheduler) return null
                    return this.configurable.system_scheduler.SystemSchedulerService
                },
                set(value) {
                    this.changePluginConfig({
                        pluginId: 'system_scheduler',
                        configName: 'SystemSchedulerService',
                        config: value.config
                    })
                }
            },
			validResearchRate() {
				return this.validNumber(this.schedulerSettings.config.system_research_rate)
            }
        },
        data() {
            return {
                coreComplete: true,
				guiComplete: true,
                message: '',
            }
        },
        methods: {
            ...mapMutations({
                changePluginConfig: CHANGE_PLUGIN_CONFIG
            }),
            ...mapActions({
                fetchData: REQUEST_API,
                startResearch: START_RESEARCH_PHASE,
                stopResearch: STOP_RESEARCH_PHASE,
                updatePluginConfig: SAVE_PLUGIN_CONFIG,
                loadPluginConfig: LOAD_PLUGIN_CONFIG
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
                })
            },
            saveGlobalSettings() {
                if (!this.coreComplete) return
                this.updatePluginConfig({
                    pluginId: 'core',
                    configName: 'CoreService',
                    config: this.configurable.core.CoreService.config
                }).then(response => {
                    if (response.status === 200) {
                        this.message = 'Saved Successfully.'
                    }
                }).catch(error => {
                	if (error.response.status === 400) {
                		this.message = error.response.data.message
                    }
                })
            },
            updateCoreValidity(valid) {
                this.coreComplete = valid
            },
			updateGuiValidity(valid) {
				this.guiComplete = valid
			},
            saveGuiSettings() {
            	if (!this.guiComplete) return
                this.updatePluginConfig({
                    pluginId: 'gui',
                    configName: 'GuiService',
                    config: this.configurable.gui.GuiService.config
                }).then(response => {
                    if (response.status === 200) {
                        this.message = 'Saved Successfully.'
                    }
                })
            },
            setResearchRate() {
            	if (!this.validResearchRate) return

                this.updatePluginConfig({
                    pluginId: 'system_scheduler',
                    configName: 'SystemSchedulerService',
                    config: this.schedulerSettings.config
                }).then(response => {
                    if (response.status === 200) {
                        this.message = 'Saved Successfully.'
                    }
                })
            },
            removeToast() {
                this.message = ''
            }
        },
        created() {
            this.loadPluginConfig({
                pluginId: 'system_scheduler',
                configName: 'SystemSchedulerService'
            })
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
            width: 800px;
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
        .tab-settings {
            width: 800px;
            .schema-form {
                > .array {
                    display: block;
                }
                .x-btn {
                    justify-self: end;
                }
            }
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
