<template>
  <div class="x-condition-function">
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
      :is="valueType"
      v-if="showArgument"
      :value="argumentProxy"
      :schema="valueSchema"
      :operator="operator"
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
import _isEmpty from 'lodash/isEmpty';
import _isEqual from 'lodash/isEqual';
import _get from 'lodash/get';
import _isPlainObject from 'lodash/isPlainObject';
import XSelect from '../../../axons/inputs/select/Select.vue';
import string from '../types/string/StringEdit.vue';
import number from '../types/numerical/NumberEdit.vue';
import bool from '../types/boolean/BooleanEdit.vue';
// eslint-disable-next-line import/no-duplicates
import integer from '../types/numerical/IntegerEdit.vue';
// eslint-disable-next-line import/no-duplicates
import array from '../types/numerical/IntegerEdit.vue';
import { SIZE_OPERATOR } from '../../../../constants/filter';

import {
  checkShowValue, getOpsList, getOpsMap, schemaEnumFind, getValueSchema,
} from '../../../../logic/condition';


export default {
  name: 'XConditionFunction',
  components: {
    XSelect, string, number, integer, bool, array,
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
      if (!Object.keys(this.opsMap).includes(this.operator)) {
        return '';
      }
      return this.operator;
    },
    argumentProxy() {
      if (!_isEmpty(this.valueSchema.enum) && !schemaEnumFind(this.valueSchema, this.argument)
          && this.operator !== SIZE_OPERATOR) {
        return null;
      }
      return this.argument;
    },
    valueSchema() {
      const schema = getValueSchema(this.schema, this.operator);
      const firstOption = _get(schema, 'enum[0]');
      if (_isPlainObject(firstOption) && 'name' in firstOption) {
        // A special case for `Saved Query` so it doesn't offer options with no actual filter
        const filteredEnum = schema.enum.filter((item) => item.name);
        return { ...schema, enum: filteredEnum };
      }
      return schema;
    },
    valueType() {
      return this.valueSchema.type;
    },
    opsMap() {
      return getOpsMap(this.schema);
    },
    opsList() {
      return getOpsList(this.opsMap);
    },
    showArgument() {
      return checkShowValue(this.schema, this.operatorProxy);
    },
  },
  methods: {
    checkTypeAndOperator(expectedTypes, expectedOps) {
      return expectedTypes.includes(this.schema.type) && expectedOps.includes(this.operator);
    },
    onInputOperator(compOp) {
      let value = this.argument;
      // Reset the value if the value schema is about to change
      if (!_isEqual(getValueSchema(this.schema, compOp), this.valueSchema)) {
        value = '';
      }
      this.$emit('update', { compOp, value });
    },
    onInputArgument(value) {
      this.$emit('update', { value });
    },
  },
};
</script>

<style lang="scss">
  .x-condition-function {
    display: grid;
    grid-template-columns: 80px auto;
    grid-gap: 4px;

    .argument {
      width: auto;
      min-width: 0;
    }
  }
</style>
