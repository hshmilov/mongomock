<template>
  <div class="x-condition-asset-entity-child x-condition__child">
    <div class="child-field">
      <div class="child-field__type">
        <x-string-view
          :value="parentField"
          :schema="{format: 'logo'}"
        />
      </div>
      <x-select
        v-model="field"
        :options="schema"
        searchable
        :read-only="readOnly"
        class="field-select"
      />
    </div>
    <x-condition-function
      :schema="fieldSchema"
      :operator="condition.compOp"
      :argument="condition.value"
      :read-only="readOnly"
      @update="onUpdateConditionFunction"
    />
    <x-button
      v-if="!readOnly"
      link
      class="child-remove"
      @click="$emit('remove')"
    >x</x-button>
  </div>
</template>

<script>
import _keyBy from 'lodash/keyBy';
import _isEqual from 'lodash/isEqual';
import XStringView from '../types/string/StringView.vue';
import XSelect from '../../../axons/inputs/select/Select.vue';
import XConditionFunction from './ConditionFunction.vue';
import XButton from '../../../axons/inputs/Button.vue';
import { getUpdatedValueAfterFieldChange, getValueSchema } from '../../../../logic/condition';


export default {
  name: 'XConditionAssetEntityChild',
  components: {
    XStringView, XSelect, XConditionFunction, XButton,
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
