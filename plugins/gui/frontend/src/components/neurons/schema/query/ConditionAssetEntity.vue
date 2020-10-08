<template>
  <div class="x-condition-asset-entity x-condition__parent">
    <div class="parent-field">
      <XSelectSymbol
        v-model="field"
        :options="schema"
        minimal
        :read-only="readOnly"
      />
      <div
        v-if="field"
        class="parent-field__name"
      >{{ fieldTitle }}</div>
    </div>
    <template v-for="{ i, expression } in children">
      <XConditionAssetEntityChild
        :key="`condition_${i}`"
        :schema="childrenSchema"
        :condition="expression"
        :parent-field="field"
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
import XSelectSymbol from '@neurons/inputs/SelectSymbol.vue';
import XConditionAssetEntityChild from '@neurons/schema/query/ConditionAssetEntityChild.vue';
import { GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL } from '@store/getters';


export default {
  name: 'XConditionAssetEntity',
  components: {
    XSelectSymbol, XConditionAssetEntityChild,
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
      getModuleSchemaWithConnectionLabel: GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL,
    }),
    field: {
      get() {
        return this.condition.field;
      },
      set(field) {
        this.$emit('update', {
          field, fieldType: field,
        });
      },
    },
    children() {
      return this.condition.children;
    },
    schema() {
      return this.getModuleSchemaWithConnectionLabel(this.module).slice(1);
    },
    schemaByName() {
      return _keyBy(this.schema, (field) => field.name);
    },
    fieldTitle() {
      return this.field
        ? this.schemaByName[this.field].title
        : '';
    },
    childrenSchema() {
      return this.field
        ? this.schemaByName[this.field].fields
        : [];
    },
  },
  methods: {
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
.x-condition-asset-entity {

  .parent-field {
    display: flex;

    .x-select-symbol {
      width: 60px;
      border-radius: 2px 0 0 2px;
    }

    &__name {
      width: 180px;
      border: 1px solid #DEDEDE;
      border-radius: 0 2px 2px 0;
      text-overflow: ellipsis;
      white-space: nowrap;
      overflow: hidden;
      line-height: 30px;
      padding: 0 4px;
      margin-left: -1px;
    }
  }
}
</style>
