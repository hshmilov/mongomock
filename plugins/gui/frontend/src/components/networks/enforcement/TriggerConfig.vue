<template>
  <div class="x-trigger-config">
    <div class="main">
      <h4 class="title">
        Input
      </h4>
      <div>Select the Saved Query for the Enforcement Set to act on:</div>
      <div class="config">
        <div class="config-base">
          <label>Saved Query:</label>
          <div class="base-query">
            <x-select-symbol
              v-model="config.view.entity"
              :options="entityOptions"
              type="icon"
              placeholder="mod"
              :read-only="readOnly"
              minimal
            />
            <x-select
              v-model="config.view.name"
              :options="viewOptions"
              searchable
              placeholder="query name"
              :read-only="readOnly"
              class="query-name"
            />
          </div>
        </div>
        <x-checkbox
          v-model="config.run_on"
          value="AddedEntities"
          :read-only="readOnly"
          label="Run on added entities only"
        />
      </div>
      <div class="section">
        <div class="header">
          <x-checkbox
            v-model="showScheduling"
            :read-only="readOnly"
          />
          <h4
            class="title"
            @click="toggleScheduling"
          >Add Scheduling</h4>
        </div>
        <div
          v-if="showScheduling"
          class="main"
        >
          <h5 class="title">
            Recurrence
          </h5>
          <div class="config">
            <div
              v-for="period in periodOptions"
              :key="period.name"
              class="list-item"
            >
              <input
                :id="period.id"
                v-model="config.period"
                type="radio"
                :value="period.name"
                :disabled="readOnly"
              >
              <label
                :for="period.id"
                class="radio-label"
              >{{ period.title }}</label>
            </div>
          </div>
          <div class="header">
            <x-checkbox
              v-model="showConditions"
              :read-only="readOnly"
            />
            <h5
              class="title"
              @click="toggleConditions"
            >Add Conditions</h5>
          </div>
          <div>Detect changes in the query results and trigger upon</div>
          <div
            v-if="showConditions"
            class="config"
          >
            <x-checkbox
              v-model="conditions.new_entities"
              label="New entities were added to results"
              :read-only="readOnly"
            />
            <x-checkbox
              v-model="conditions.previous_entities"
              label="Previous entities were subtracted from results"
              :read-only="readOnly"
            />
            <div class="config-item">
              <x-checkbox
                v-model="showAbove"
                label="The number of results is above..."
                :read-only="readOnly"
              />
              <input
                v-if="showAbove"
                v-model="above"
                type="number"
                :disabled="readOnly"
                class="above"
                @keypress="validateInteger"
              >
            </div>
            <div class="config-item">
              <x-checkbox
                v-model="showBelow"
                label="The number of results is below..."
                :read-only="readOnly"
              />
              <input
                v-if="showBelow"
                v-model="below"
                type="number"
                :disabled="readOnly"
                class="below"
                @keypress="validateInteger"
              >
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="footer">
      <x-button
        v-if="!readOnly"
        :disabled="disableConfirm"
        @click="confirmTrigger"
      >Save</x-button>
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
    import {mapState} from 'vuex'

    export default {
        name: 'XTriggerConfig',
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
            ...mapState({
                triggerPeriods(state) {
                    return state.constants.constants.trigger_periods
                }
            }),
            config: {
                get() {
                    if (!this.value) return {}
                    return this.value
                },
                set(config) {
                    this.$emit('input', config)
                }
            },
            viewEntity() {
              return this.config.view.entity
            },
            periodOptions() {
                return Object.entries(this.triggerPeriods).map(([name, title]) => {
                    return {
                        name, title, id: `${name}_period`
                    }
                })
            },
            conditions() {
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
            },
            anyConditions() {
                if (!this.conditions) return false
                return this.conditions.new_entities || this.conditions.previous_entities
                        || this.conditions.above || this.conditions.below
            },
            showAbove: {
                get() {
                    return Boolean(this.config.conditions.above)
                },
                set(show) {
                    this.config.conditions.above = show? 1: null
                }
            },
            showBelow: {
                get() {
                    return Boolean(this.config.conditions.below)
                },
                set(show) {
                    this.config.conditions.below = show? 1: null
                }
            },
            above: {
                get() {
                    return this.conditions.above
                },
                set(value) {
                  if (!value) return
                  this.conditions.above = parseInt(value) > 0 ? parseInt(value) : 0
                }
            },
            below: {
                get() {
                    return this.conditions.below
                },
                set(value) {
                  if (!value) return
                  this.conditions.below = parseInt(value) > 0 ? parseInt(value) : 0
                }
            }
        },
        data() {
            return {
              showConditions: false
            }
        },
        watch: {
            runOn() {
                if (!this.runOn) {
                    this.config.run_on = 'AllEntities'
                }
            },
            viewEntity(newEntity, oldEntity) {
                if (newEntity !== oldEntity) {
                  this.config.view.name = ''
                }
            }
        },
        mounted() {
            this.showConditions = this.anyConditions
        },
        methods: {
            validateInteger,
            confirmTrigger() {
                this.$emit('confirm')
            },
            toggleScheduling() {
                this.showScheduling = !this.showScheduling
            },
            toggleConditions() {
                this.showConditions = !this.showConditions
                if (!this.showConditions) {
                  this.config.conditions = {
                    new_entities: false,
                    previous_entities: false,
                    above: null,
                    below: null
                  }
                }
            }
        }
    }
</script>

<style lang="scss">
    .x-trigger-config {
        display: grid;
        grid-template-rows: calc(100% - 30px) 30px;
        align-items: flex-start;
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
                }
            }
        }
        .footer {
            text-align: right;
        }
    }
</style>