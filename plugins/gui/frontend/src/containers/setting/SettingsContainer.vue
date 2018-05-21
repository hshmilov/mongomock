<template>
    <x-page title="Settings" class="settings">
        <tabs>
            <tab title="Lifecycle Settings" id="research-settings-tab" selected="true">
                <h3>Discovery Phase</h3>
                <div class="grid grid-col-2">
                    <label for="schedule" class="label">Next Scheduled Time:</label>
                    <x-date-edit id="schedule" :value="nextResearchStart" @input="scheduleResearch" :limit="limit"/>
                    <template v-if="schedulerSettings && schedulerSettings.config">
                        <label for="research_rate" class="label">Schedule Rate (hours)</label>
                        <div class="grid-item">
                            <input id="research_rate" type="number" min="0"
                                   v-model="schedulerSettings.config.system_research_rate">
                            <a class="x-btn right" @click="setResearchRate">Set</a>
                        </div>
                    </template>
                    <template v-else>Loading</template>
                </div>
            </tab>
            <tab title="Global Settings" id="email-settings-tab" v-if="configurable.core">
                <div class="grid grid-col-2">
                    <x-schema-form :schema="configurable.core.CoreService.schema"
                                   v-model="configurable.core.CoreService.config" @validate="updateValidity"
                                   :api-upload="`adapters/core`"/>

                </div>
                <button class="x-btn" :class="{'disabled':!complete}" @click="setEmailServer">Save</button>
            </tab>
            <tab title="GUI Settings" id="system-settings-tab" v-if="configurable.gui">
                <div class="grid grid-col-2">
                    <x-schema-form :schema="configurable.gui.GuiService.schema" v-model="configurable.gui.GuiService.config"/>
                </div>
                <div class="row">
                </div>
                <a class="x-btn" @click="saveGuiSettings">Save</a>
            </tab>
        </tabs>
        <modal v-if="message">
            <div slot="body">
                <div class="show-space">{{message}}</div>
            </div>
            <div slot="footer">
                <button class="x-btn" @click="closeModal">OK</button>
            </div>
        </modal>
    </x-page>
</template>

<script>
    import xSchemaForm from '../../components/schema/SchemaForm.vue'
    import xPage from '../../components/layout/Page.vue'
    import Tabs from '../../components/tabs/Tabs.vue'
    import Tab from '../../components/tabs/Tab.vue'
    import xDateEdit from '../../components/controls/string/DateEdit.vue'
    import xCheckbox from '../../components/inputs/Checkbox.vue'
    import Modal from '../../components/popover/Modal.vue'

    import {FETCH_LIFECYCLE} from '../../store/modules/dashboard'
    import {REQUEST_API, START_RESEARCH_PHASE, STOP_RESEARCH_PHASE} from '../../store/actions'
    import {mapState, mapActions, mapMutations} from 'vuex'
    import {SAVE_PLUGIN_CONFIG, LOAD_PLUGIN_CONFIG, CHANGE_PLUGIN_CONFIG} from "../../store/modules/configurable";

    export default {
        name: 'settings-container',
        components: {xPage, Tabs, Tab, xDateEdit, xCheckbox, xSchemaForm, Modal},
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

        },
        data() {
            return {
                lifecycle: {
                    researchRate: 0
                },
                complete: true,
                message: '',
            }
        },
        methods: {
            ...mapMutations({
                changePluginConfig: CHANGE_PLUGIN_CONFIG
            }),
            ...mapActions({
                fetchLifecycle: FETCH_LIFECYCLE,
                fetchData: REQUEST_API,
                startResearch: START_RESEARCH_PHASE,
                stopResearch: STOP_RESEARCH_PHASE,
                updatePluginConfig: SAVE_PLUGIN_CONFIG,
                loadPluginConfig: LOAD_PLUGIN_CONFIG
            }),
            scheduleResearch(scheduleDate) {
                this.fetchData({
                    rule: `research_phase`,
                    method: 'POST',
                    data: {timestamp: scheduleDate}
                })
            },
            setEmailServer() {
                if (!this.complete) return
                this.updatePluginConfig({
                    pluginId: 'core',
                    configName: 'CoreService',
                    config: this.configurable.core.CoreService.config
                }).then(response => {
                    if (response.status === 200) {
                        this.message = 'Saved Successfully.'
                    }
                })
            },
            updateValidity(valid) {
                this.complete = valid
            },
            saveGuiSettings() {
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
            closeModal() {
                this.message = ''
            }
        },
        created() {
            this.fetchLifecycle()
            this.loadPluginConfig({
                pluginId: 'system_scheduler',
                configName: 'SystemSchedulerService'
            })
            this.loadPluginConfig({
                pluginId: 'core',
                configName: 'CoreService'
            })
        }
    }
</script>

<style lang="scss">
    .settings {
        .grid {
            grid-row-gap: 12px;
            width: 600px;
            align-items: center;
            grid-auto-rows: auto;
            margin-bottom: 24px;
            margin-right: 15px;
            &.grid-col-2 {
                grid-template-columns: 2fr 3fr;
            }
            .grid-item {
                text-align: right;
            }
            .x-btn {
                justify-self: end;
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
