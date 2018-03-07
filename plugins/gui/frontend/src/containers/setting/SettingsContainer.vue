<template>
    <scrollable-page title="Settings" class="settings">
        <tabs>
            <tab title="Lifecycle Settings" id="research-settings-tab" key="basic" selected="true">
                <h3>Research Phase</h3>
                <div class="grid-2-3">
                    <label for="start">Trigger Run</label>
                    <div class="grid-item">
                        <a id="start" class="btn" @click="startResearch">Start</a>
                    </div>
                    <label for="schedule" class="label">Next Scheduled Time:</label>
                    <x-date-edit id="schedule" v-model="nextResearchStart" @input="scheduleResearch" :limit="limit" />
                    <label for="research_rate" class="label">Schedule Rate (hours)</label>
                    <div class="grid-item">
                        <input id="research_rate" type="number" min="0" v-model="researchRate">
                        <a class="btn set" @click="setResearchRate">Set</a>
                    </div>
                </div>
                <div class="row">
                    <div class="col-4">
                        <h3>Execution</h3>
                        <toggle-button id="toggle" :value="executionEnabled" color="#FF7D46" :sync="true" :labels="true"
                                       @change="toggleExecution"/>
                        <div v-if=""></div>
                    </div>
                </div>
            </tab>
            <tab title="Email Settings" id="email-settings-tab" key="blah">
                <div class="item">
                    <label for="host" class="label">Host</label>
                    <input id="host" type="text">
                </div>
                <div class="item">
                    <label for="port" class="label">Port</label>
                    <input id="port" type="text">
                </div>
                <div class="item">
                    <a id="save" class="btn">Save</a>
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
    import {FETCH_LIFECYCLE} from '../../store/modules/dashboard'
    import {REQUEST_API} from '../../store/actions'
    import {mapActions} from 'vuex'
    // import TagsMixin from './tags'

    export default {
        name: 'settings-container',
        components: {ScrollablePage, NamedSection, Card, Tabs, Tab, xDateEdit},
        mixins: [],
        computed: {
            limit() {
                return [{
                    type: 'fromto',
                    from: `${new Date().toDateString()} ${new Date().toTimeString()}`
                }]
            }
        },
        data() {
            return {
                nextResearchStart: "",
                executionEnabled: true,
                researchRate: 0
            }
        },
        methods: {
            ...mapActions({fetchLifecycle: FETCH_LIFECYCLE}),
            ...mapActions({fetchData: REQUEST_API}),
            startResearch() {
                this.fetchData({
                    rule: `api/research_phase`,
                    method: 'POST'
                })
            },
            toggleExecution(executionEnabled) {
                let param = `enable`
                if (!executionEnabled.value) {
                    param = `disable`
                }
                this.fetchData({
                    rule: `api/execution/${param}`,
                    method: 'POST'
                })
                this.executionEnabled = executionEnabled.value
            },
            scheduleResearch(scheduleDate) {
                this.fetchData({
                    rule: `api/research_phase`,
                    method: 'POST',
                    data: {timestamp: scheduleDate}
                })
            },
            setResearchRate() {
                this.fetchData({
                    rule: `api/dashboard/lifecycle_rate`,
                    method: 'POST',
                    data: {system_research_rate: this.researchRate * 60 * 60}
                })
            }
        },
        created() {
            this.fetchLifecycle().then((response) => {
                let tempDate = new Date(parseInt(response.data.next_run_time) * 1000)
                this.nextResearchStart = `${tempDate.toLocaleDateString()} ${tempDate.toLocaleTimeString()}`
            })
            this.fetchData({
                rule: 'api/execution'
            }).then((response) => {
            	this.executionEnabled = (response.data === 'enabled')
            })
            this.fetchData({
                rule: 'api/dashboard/lifecycle_rate'
            }).then((response) => {
                this.researchRate = response.data / 60 / 60
            })
        }
    }
</script>

<style lang="scss">
    .settings {
        .grid-2-3 {
            display: grid;
            grid-template-columns: 1fr 2fr;
            grid-template-rows: 1fr 1fr 1fr;
            grid-row-gap: 12px;
            width: 500px;
            align-items: center;
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
        .row {
            margin-top: 24px;
        }
    }
</style>