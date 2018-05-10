<template>
    <x-page title="Reporting">
        <x-box class="x-report">
            <div class="x-report-download">
                <a class="x-btn great" @click="startDownload" tabindex="1" :class="{disabled: downloading}">
                    <template v-if="downloading">GENERATING...</template>
                    <template v-else>Download Now</template>
                </a>
            </div>
            <h3>Periodical Report Email</h3>
            <div class="x-content">
                <div>
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
                <div class="x-section">
                    <h4>Email List</h4>
                    <vm-select v-model="execReportSettings.recipients" multiple filterable allow-create placeholder=""
                               no-data-text="Type mail addresses..." :default-first-option="true"/>
                </div>
                <div class="x-section x-btn-container">
                    <a class="x-btn" :class="{disabled: !valid}" tabindex="6" @click="schedule_exec_report">Save</a>
                    <a class="x-btn inverse" :class="{disabled: !valid}" tabindex="7" @click="test_exec_report">Test Now</a>
                </div>
            </div>
        </x-box>
        <modal v-if="error">
            <div slot="body">
                <div class="show-space">{{error}}</div>
            </div>
            <button class="x-btn" slot="footer" @click="closeError">OK</button>
        </modal>
    </x-page>
</template>

<script>
    import xPage from '../../components/layout/Page.vue'
    import xBox from '../../components/layout/Box.vue'
    import Modal from '../../components/popover/Modal.vue'

    import {mapActions} from 'vuex'
    import {DOWNLOAD_REPORT} from '../../store/modules/report'
    import {REQUEST_API} from '../../store/actions'

    export default {
        name: 'report-container',
        components: {xPage, xBox, Modal},
        computed: {
        	valid() {
        		return this.execReportSettings.recipients.length > 0 && this.execReportSettings.period
            }
        },
        data() {
            return {
                execReportSettings: {
                    period: 'weekly',
                    recipients: []
                },
                downloading: false,
                error: ''
            }
        },
        methods: {
            ...mapActions({downloadReport: DOWNLOAD_REPORT, fetchData: REQUEST_API}),
            startDownload() {
                if (this.downloading) return
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
                }).catch((error) => {
                    this.downloading = false
                    this.error = error.response.data.message
                })
            },
            test_exec_report() {
            	if (!this.execReportSettings.recipients.length) {
            		return
                }
                this.fetchData({
                    rule: `test_exec_report`,
                    method: 'POST',
                    data: this.execReportSettings.recipients
                }).then(() => this.error = '').catch(error => this.error = error.response.data.message)
            },
            schedule_exec_report() {
				if (!this.valid) {
					return
				}
                this.fetchData({
                    rule: `exec_report`,
                    method: 'POST',
                    data: this.execReportSettings
                })
            },
            closeError() {
            	this.error = ''
            }
        },
        created() {
            this.fetchData({
                rule: `exec_report`,
            }).then((response) => {
                if (response.data && response.data.recipients) this.execReportSettings = response.data
            })
        }
    }
</script>

<style lang="scss">
    .x-report {
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
</style>