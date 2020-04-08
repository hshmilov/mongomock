<template>
  <!-- Date Picker -->
  <x-date-edit
    v-if="isDate"
    v-model="data"
    :read-only="readOnly"
    :minimal="true"
    :clearable="clearable"
    @input="input"
  />
  <x-time-picker
    v-else-if="isTime"
    v-model="data"
    :schema="schema"
    :read-only="readOnly"
    @validate="onValidate"
    @input="input"
  />
  <textarea
    v-else-if="isText"
    v-model="data"
    :maxlength="schema.limit"
    :disabled="readOnly || schema.readOnly"
    rows="3"
    @input="input"
  />
  <div
    v-else-if="inputType"
    class="string-input-container"
  >
    <input
      :id="schema.name"
      v-model="processedData"
      :type="inputType"
      :class="{'error-border': error}"
      :disabled="readOnly || schema.readOnly"
      :placeholder="schema.placeholder"
      @input="input"
      @focusout.stop="focusout"
      @focusin="onFocusIn"
      @keydown="onKeyPress"
    >
    <slot name="icon" />
  </div>
  <!-- Select from enum values -->
  <x-select
    v-else-if="enumOptions && !schema.source"
    v-model="processedData"
    :options="enumOptions"
    placeholder="value..."
    :searchable="true"
    :class="{'error-border': error}"
    :read-only="readOnly || schema.readOnly"
    @input="input"
    @focusout.stop="validate"
  />
  <component
    :is="dynamicType"
    v-else-if="enumOptions && schema.source"
    v-model="processedData"
    :schema="schema"
    :searchable="true"
    placeholder="value…"
    :class="{'error-border': error, [`${schema.source.key}`]: true}"
    :read-only="readOnly || schema.readOnly"
    @input="input"
    @focusout.stop="validate"
  />
</template>

<script>
import xSelect from '@axons/inputs/select/Select.vue';
import {
  xTagSelect,
  XInstancesSelect,
  xClientConnectionSelect,
  xRolesSelect,
} from '@axons/inputs/dynamicSelects';
import xTimePicker from '@axons/inputs/TimePicker.vue';
import { validateEmail } from '@constants/validations';
import primitiveMixin from '../../../../../mixins/primitive';
import xDateEdit from './DateEdit.vue';

export default {
  name: 'XStringEdit',
  components: {
    xSelect,
    xDateEdit,
    xTagSelect,
    XInstancesSelect,
    xTimePicker,
    xClientConnectionSelect,
    xRolesSelect,
  },
  mixins: [primitiveMixin],
  props: {
    clearable: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      data: '',
      valid: true,
      error: '',
    };
  },
  computed: {
    processedData: {
      get() {
        return this.isUnchangedPassword ? '********' : this.data;
      },
      set(newVal) {
        this.data = newVal;
      },
    },
    isEmailValid() {
      return (!this.data || validateEmail(this.data)) ? '' : 'error-border';
    },
    isDate() {
      return (this.schema.format === 'date-time' || this.schema.format === 'date');
    },
    isTime() {
      return this.schema.format === 'time'
    },
    isText() {
      return this.schema.format === 'text';
    },
    isMail() {
      return this.schema.format === 'email';
    },
    isUnchangedPassword() {
      return this.inputType === 'password' && this.data && this.data[0] === 'unchanged';
    },
    inputType() {
      if (this.schema.format && this.schema.format === 'password') {
        return 'password';
      } if (this.schema.enum) {
        return '';
      }
      return 'text';
    },
    dynamicType() {
      if (!this.schema.source) return null;
      switch (this.schema.source.key) {
        case 'all-tags':
          return 'xTagSelect';
        case 'all-instances':
          return 'XInstancesSelect';
        case 'all-connection-labels':
          return 'xClientConnectionSelect';
        case 'all-roles':
          return 'xRolesSelect';
        default:
          return null;
      }
    },
  },
  methods: {
    formatData() {
      return this.data;
    },
    onFocusIn() {
      if (this.isUnchangedPassword) {
        this.data = '';
      }
    },
    onValidate(validity) {
      this.$emit('validate', validity);
    },
    checkData() {
      return !this.isMail ? true : !this.isEmailValid;
    },
  },
};
</script>

<style lang="scss">
</style>
