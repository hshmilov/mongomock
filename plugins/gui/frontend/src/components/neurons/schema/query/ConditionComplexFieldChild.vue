<template>
  <div class="x-condition-complex-field-child x-condition__child">
    <XSelect
      v-model="field"
      :options="schema"
      searchable
      :read-only="readOnly"
      class="field-select"
    />
    <XConditionFunction
      :schema="fieldSchema"
      :operator="condition.compOp"
      :argument="condition.value"
      :read-only="readOnly"
      @update="onUpdateConditionFunction"
    />
    <XButton
      v-if="!readOnly"
      type="link"
      class="child-remove"
      @click="$emit('remove')"
    >x</XButton>
  </div>
</template>

<script>
import _keyBy from 'lodash/keyBy';
import XSelect from '../../../axons/inputs/select/Select.vue';
import XConditionFunction from './ConditionFunction.vue';
import XButton from '../../../axons/inputs/Button.vue';
import { getUpdatedValueAfterFieldChange } from '../../../../logic/condition';


export default {
  name: 'XConditionComplexFieldChild',
  components: {
    XSelect, XConditionFunction, XButton,
  },
  model: {
    prop: 'condition',
    event: 'change',
  },
  props: {
    schema: {
      type: Array,
      default: () => [],
    },
    condition: {
      type: Object,
      required: true,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    field: {
      get() {
        return this.condition.field;
      },
      set(field) {
        const value = getUpdatedValueAfterFieldChange(this.getFieldSchema(field),
          this.fieldSchema,
          this.condition.compOp,
          this.condition.value);
        this.$emit('change', { ...this.condition, field, value });
      },
    },
    schemaByName() {
      return _keyBy(this.schema, (field) => field.name);
    },
    fieldSchema() {
      return this.getFieldSchema(this.field);
    },
  },
  methods: {
    onUpdateConditionFunction(conditionFunction) {
      this.$emit('change', { ...this.condition, ...conditionFunction });
    },
    getFieldSchema(field) {
      return field
        ? this.schemaByName[field]
        : {};
    },
  },
};
</script>

<style lang="scss">
.x-condition-complex-field-child {
  > .x-select {
    margin-left: 60px;
  }
}
</style>
