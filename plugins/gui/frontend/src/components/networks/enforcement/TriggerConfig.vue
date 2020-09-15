<template>
  <div class="x-trigger-config">
    <h4 class="main-trigger-title">
      Saved Query
    </h4>
    <div>Select the Saved Query for the enforcement set to act on:</div>
    <div class="config">
      <div class="config-base">
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
            :options="currentViewOptions"
            searchable
            placeholder="query name"
            :read-only="readOnly || entityOptions.length === 0 || !views[viewEntity]"
            class="query-name"
          />
        </div>
      </div>
      <XCheckbox
        v-model="runOn"
        class="added-entities"
        value="AddedEntities"
        :read-only="readOnly"
        label="Run on added entities only"
      />
    </div>
    <h4 class="trigger-title">Custom Scheduling</h4>
    <XSwitch
      :checked="showScheduling"
      label="Enable custom scheduling"
      :read-only="readOnly"
      @change="showScheduling = !showScheduling"
    />
    <template v-if="showScheduling">
      <h5 class="trigger-subtitle">Custom Schedule Settings</h5>
      <XForm
        v-model="periodData"
        :schema="periodSchema"
        :read-only="readOnly"
        @validate="onPeriodValidate"
      />
      <h5 class="trigger-subtitle">Additional Conditions</h5>
      <XSwitch
        :checked="showConditions"
        label="Apply additional enforcement execution conditions"
        :read-only="readOnly"
        @change="toggleConditions"
      />
      <div
        v-if="showConditions"
        class="config"
      >
        <XCheckbox
          v-model="conditions.new_entities"
          label="Only when assets have been added since the last execution"
          :read-only="readOnly"
        />
        <XCheckbox
          v-model="conditions.previous_entities"
          label="Only when assets have been removed since the last execution"
          :read-only="readOnly"
        />
        <div class="config-item">
          <XCheckbox
            v-model="showAbove"
            label="Only when the number of assets is above N"
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
            label="Only when the number of assets is below N"
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
    </template>
  </div>
</template>

<script>
import { mapState } from 'vuex';
import XSwitch from '@axons/inputs/Switch.vue';
import XSelect from '@axons/inputs/select/Select.vue';
import XCheckbox from '@axons/inputs/Checkbox.vue';
import XSelectSymbol from '@neurons/inputs/SelectSymbol.vue';
import XForm from '@neurons/schema/Form.vue';

import viewsMixin from '../../../mixins/views';
import { validateInteger } from '../../../constants/validations';
import { weekDays, monthDays } from '../../../constants/utils';

export default {
  name: 'XTriggerConfig',
  components: {
    XSelect, XCheckbox, XSelectSymbol, XSwitch, XForm,
  },
  mixins: [viewsMixin],
  props: {
    value: {
      type: Object,
      default: () => {},
    },
    readOnly: Boolean,
  },
  data() {
    return {
      showConditions: false,
      weekDays: weekDays.map(this.getDayObject),
      monthDays: monthDays.map(this.getDayObject),
      defaultRecurrence: {
        daily: 1,
        weekly: ['0'],
        monthly: ['1'],
      },
      defaultTime: {
        period_time: '13:00',
      },
      periodValid: true,
    };
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
    timeSchema() {
      return {
        name: 'period_time',
        type: 'string',
        format: 'time',
        title: 'Scheduled run time',
      };
    },
    periodSchema() {
      return {
        type: 'array',
        items: [{
          name: 'conditional',
          type: 'string',
          title: 'Repeat scheduled run',
          enum: this.periodOptions,
        }, {
          name: 'daily',
          type: 'array',
          title: '',
          required: ['period_recurrence', 'period_time'],
          items: [{
            name: 'period_recurrence',
            type: 'integer',
            title: 'Scheduled run every (days)',
            min: 1,
          }, this.timeSchema],
        }, {
          name: 'weekly',
          type: 'array',
          title: '',
          required: ['period_recurrence', 'period_time'],
          items: [{
            name: 'period_recurrence',
            type: 'array',
            title: 'Scheduled run day(s)',
            items: {
              title: '',
              name: 'recurrence',
              type: 'string',
              enum: this.weekDays,
            },
          }, this.timeSchema],
        }, {
          name: 'monthly',
          type: 'array',
          title: '',
          required: ['period_recurrence', 'period_time'],
          items: [{
            name: 'period_recurrence',
            type: 'array',
            title: 'Scheduled run day(s)',
            items: {
              title: '',
              name: 'recurrence',
              type: 'string',
              enum: this.monthDays,
            },
          }, this.timeSchema],
        }],
        required: ['conditional'],
      };
    },
    conditions() {
      return this.config.conditions;
    },
    disableConfirm() {
      return Boolean(!(this.config.view.id && this.config.view.entity && this.periodValid));
    },
    currentViewOptions() {
      return this.viewSelectOptionsGetter(true)(this.viewEntity, this.viewId);
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
    periodData: {
      get() {
        const { period, period_recurrence, period_time } = this.config;
        const periodSettings = {
          conditional: period,
        };
        if (period !== 'all') {
          periodSettings[period] = {
            period_recurrence,
            period_time,
          };
        }
        return periodSettings;
      },
      set({ conditional, ...periodSettings }) {
        this.config.period = conditional;
        if (periodSettings[conditional]) {
          this.config = { ...this.config, ...periodSettings[conditional] };
        } else {
          this.config = {
            ...this.config,
            period_recurrence: this.defaultRecurrence[conditional],
            ...this.defaultTime,
          };
        }
      },
    },
  },
  watch: {
    showScheduling(isSchedulingShown) {
      if (!isSchedulingShown) {
        this.periodValid = true;
      }
    },
    disableConfirm(isError) {
      this.$emit('trigger-validity-changed', !isError);
    },
  },
  mounted() {
    this.showConditions = this.anyConditions;
  },
  methods: {
    validateInteger,
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
    onPeriodValidate(isValid) {
      this.periodValid = isValid;
    },
    getDayObject(day) {
      return { title: day.title, name: String(day.name) };
    },
  },
};
</script>

<style lang="scss">
  .x-trigger-config {

    .main-trigger-title {
      margin: 10px 0 4px 0;
    }

    .trigger-title {
      margin: 24px 0 4px 0;
    }

    .trigger-subtitle {
      margin: 16px 0 4px 0;
    }

    .config {
      margin: 8px 0;

      .added-entities {
        margin-top: 8px;
      }

      .config-base {
        display: flex;
        align-items: center;

        .base-query {
          flex: 1 0 auto;
          display: flex;

          .x-select-symbol {
            width: 60px;
          }

          .query-name {
            flex: 1 0 auto;
          }
        }
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

    .x-form {
      > .x-array-edit .list {
        grid-template-columns: 1fr;

        .item_period_recurrence input {
          width: 200px;
        }

        .ant-form-item .period_recurrence_select {
          width: 400px;
        }
      }
      .form-error {
        margin-top: 0;
      }
    }
  }
</style>
