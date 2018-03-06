<template>
    <scrollable-page title="Settings" class="settings">
        <tabs>
            <tab title="Lifecycle Settings" id="research-settings-tab" key="basic" selected="true">
                <div class="row">
                    <div class="col-4">
                        <h3>Research</h3>
                        <a class="btn start" @click="startResearch">Start Research Phase</a>
                        <label for="schedule" class="label">Next Scheduled Research:</label>
                        <x-date-edit id="schedule" v-model="nextResearchStart" @input="scheduleResearch" :limit="limit" />
                        <label for="research_rate" class="label">Research Phases Rate</label>
                        <input id="research_rate" type="number" class="ml-4" :onchange="setResearchRate">
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
                executionEnabled: true
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
            setResearchRate(researchRate) {
                this.fetchData({
                    rule: `api/research_phase`,
                    method: 'POST',
                    data: {timestamp: researchRate}
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
            	this.executionEnabled = (response === 'enable')
            })
        }
    }
</script>

<style lang="scss">
    .settings {
        .btn.start {
            width: 100%;
        }
        input.cov-datepicker {
            width: 100%;
        }
        .row {
            margin-top: 24px;
        }
    }
</style>