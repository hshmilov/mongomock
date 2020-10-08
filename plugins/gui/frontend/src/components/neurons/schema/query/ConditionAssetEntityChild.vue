<template>
  <div class="x-condition-asset-entity-child x-condition__child">
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
    <ExpressionActions
      v-if="!readOnly"
      :is-column-in-table="isColumnInTable"
      :disabled-toggle-field="!condition.field"
      class-name="child"
      @duplicate="$emit('duplicate')"
      @toggle-column="$emit('toggle-column', condition.field)"
      @remove="$emit('remove')"
    />
  </div>
</template>

<script>
import _keyBy from 'lodash/keyBy';
import XStringView from '@neurons/schema/types/string/StringView.vue';
import XSelect from '@axons/inputs/select/Select.vue';
import XConditionFunction from '@neurons/schema/query/ConditionFunction.vue';
import ExpressionActions from '@neurons/schema/query/ExpressionActions.vue';
import { getUpdatedValueAfterFieldChange } from '@/logic/condition';

export default {
  name: 'XConditionAssetEntityChild',
  components: {
    XStringView, XSelect, XConditionFunction, ExpressionActions,
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
    viewFields: {
      type: Array,
      default: () => ([]),
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
  .child-field {
    display: flex;

    &__type {
      width: calc(60px + 16px);
      border: 1px solid $grey-2;
      border-radius: 2px 0 0 2px;
      padding: 0 8px;
      display: flex;
      align-items: center;

      .logo {
        max-width: 30px;
        height: auto;
        max-height: 24px;
      }
    }

    .x-select {
      margin-left: -1px;
      border-radius: 0 2px 2px 0;
      width: 100%;
      max-width: 180px;
    }
  }
}
</style>
