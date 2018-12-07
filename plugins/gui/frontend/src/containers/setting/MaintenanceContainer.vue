<template>
    <md-card>
        <md-card-expand>
            <md-card-expand-trigger>
                <md-button class="x-btn link" :disabled="readOnly" id="maintenance_settings">ADVANCED SETTINGS</md-button>
            </md-card-expand-trigger>
            <md-card-expand-content>
                <md-card-content>
                    <x-checkbox v-model="allowProvision" label="Remote Support" />
                    <div v-if="allowProvision" class="x-content">
                        <div class="x-section">
                            <x-checkbox v-model="allowAnalytics" label="Anonymized Analytics" />
                            <div v-if="allowAnalytics">
                                <div class="title">Warning:</div>
                                <div class="content">{{ disableWarnings['analytics'] }}</div>
                            </div>
                            <div v-else class="title">Turning on this feature allows Axonius to proactively detect issues and notify about errors</div>
                        </div>
                        <div class="x-section">
                            <x-checkbox v-model="allowTroubleshooting" label="Remote Access" />
                            <div v-if="allowTroubleshooting">
                                <div class="title">Warning:</div>
                                <div class="content">{{ disableWarnings['troubleshooting'] }}</div>
                            </div>
                            <div v-else class="title">Turning on this feature allows Axonius to keep the system updated and speed-up issues resolution time</div>
                        </div>
                    </div>
                    <div v-else class="x-content">
                        <div class="x-section title">Turning on this feature allows Axonius to keep the system updated, speed-up issues resolution time and proactively detect issues and notify about errors</div>
                        <div class="x-section">
                            <div class="title">OR</div>
                            <div class="config">
                                <template v-if="accessEndTime">
                                    <div class="warning mr-12">Temporary Remote Support will end at: {{ accessEndTime }}</div>
                                    <button class="x-btn" @click="stopTempAccess">Stop</button>
                                </template>
                                <template v-else>
                                    <div class="mr-8">Give temporary Remote Support for</div>
                                    <input type="number" v-model="accessDuration" @keypress="validateNumber" class="mr-8" />
                                    <div class="mr-12">Hours</div>
                                    <button class="x-btn" :class="{disabled: !enableStartAccess}" @click="startTempAccess">Start</button>
                                </template>
                            </div>
                        </div>
                    </div>
                </md-card-content>
            </md-card-expand-content>
        </md-card-expand>
        <x-modal v-if="disableToConfirm" @confirm="approveDisable" @close="disableToConfirm = null"
                 approve-text="Confirm">
            <div slot="body">
                <div>
                    <div class="title">Warning:</div>
                    <div class="content">{{ disableWarnings[disableToConfirm] }}</div>
                </div>
                <div class="mt-12">Turn off this feature?</div>
            </div>
        </x-modal>
    </md-card>
</template>

<script>
    import xCheckbox from '../../components/inputs/Checkbox.vue'
    import xModal from '../../components/popover/Modal.vue'

    import { mapState, mapActions } from 'vuex'
    import {
        FETCH_MAINTENANCE_CONFIG, SAVE_MAINTENANCE_CONFIG, START_MAINTENANCE_CONFIG, STOP_MAINTENANCE_CONFIG
    } from '../../store/modules/settings'

    import { validateNumber } from '../../utils'

    export default {
        name: 'x-maintenance-container',
        components: { xCheckbox, xModal },
        props: {
            readOnly: {
                type: Boolean, default: false
            }
        },
        computed: {
            ...mapState({
                maintenance(state) {
                    return state.settings.advanced.maintenance
                }
            }),
            allowProvision: {
                get() {
                    return this.maintenance.provision
                },
                set(value) {
                    this.onMaintenanceChange('provision', value)
                }
            },
            allowAnalytics: {
                get() {
                    return this.maintenance.analytics
                },
                set(value) {
                    this.onMaintenanceChange('analytics', value)
                }
            },
            allowTroubleshooting: {
                get() {
                    return this.maintenance.troubleshooting
                },
                set(value) {
                    this.onMaintenanceChange('troubleshooting', value)
                }
            },
            accessEndTime() {
                if (!this.maintenance.timeout) return null
                let dateTime = new Date(this.maintenance.timeout)
                dateTime.setMinutes(dateTime.getMinutes() - dateTime.getTimezoneOffset())
                return dateTime.toISOString().replace(/(T|Z)/g, ' ').split('.')[0]
            },
            disableWarnings() {
                return {
                    'analytics': 'Turning off this feature prevents Axonius from proactively detecting issues and notifying about errors',
                    'troubleshooting': 'Turning off this feature prevents Axonius from updating the system and can lead to slower issue resolution time',
                    'provision': 'Turning off this feature prevents Axonius from proactively detecting issues and notifying about errors'
                }
            },
            enableStartAccess() {
                return this.accessDuration > 0
            }
        },
        data() {
            return {
                accessDuration: 24,
                disableToConfirm: null
            }
        },
        methods: {
            ...mapActions({
                saveMaintenance: SAVE_MAINTENANCE_CONFIG, fetchMaintenance: FETCH_MAINTENANCE_CONFIG,
                startMaintenance: START_MAINTENANCE_CONFIG, stopMaintenance: STOP_MAINTENANCE_CONFIG
            }),
            onMaintenanceChange(type, value) {
                if (value) {
                    this.saveMaintenance({ [ type ]: value })
                } else {
                    this.disableToConfirm = type
                }
            },
            approveDisable() {
                this.saveMaintenance({ [ this.disableToConfirm ]: false })
                this.disableToConfirm = null
            },
            validateNumber,
            startTempAccess() {
                if (!this.enableStartAccess) return
                this.startMaintenance({duration: this.accessDuration})
            },
            stopTempAccess() {
                this.stopMaintenance()
            }
        },
        created() {
            this.fetchMaintenance()
        }
    }
</script>

<style lang="scss">
    .md-card {
        box-shadow: none;
        .md-card-expand {
            min-height: 36px;
            .md-button {
                margin: 0;
            }
        }
        .md-card-content {
            min-height: 240px;
        }
        .title {
            font-weight: 400;
            display: inline-block;
        }
        .content {
            margin-left: 4px;
            display: inline;
        }
        .config {
            display: flex;
            align-items: center;
        }
        .warning {
            font-style: italic;
        }
    }
</style>