<template>
  <div class="x-condition-asset-entity-child x-condition__child x-condition__scaled">
    <XExpressionOperators
      :first="first"
      :expression="condition"
      :disabled="readOnly"
      :is-column-in-table="isColumnInTable"
      :disabled-toggle-field="!condition.field"
      @change="updateExpression"
      @duplicate="$emit('duplicate')"
      @toggle-column="$emit('toggle-column', condition.field)"
      @remove="$emit('remove')"
    >
      <template #default>
        <div class="x-condition-asset-entity-child__content">
          <div class="child-field">
            <div class="child-field__type">
              <XStringView
                :value="parentField"
                :schema="{format: 'logo'}"
              />
            </div>
            <XSelect
              v-model="field"
              :options="schema"
              searchable
              :read-only="readOnly"
              class="field-select"
            />
          </div>
          <XConditionFunction
            :schema="fieldSchema"
            :operator="condition.compOp"
            :argument="condition.value"
            :read-only="readOnly"
            @update="onUpdateConditionFunction"
          />
        </div>
      </template>
    </XExpressionOperators>
  </div>
</template>

<script>
import _keyBy from 'lodash/keyBy';
import XStringView from '@neurons/schema/types/string/StringView.vue';
import XSelect from '@axons/inputs/select/Select.vue';
import XConditionFunction from '@neurons/schema/query/ConditionFunction.vue';
import XExpressionOperators from './ExpressionOperators.vue';
import { getUpdatedValueAfterFieldChange } from '@/logic/condition';

export default {
  name: 'XConditionAssetEntityChild',
  components: {
    XStringView, XSelect, XConditionFunction, XExpressionOperators,
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
    parentField: {
      type: String,
      required: true,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
    first: {
      type: Boolean,
      default: false,
    },
    viewFields: {
      type: Array,
      default: () => ([]),
    },
    fieldType: {
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
    isColumnInTable() {
      return this.viewFields.includes(this.condition.field);
    },
  },
  methods: {
    updateExpression(value) {
      this.$emit('change', { ...this.condition, ...value });
    },
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
.x-condition-asset-entity-child {
  &.x-condition__child {
    display: block;
  }
  &__content {
    display: grid;
    grid-gap: 4px;
    grid-template-columns: 240px auto;
    min-width: 0;
  }
}
</style>
