<template>
  <div class="x-condition-complex-field x-condition__parent">
    <x-select-typed-field
      :value="field"
      :filtered-adapters="condition.filteredAdapters"
      :options="schema"
      :read-only="readOnly"
      @input="onChangeField"
    />
    <template v-for="{ i, expression } in children">
      <x-condition-complex-field-child
        :key="`condition_${i}`"
        :schema="childrenSchema"
        :condition="expression"
        :read-only="readOnly"
        @change="onChangeChild(i, $event)"
        @remove="onRemoveChild(i)"
      />
    </template>
    <slot />
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import _keyBy from 'lodash/keyBy';
import xSelectTypedField from '../../inputs/SelectTypedField.vue';
import xConditionComplexFieldChild from './ConditionComplexFieldChild.vue';

import { GET_MODULE_SCHEMA } from '../../../../store/getters';


export default {
  name: 'XConditionComplexField',
  components: {
    xSelectTypedField, xConditionComplexFieldChild,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    condition: {
      type: Object,
      default: undefined,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    ...mapGetters({
      getModuleSchema: GET_MODULE_SCHEMA,
    }),
    field() {
      return this.condition.field;
    },
    children() {
      return this.condition.children;
    },
    schema() {
      return this.getModuleSchema(this.module, true);
    },
    schemaByName() {
      return this.schema.reduce((map, item) => ({
        ...map,
        ..._keyBy(item.fields, (field) => field.name),
      }), []);
    },
    childrenSchema() {
      if (!this.field) {
        return [];
      }
      const fieldSchema = this.schemaByName[this.field];
      return Array.isArray(fieldSchema.items)
        ? fieldSchema.items
        : fieldSchema.items.items;
    },
  },
  methods: {
    onChangeField(field, fieldType, filteredAdapters) {
      this.$emit('update', {
        field,
        fieldType,
        filteredAdapters,
      });
    },
    onChangeChild(index, expression) {
      this.$emit('change-child', { index, expression });
    },
    onRemoveChild(index) {
      this.$emit('remove-child', index);
    },
  },
};

</script>

<style lang="scss">
  .x-condition-complex-field {

    .x-select-typed-field {
      width: 240px;
    }
  }
</style>
