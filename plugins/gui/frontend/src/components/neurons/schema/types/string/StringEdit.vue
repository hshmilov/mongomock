<template>
  <!-- Date Picker -->
  <XDateEdit
    v-if="isDate"
    v-model="data"
    :read-only="readOnly"
    :clearable="clearable"
    @input="input"
  />
  <XTimePicker
    v-else-if="isTime"
    v-model="data"
    :schema="schema"
    :read-only="readOnly"
    @validate="onValidate"
    @input="input"
  />
  <textarea
    v-else-if="isText"
    :id="schema.name"
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
  <XSelect
    v-else-if="enumOptions && !schema.source"
    v-model="processedData"
    :options="enumOptions"
    :placeholder="placeholder"
    :searchable="true"
    :class="{'error-border': error}"
    :read-only="readOnly || schema.readOnly"
    @input="input"
    @focusout.stop="validate"
  />
  <Component
    :is="dynamicType"
    v-else-if="enumOptions && schema.source"
    v-model="processedData"
    :schema="schema"
    :searchable="true"
    :placeholder="placeholder"
    :class="{'error-border': error, [`${schema.source.key}`]: true}"
    :read-only="readOnly || schema.readOnly"
    @input="input"
    @focusout.stop="validate"
  />
</template>

<script>
import XSelect from '@axons/inputs/select/Select.vue';
import {
  XTagSelect,
  XInstancesSelect,
  clientConnectionSelectGenerator,
  XRolesSelect,
} from '@axons/inputs/dynamicSelects';
import XTimePicker from '@axons/inputs/TimePicker.vue';
import { validateEmail } from '@constants/validations';
import { osDistributionFormat, BIGGER_THAN_OPERATOR, SMALLER_THAN_OPERATOR } from '@constants/filter';
import primitiveMixin from '../../../../../mixins/primitive';
import XDateEdit from './DateEdit.vue';

export default {
  name: 'XStringEdit',
  components: {
    XSelect,
    XDateEdit,
    XTagSelect,
    XInstancesSelect,
    XTimePicker,
    XRolesSelect,
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
      return this.schema.format === 'time';
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
      } if (this.schema.format && this.schema.format === osDistributionFormat
        && this.operator !== SMALLER_THAN_OPERATOR && this.operator !== BIGGER_THAN_OPERATOR) {
        return 'text';
      } if (this.schema.enum) {
        return '';
      }
      return 'text';
    },
    dynamicType() {
      if (!this.schema.source) return null;
      switch (this.schema.source.key) {
        case 'all-tags':
          return 'XTagSelect';
        case 'all-instances':
          return 'XInstancesSelect';
        case 'all-connection-labels':
          return clientConnectionSelectGenerator(this.schema.name);
        case 'all-roles':
          return 'XRolesSelect';
        default:
          return null;
      }
    },
    placeholder() {
      return this.schema.placeholder || 'value...';
    },
  },
  methods: {
    formatData() {
      return this.data;
    },
    resetData() {
      this.data = '';
    },
    onFocusIn(event) {
      if (this.isUnchangedPassword) {
        event.target.select();
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
