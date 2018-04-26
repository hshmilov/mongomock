<template>
    <x-page title="Reporting">
        <x-box class="x-report">
            <div class="x-report-download">
                <a class="x-btn great" @click="downloadReport" tabindex="1">Download Now</a>
            </div>
            <h3>Periodical Report Email</h3>
            <div class="x-content">
                <div>
                    <h4>Email Frequency</h4>
                    <div class="x-grid">
                        <input disabled id="period-daily" type="radio" value="daily" v-model="emailReport.period">
                        <label for="period-daily">Daily</label>
                        <input disabled id="period-weekly" type="radio" value="weekly" v-model="emailReport.period">
                        <label for="period-weekly">Weekly</label>
                        <input disabled id="period-monthly" type="radio" value="monthly" v-model="emailReport.period">
                        <label for="period-monthly">Monthly</label>
                    </div>
                </div>
                <div class="x-section">
                    <h4>Email List</h4>
                    <vm-select v-model="emailReport.emails" multiple filterable allow-create placeholder=""
                               no-data-text="Type mail addresses..." :default-first-option="true" disabled/>
                </div>
                <div class="x-section x-btn-container">
                    <a class="x-btn disabled" tabindex="6">Save</a>
                    <a class="x-btn disabled inverse" tabindex="7">Test Now</a>
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
            ...mapActions({downloadReport: DOWNLOAD_REPORT})
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