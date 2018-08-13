<template>
    <x-page title="Reporting">
        <x-box class="x-report">
            <div class="v-spinner-bg" v-if="loading"></div>
            <pulse-loader :loading="loading" color="#FF7D46" />
            <div class="x-report-download">
                <a class="x-btn great" @click="startDownload" :class="{disabled: disableDownloadReport}" id="reports_download">
                    <template v-if="downloading">DOWNLOADING...</template>
                    <template v-else>Download Now</template>
                </a>
            </div>
            <div class="x-report-latest">
                {{latestReportDate}}.
                <template v-if="!isLatestReport"></template>
            </div>
            <h3 id="reports_schedule">Periodical Report Email</h3>
            <div class="x-content">
                <div id="reports_frequency">
                    <h4>Email Frequency</h4>
                    <div class="x-grid">
                        <input id="period-daily" type="radio" value="daily" v-model="execReportSettings.period">
                        <label for="period-daily">Daily</label>
                        <input id="period-weekly" type="radio" value="weekly" v-model="execReportSettings.period">
                        <label for="period-weekly">Weekly</label>
                        <input id="period-monthly" type="radio" value="monthly" v-model="execReportSettings.period">
                        <label for="period-monthly">Monthly</label>
                    </div>
                </div>
                <div class="x-section" id="reports_mails">
                    <h4>Email List</h4>
                    <vm-select v-model="execReportSettings.recipients" multiple filterable allow-create
                               placeholder="" no-data-text="Type mail addresses..." :default-first-option="true"/>
                </div>
                <div class="x-section x-btn-container">
                    <a class="x-btn" :class="{disabled: !valid}" @click="scheduleExecReport">Save</a>
                    <a class="x-btn inverse" :class="{ disabled: !hasRecipients || disableDownloadReport }"
                       @click="testExecReport">Test Now</a>
                </div>
            </div>
        </x-box>
        <x-toast v-if="message" :message="message" @done="removeToast" />
    </x-page>
</template>

<script>
    import xPage from '../../components/layout/Page.vue'
    import xBox from '../../components/layout/Box.vue'
    import xToast from '../../components/popover/Toast.vue'
	import PulseLoader from 'vue-spinner/src/PulseLoader.vue'

    import { mapMutations, mapActions } from 'vuex'
    import { DOWNLOAD_REPORT } from '../../store/modules/report'
    import { CHANGE_TOUR_STATE } from '../../store/modules/onboarding'
	import { REQUEST_API } from '../../store/actions'

    export default {
        name: 'report-container',
        components: { xPage, xBox, xToast, PulseLoader },
        computed: {
        	valid() {
        		return this.execReportSettings.period
            },
            hasRecipients() {
        		return this.execReportSettings.recipients && this.execReportSettings.recipients.length
            },
            disableDownloadReport() {
        	    return this.downloading || !this.isLatestReport
            },
            loading() {
        		return this.fetching.lastGenerated || this.fetching.schedule
            }
        },
        data() {
            return {
                execReportSettings: {
                    period: 'weekly',
                    recipients: []
                },
                downloading: false,
                latestReportDate: 'No report generated. Press \"Discover Now\" to generate',
                isLatestReport: false,
                message: '',
                fetching: {
                	lastGenerated: false, schedule: false
                }
            }
        },
        methods: {
            ...mapMutations({ changeState: CHANGE_TOUR_STATE }),
            ...mapActions({ downloadReport: DOWNLOAD_REPORT, fetchData: REQUEST_API }),
            startDownload() {
                if (this.disableDownloadReport) return
                this.downloading = true
                this.downloadReport().then((response) => {
                    this.downloading = false
                    let blob = new Blob([response.data], {type: response.headers["content-type"]})
                    let link = document.createElement('a')
                    link.href = window.URL.createObjectURL(blob)
                    let now = new Date()
                    let formattedDate = now.toLocaleDateString().replace(/\//g, '')
                    let formattedTime = now.toLocaleTimeString().replace(/:/g, '')
                    link.download = `axonius-report_${formattedDate}-${formattedTime}.pdf`
                    link.click()
                    this.changeState({ name: 'tourFinale' })
                }).catch((error) => {
                    this.downloading = false
                    this.message = error.response.data.message
                })
            },
            testExecReport() {
            	if (!this.hasRecipients) return

                this.fetchData({
                    rule: `test_exec_report`,
                    method: 'POST',
                    data: this.execReportSettings.recipients
                }).then(() => this.message = 'Email with executive report was sent.')
                    .catch(error => this.message = error.response.data.message)
            },
            scheduleExecReport() {
				if (!this.valid) return

                this.fetchData({
                    rule: `exec_report`,
                    method: 'POST',
                    data: this.execReportSettings
                }).then((response) => {
                    if (response.status === 200) {
                        this.message = 'Executive report periodic email setting saved.'
                    }
                })
            },
            removeToast() {
            	this.message = ''
            }
        },
        created() {
        	this.fetching.schedule = true
            this.fetchData({
                rule: `exec_report`,
            }).then((response) => {
				this.fetching.schedule = false
                if (response.data) this.execReportSettings = { recipients: [], ...response.data }
            })
            this.changeState({ name: 'reportsSchedule' })
            this.fetching.lastGenerated = true
            this.fetchData({
                rule: `get_latest_report_date`,
                method: 'GET',
            }).then((response) => {
				this.fetching.lastGenerated = false
                if (response.data) {
                    this.latestReportDate = "Last generated: " + response.data
                    this.isLatestReport = true
                }
            })
        }
    }
</script>

<style lang="scss">
    .x-report {
        position: relative;
        width: 60vw;
        .x-report-download {
            margin-bottom: 24px;
            .x-btn {
                background-color: $theme-orange;
            }
            .error-text {
                display: inline-block;
                margin-left: 8px;
            }
        }
        .x-grid {
            grid-template-columns: 20px auto;
            grid-row-gap: 8px;
            align-items: center;
            label {
                margin: 0;
            }
        }
        .vm-select {
            width: 480px;
            .vm-select-input__inner {
                width: 100%;
            }
        }
        .x-btn-container {
            text-align: right;
            .x-btn {
                margin-left: 12px;
            }
        }
    }
    #reports_schedule {
        margin-bottom: 0;
    }
</style>