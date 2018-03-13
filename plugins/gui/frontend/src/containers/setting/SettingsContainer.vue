<template>
    <scrollable-page title="Settings" class="settings">
        <tabs>
            <tab title="Lifecycle Settings" id="research-settings-tab" selected="true">
                <h3>Research Phase</h3>
                <div class="grid grid-col-2 grid-row-3">
                    <label for="start">Trigger Run</label>
                    <div class="grid-item">
                        <a id="start" class="btn" @click="startResearch">Start</a>
                    </div>
                    <label for="schedule" class="label">Next Scheduled Time:</label>
                    <x-date-edit id="schedule" :value="nextResearchStart" @input="scheduleResearch" :limit="limit" />
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
                <div class="item">
                    <label for="host" class="label" >Host</label>
                    <input id="host" type="text" v-model="emailHost">
                </div>
                <div class="item">
                    <label for="port" class="label">Port</label>
                    <input id="port" type="text" v-model="emailPort">
                </div>
                <div class="item">
                    <a id="save" class="btn" @click="setEmailServer">Save</a>
                </div>
            </tab>
            <tab title="System Settings" id="system-settings-tab">
                <h3>Data Tables</h3>
                <div class="grid grid-col-2 grid-row-3">
                    <label for="refresh-rate">Auto-Refresh Rate (seconds)</label>
                    <input id="refresh-rate" type="number" min="0" v-model="refreshRate">
                    <label for="single-adapter">Use Single Adapter View</label>
                    <checkbox id="single-adapter" v-model="singleAdapter" />
                    <div/>
                    <button class="btn" @click="saveSettings">save</button>
                </div>
                <div class="row">
                </div>
            </tab>
        </tabs>
    </scrollable-page>
</template>

<script>
    import ScrollablePage from '../../components/ScrollablePage.vue'
    import NamedSection from '../../components/NamedSection.vue'
    import Card from '../../components/Card.vue'
    import Tabs from '../../components/tabs/Tabs.vue'
    import Tab from '../../components/tabs/Tab.vue'
    import xDateEdit from '../../components/controls/string/DateEdit.vue'
    import Checkbox from '../../components/Checkbox.vue'

    import { FETCH_LIFECYCLE } from '../../store/modules/dashboard'
    import { FETCH_SETTINGS, UPDATE_REFRESH_RATE, UPDATE_SINGLE_ADAPTER, SAVE_SETTINGS } from '../../store/modules/settings'
    import { REQUEST_API } from '../../store/actions'
    import { mapState, mapMutations, mapActions } from 'vuex'

    export default {
        name: 'settings-container',
        components: {ScrollablePage, NamedSection, Card, Tabs, Tab, xDateEdit, Checkbox},
        computed: {
            ...mapState(['dashboard', 'settings']),
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
            refreshRate: {
            	get() {
            		return this.settings.data.refreshRate
                },
                set(refreshRate) {
            		this.updateRefreshRate(parseInt(refreshRate))
                }
            },
            singleAdapter: {
            	get(){
            		return this.settings.data.singleAdapter
                },
                set(singleAdapter) {
            		this.updateSingleAdapter(singleAdapter)
                }
            }
        },
        data() {
            return {
                emailHost: "",
                emailPort: "",
                lifecycle: {
                    executionEnabled: true,
                    researchRate: 0
                }
            }
        },
        methods: {
            ...mapMutations( {
                updateRefreshRate: UPDATE_REFRESH_RATE,
                updateSingleAdapter: UPDATE_SINGLE_ADAPTER
            }),
            ...mapActions({
                fetchLifecycle: FETCH_LIFECYCLE,
                fetchSettings: FETCH_SETTINGS,
				fetchData: REQUEST_API,
                saveSettings: SAVE_SETTINGS
            }),
            startResearch() {
                this.fetchData({
                    rule: `research_phase`,
                    method: 'POST'
                })
            },
            toggleExecution(executionEnabled) {
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
            scheduleResearch(scheduleDate) {
                this.fetchData({
                    rule: `research_phase`,
                    method: 'POST',
                    data: {timestamp: scheduleDate}
                })
            },
            setResearchRate() {
                this.fetchData({
                    rule: `dashboard/lifecycle_rate`,
                    method: 'POST',
                    data: {system_research_rate: this.lifecycle.researchRate * 60 * 60}
                })
            },
            setEmailServer() {
                this.fetchData({
                    rule: `email_server`,
                    method: 'POST',
                    data: {host: this.emailHost, port: this.emailPort}
                })
            }
        },
        created() {
            this.fetchLifecycle()
            this.fetchSettings()
            this.fetchData({
                rule: 'execution'
            }).then((response) => {
            	this.executionEnabled = (response.data === 'enabled')
            })
            this.fetchData({
                rule: 'dashboard/lifecycle_rate'
            }).then((response) => {
                this.lifecycle.researchRate = response.data / 60 / 60
            })
            this.fetchData({
                rule: 'email_server'
            }).then((response) => {
                this.emailHost = response.data.host
                this.emailPort = response.data.port
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
            &.grid-col-2 {
                grid-template-columns: 1fr 2fr;
            }
            &.grid-row-3 {
                grid-template-rows: 1fr 1fr 1fr;
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
        #system-settings-tab {
            .btn {
                justify-self: end;
            }
        }
    }
</style>