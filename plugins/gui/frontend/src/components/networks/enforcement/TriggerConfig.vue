<template>
  <div class="x-trigger-config">
    <div class="main">
      <h4 class="trigger-title">
        Input
      </h4>
      <div>Select the Saved Query for the Enforcement Set to act on:</div>
      <div class="config">
        <div class="config-base">
          <label>Saved Query:</label>
          <div class="base-query">
            <XSelectSymbol
              v-model="viewEntity"
              :options="entityOptions"
              type="icon"
              placeholder="mod"
              :read-only="readOnly || entityOptions.length === 0"
              minimal
            />
            <XSelect
              v-model="config.view.id"
              :options="viewOptions"
              searchable
              placeholder="query name"
              :read-only="readOnly || entityOptions.length === 0 || !views[viewEntity]"
              class="query-name"
            />
          </div>
        </div>
        <XCheckbox
          v-model="runOn"
          value="AddedEntities"
          :read-only="readOnly"
          label="Run on added entities only"
        />
      </div>
      <div class="section">
        <div class="header">
          <XCheckbox
            v-model="showScheduling"
            :read-only="readOnly"
          />
          <h4
            class="scheduling-title"
            @click="toggleScheduling"
          >Add Scheduling</h4>
        </div>
        <div
          v-if="showScheduling"
          class="main"
        >
          <h5 class="trigger-title">
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
            <XCheckbox
              v-model="showConditions"
              :read-only="readOnly"
            />
            <h5
              class="scheduling-title"
              @click="toggleConditions"
            >Add Conditions</h5>
          </div>
          <div>Detect changes in the query results and trigger upon</div>
          <div
            v-if="showConditions"
            class="config"
          >
            <XCheckbox
              v-model="conditions.new_entities"
              label="New entities were added to results"
              :read-only="readOnly"
            />
            <XCheckbox
              v-model="conditions.previous_entities"
              label="Previous entities were subtracted from results"
              :read-only="readOnly"
            />
            <div class="config-item">
              <XCheckbox
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
              <XCheckbox
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
      <XButton
        v-if="!readOnly"
        type="primary"
        :disabled="disableConfirm"
        @click="confirmTrigger"
      >Save</XButton>
    </div>
  </div>
</template>

<script>
import { mapState } from 'vuex';
import XSelect from '../../axons/inputs/select/Select.vue';
import XButton from '../../axons/inputs/Button.vue';
import XCheckbox from '../../axons/inputs/Checkbox.vue';
import XSelectSymbol from '../../neurons/inputs/SelectSymbol.vue';

import viewsMixin from '../../../mixins/views';
import { validateInteger } from '../../../constants/validations';

export default {
  name: 'XTriggerConfig',
  components: {
    XSelect, XButton, XCheckbox, XSelectSymbol,
  },
  mixins: [viewsMixin],
  props: {
    value: {
      type: Object,
      default: () => {},
    },
    readOnly: Boolean,
  },
  computed: {
    ...mapState({
      triggerPeriods(state) {
        return state.constants.constants.trigger_periods;
      },
    }),
    config: {
      get() {
        if (!this.value) return {};
        return this.value;
      },
      set(config) {
        this.$emit('input', config);
      },
    },
    viewEntity: {
      get() {
        return this.config.view.entity;
      },
      set(entity) {
        if (entity !== this.viewEntity) {
          this.config.view.id = '';
        }
        this.config.view.entity = entity;
      },
    },
    viewId() {
      return this.config.view.id;
    },
    runOn: {
      get() {
        return this.config.run_on;
      },
      set(runOn) {
        this.config.run_on = runOn || 'AllEntities';
      },
    },
    periodOptions() {
      return this.triggerPeriods.map((x) => Object.entries(x).map(([name, title]) => ({ name, title, id: `${name}_period` }))).map((x) => x[0]);
    },
    conditions() {
      return this.config.conditions;
    },
    disableConfirm() {
      return Boolean(!(this.config.view.id && this.config.view.entity));
    },
    viewOptions() {
      if (!this.views || !this.viewEntity) {
        return [];
      }
      if (!this.views[this.viewEntity]) {
        return [{
          name: this.viewId,
          title: 'Missing Permissions',
        }];
      }
      return this.views[this.viewEntity];
    },
    showScheduling: {
      get() {
        return this.config.period !== 'never';
      },
      set(show) {
        this.config.period = show ? 'all' : 'never';
      },
    },
    anyConditions() {
      if (!this.conditions) return false;
      // the reason for the '!!' is that these conditions might be integers
      return (!!this.conditions.new_entities) || (!!this.conditions.previous_entities)
                        || (!!this.conditions.above) || (!!this.conditions.below);
    },
    showAbove: {
      get() {
        return Boolean(this.config.conditions.above);
      },
      set(show) {
        this.config.conditions.above = show ? 1 : null;
      },
    },
    showBelow: {
      get() {
        return Boolean(this.config.conditions.below);
      },
      set(show) {
        this.config.conditions.below = show ? 1 : null;
      },
    },
    above: {
      get() {
        return this.conditions.above;
      },
      set(value) {
        if (!value) return;
        this.conditions.above = parseInt(value, 10) > 0 ? parseInt(value, 10) : 0;
      },
    },
    below: {
      get() {
        return this.conditions.below;
      },
      set(value) {
        if (!value) return;
        this.conditions.below = parseInt(value, 10) > 0 ? parseInt(value, 10) : 0;
      },
    },
  },
  data() {
    return {
      showConditions: false,
    };
  },
  mounted() {
    this.showConditions = this.anyConditions;
  },
  methods: {
    validateInteger,
    confirmTrigger() {
      this.$emit('confirm');
    },
    toggleScheduling() {
      this.showScheduling = !this.showScheduling;
    },
    toggleConditions() {
      this.showConditions = !this.showConditions;
      if (!this.showConditions) {
        this.config.conditions = {
          new_entities: false,
          previous_entities: false,
          above: null,
          below: null,
        };
      }
    },
  },
};
</script>

<style lang="scss">
    .x-trigger-config {
        display: grid;
        grid-template-rows: calc(100% - 30px) 30px;
        align-items: flex-start;
        height: 100%;
        .main {
            overflow: auto;
            height: 100%;
            .trigger-title {
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
                    .scheduling-title {
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
