<template>
  <div class="x-condition-function-field-comparison">
    <XSelect
      v-if="opsList.length"
      :value="operatorProxy"
      :options="opsList"
      placeholder="func..."
      class="expression-comp"
      :read-only="readOnly"
      @input="onInputOperator"
    />
    <Component
      :is="'integer'"
      v-if="showArgument"
      :value="argumentProxy"
      :schema="valueSchema"
      :read-only="readOnly"
      :clearable="false"
      class="argument"
      :class="{'grid-span2': !opsList.length}"
      @input="onInputArgument"
    />
    <div v-else />
  </div>
</template>

<script>
import XSelect from '../../../axons/inputs/select/Select.vue';
import integer from '../types/numerical/IntegerEdit.vue';

import {
  equalsFilter, dateFilter,
} from '../../../../constants/filter';

export default {
  name: 'XConditionFunctionFieldComparison',
  components: {
    XSelect, integer,
  },
  props: {
    schema: {
      type: Object,
      required: true,
    },
    operator: {
      type: String,
      default: '',
    },
    argument: {
      type: [String, Number, Boolean, Array],
      default: null,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    operatorProxy() {
      return this.operator;
    },
    argumentProxy() {
      return this.argument[1];
    },
    valueSchema() {
      return { type: 'integer' };
    },
    opsList() {
      if (this.schema.format !== 'date-time') {
        return equalsFilter;
      }
      return dateFilter;
    },
    showArgument() {
      return ['<Days', '>Days'].includes(this.operator);
    },
  },
  methods: {
    checkTypeAndOperator(expectedTypes, expectedOps) {
      return expectedTypes.includes(this.schema.type) && expectedOps.includes(this.operator);
    },
    onInputOperator(compOp) {
      const value = this.argument[0];
      this.$emit('update', { compOp, value });
    },
    onInputArgument(value) {
      if (['<Days', '>Days'].includes(this.operator)) {
        const subvalue = value != '' ? value : '0';
        this.$emit('update', { subvalue });
        return;
      }
      this.$emit('update', { value });
    },
  },
};
</script>

<style lang="scss">
  .x-condition-function-field-comparison {
    display: grid;
    grid-template-columns: 80px auto;
    grid-gap: 4px;

    .argument {
      width: auto;
      min-width: 0;
    }
  }
</style>
