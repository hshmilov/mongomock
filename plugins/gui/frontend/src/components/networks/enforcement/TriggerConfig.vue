<template>
    <div class="x-trigger-config">
        <div class="main">
            <h4 class="title">Enforcement Input</h4>
            <div>Describe the entities for the Enforcement to run on:</div>
            <div class="config">
                <div class="config-base">
                    <label>Saved Query:</label>
                    <div class="base-query">
                        <x-select-symbol v-bind="{options: entityOptions, type: 'icon', placeholder: 'mod', readOnly}" minimal v-model="config.view.entity" />
                        <x-select :options="viewOptions" searchable placeholder="query name" :read-only="readOnly"
                                  v-model="config.view.name" class="query-name" />
                    </div>
                </div>
                <x-checkbox v-model="config.run_on" value="AddedEntities" :read-only="readOnly" label="Run on added entities only" />
            </div>
            <div class="section">
                <div class="header">
                    <x-checkbox v-model="showScheduling" :read-only="readOnly" />
                    <h4 class="title" @click="toggleScheduling">Add Scheduling</h4>
                </div>
                <div v-if="showScheduling" class="main">
                    <h5 class="title">Recurrence</h5>
                    <div>Monitor your description over the period:</div>
                    <div class="config">
                        <div v-for="period in periodOptions" class="list-item">
                            <input type="radio" :id="period.id" :value="period.name" v-model="config.period" :disabled="readOnly">
                            <label :for="period.id" class="radio-label">{{period.title}}</label>
                        </div>
                    </div>
                    <h5 class="title">Conditions</h5>
                    <div>Detect the monitored changes and trigger upon:</div>
                    <div class="config">
                        <x-checkbox label="New entities were added to results" v-model="conditions.new_entities" :read-only="readOnly" />
                        <x-checkbox label="Previous entities were subtracted from results" v-model="conditions.previous_entities" :read-only="readOnly" />
                        <div class="config-item">
                            <x-checkbox label="The number of results is above..." v-model="showAbove" :read-only="readOnly" />
                            <input type="number" v-if="showAbove" v-model="conditions.above" @keypress="validateInteger" :disabled="readOnly" class="above">
                        </div>
                        <div class="config-item">
                            <x-checkbox label="The number of results is below..." v-model="showBelow" :read-only="readOnly" />
                            <input type="number" v-if="showBelow" v-model="conditions.below" @keypress="validateInteger" :disabled="readOnly" class="below">
                        </div>
                    </div>
                </div>
            </div>
            </div>
        <div class="footer">
            <x-button v-if="!readOnly" :disabled="disableConfirm" @click="confirmTrigger">Save</x-button>
        </div>
    </div>
</template>

<script>
    import xSelect from '../../axons/inputs/Select.vue'
    import xButton from '../../axons/inputs/Button.vue'
    import xCheckbox from '../../axons/inputs/Checkbox.vue'
    import xSelectSymbol from '../../neurons/inputs/SelectSymbol.vue'

    import viewsMixin from '../../../mixins/views'
    import { validateInteger } from '../../../constants/utils'
    import {triggerPeriods, triggerPeriodMeta} from '../../../constants/enforcement'

    export default {
        name: 'x-trigger-config',
        components: {
            xSelect, xButton, xCheckbox, xSelectSymbol
        },
        mixins: [viewsMixin],
        props: {
            value: {
                type: Object,
                default: () => {}
            },
            readOnly: Boolean
        },
        computed: {
            config: {
                get() {
                    if (!this.value) return {}
                    return this.value
                },
                set(config) {
                    this.$emit('input', config)
                }
            },
            periodOptions() {
                return triggerPeriods.map(name => {
                    return {
                        name, title: triggerPeriodMeta[name], id: `${name}_period`
                    }
                })
            },
            conditions() {
                this.showAbove = (this.config.conditions.above !== null)
                this.showBelow = (this.config.conditions.below !== null)
                if (this.showAbove) {
                    this.config.conditions.above = parseInt(this.config.conditions.above)
                }
                if (this.showBelow) {
                    this.config.conditions.below = parseInt(this.config.conditions.below)
                }
                return this.config.conditions
            },
            disableConfirm() {
                return Boolean(!(this.config.view.name && this.config.view.entity))
            },
            runOn() {
                return this.config.run_on
            },
            viewOptions() {
                if (!this.views || !this.config.view.entity) return
                let views = this.views[this.config.view.entity]
                if (!views.some(view => view.name === this.config.view.name)) {
                    views.push({
                        name: this.config.view.name, title: `${this.config.view.name} (deleted)`
                    })
                }
                return views
            },
            showScheduling: {
                get() {
                    return this.config.period !== 'never'
                },
                set(show) {
                    this.config.period = show? 'all': 'never'
                }
            }
        },
        data() {
            return {
                showAbove: false,
                showBelow: false,
            }
        },
        watch: {
            showAbove(show) {
                this.initConditionValues(show, 'above')
            },
            showBelow(show) {
                this.initConditionValues(show, 'below')
            },
            runOn() {
                if (!this.runOn) {
                    this.config.run_on = 'AllEntities'
                }
            }
        },
        methods: {
            validateInteger,
            confirmTrigger() {
                this.$emit('confirm')
            },
            initConditionValues(show, name) {
                if (show && !this.config.conditions[name]) {
                    this.config.conditions[name] = 0
                } else if (!show) {
                    this.config.conditions[name] = null
                }
            },
            toggleScheduling() {
                this.showScheduling = !this.showScheduling
            }
        }
    }
</script>

<style lang="scss">
    .x-trigger-config {
        display: grid;
        grid-template-rows: auto 30px;
        align-items: start;
        .main {
            overflow: auto;
            height: 100%;
            .title {
                margin: 24px 0 8px;
            }
            .config {
                margin: 8px 0 8px 12px;
                .config-base {
                    display: flex;
                    align-items: center;
                    .base-query {
                        flex: 1 0 auto;
                        margin-left: 24px;
                        display: flex;
                        .x-select-symbol {
                            width: 60px;
                        }
                        .query-name {
                            flex: 1 0 auto;
                        }
                    }
                    .md-switch {
                        margin: 4px 0;
                    }
                }
                .radio-label {
                    margin-left: 8px;
                }
                .x-checkbox {
                    line-height: 24px;
                }
                .config-item {
                    display: flex;
                    align-items: center;
                    line-height: 24px;
                    .x-checkbox {
                        margin-right: 12px;
                    }
                    .above, .below {
                        flex: 1 0 auto;
                    }
                }
            }
            .section {
                .header {
                    display: flex;
                    align-items: center;
                    margin-top: 24px;
                    .x-checkbox {
                        margin-bottom: 4px;
                    }
                    .title {
                        margin: 0 0 0 8px;
                        cursor: pointer;
                    }
                }
                .main {
                    margin-left: 24px;
                    .title {
                        margin: 12px 0;
                    }
                }
            }
        }
        .footer {
            text-align: right;
        }
    }
</style>