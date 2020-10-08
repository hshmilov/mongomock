<template>
  <div class="x-condition-complex-field x-condition__parent">
    <XSelectTypedField
      :value="field"
      :filtered-adapters="condition.filteredAdapters"
      :options="schema"
      :read-only="readOnly"
      @input="onChangeField"
    />
    <template v-for="{ i, expression } in children">
      <XConditionComplexFieldChild
        :key="`condition_${i}`"
        :parent-field="field"
        :schema="childrenSchema"
        :condition="expression"
        :read-only="readOnly"
        :view-fields="viewFields"
        @change="onChangeChild(i, $event)"
        @remove="onRemoveChild(i)"
        @duplicate="onDuplicateChild(i)"
        @toggle-column="toggleColumn"
      />
    </template>
    <slot />
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import _keyBy from 'lodash/keyBy';
import XSelectTypedField from '@neurons/inputs/SelectTypedField.vue';
import { GET_MODULE_SCHEMA } from '@store/getters';
import XConditionComplexFieldChild from '@neurons/schema/query/ConditionComplexFieldChild.vue';


export default {
  name: 'XConditionComplexField',
  components: {
    XSelectTypedField, XConditionComplexFieldChild,
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
    viewFields: {
      type: Array,
      default: () => ([]),
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
      return this.getModuleSchema(this.module, true, true);
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
    onDuplicateChild(index) {
      this.$emit('duplicate-child', index);
    },
    toggleColumn(columnName) {
      this.$emit('toggle-column', columnName);
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
