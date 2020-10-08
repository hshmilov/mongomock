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
    <ExpressionActions
      v-if="!readOnly"
      :is-column-in-table="isColumnInTable"
      :disabled-toggle-field="!condition.field"
      class-name="child"
      @duplicate="$emit('duplicate')"
      @toggle-column="$emit('toggle-column', fullField)"
      @remove="$emit('remove')"
    />
  </div>
</template>

<script>
import _keyBy from 'lodash/keyBy';
import XSelect from '@axons/inputs/select/Select.vue';
import XConditionFunction from '@neurons/schema/query/ConditionFunction.vue';
import ExpressionActions from '@neurons/schema/query/ExpressionActions.vue';
import { getUpdatedValueAfterFieldChange } from '@/logic/condition';

export default {
  name: 'XConditionComplexFieldChild',
  components: {
    XSelect, XConditionFunction, ExpressionActions,
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
    viewFields: {
      type: Array,
      default: () => ([]),
    },
    parentField: {
      type: String,
      default: '',
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
    fullField() {
      return `${this.parentField}.${this.condition.field}`;
    },
    isColumnInTable() {
      return this.viewFields.includes(this.fullField);
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
