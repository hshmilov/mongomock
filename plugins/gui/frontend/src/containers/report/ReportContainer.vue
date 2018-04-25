<template>
    <x-page title="Reporting">
        <div slot="action">
            <a class="x-btn great" @click="downloadReport" tabindex="1">Download Now</a>
        </div>
        <x-box class="x-report-email">
            <h3>Periodical Report Email</h3>
            <div class="x-content">
                <div>
                    <h4>Email Frequency</h4>
                    <div class="x-grid">
                        <input id="period-daily" type="radio" value="daily" v-model="emailReport.period">
                        <label for="period-daily">Daily</label>
                        <input id="period-weekly" type="radio" value="weekly" v-model="emailReport.period">
                        <label for="period-weekly">Weekly</label>
                        <input id="period-monthly" type="radio" value="monthly" v-model="emailReport.period">
                        <label for="period-monthly">Monthly</label>
                    </div>
                </div>
                <div class="x-section">
                    <h4>Email List</h4>
                    <vm-select v-model="emailReport.emails" multiple filterable allow-create placeholder=""
                               no-data-text="Type mail addresses..." :default-first-option="true"/>
                </div>
                <div class="x-section x-btn-container">
                    <a class="x-btn" tabindex="6" @click="saveReporting">Save</a>
                    <a class="x-btn inverse" tabindex="7" @click="testReporting">Test Now</a>
                </div>
            </div>
        </x-box>
    </x-page>
</template>

<script>
    import xPage from '../../components/layout/Page.vue'
    import xBox from '../../components/layout/Box.vue'

    import { mapActions } from 'vuex'
    import { DOWNLOAD_REPORT } from '../../store/modules/report'

	export default {
		name: 'report-container',
        components: { xPage, xBox },
        data() {
			return {
				emailReport: {
					period: 'weekly',
                    emails: []
				}
            }
        },
        methods: {
            ...mapActions({downloadReport: DOWNLOAD_REPORT}),
            saveReporting() {

            },
            testReporting() {

            }
        }
	}
</script>

<style lang="scss">
    .x-report-email {
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