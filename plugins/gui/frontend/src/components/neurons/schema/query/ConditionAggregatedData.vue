<template>
  <div class="x-condition-aggregated-data x-condition__child">
    <x-select-typed-field
      :value="field"
      :filtered-adapters="condition.filteredAdapters"
      :options="schema"
      :read-only="readOnly"
      @input="onChangeField"
    />
    <x-condition-function
      :schema="fieldSchema"
      :operator="condition.compOp"
      :argument="condition.value"
      :read-only="readOnly"
      @update="onUpdateConditionFunction"
    />
  </div>
</template>

<script>
import _isEmpty from 'lodash/isEmpty';
import _get from 'lodash/get';
import { mapState, mapGetters } from 'vuex';
import xSelectTypedField from '../../inputs/SelectTypedField.vue';
import xConditionFunction from './ConditionFunction.vue';


import { GET_MODULE_SCHEMA, GET_DATA_SCHEMA_BY_NAME } from '../../../../store/getters';
import { getUpdatedValueAfterFieldChange } from '../../../../logic/condition';

export default {
  name: 'XConditionAggregatedData',
  components: {
    xSelectTypedField, xConditionFunction,
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
    ...mapState({
      savedViews(state) {
        return state[this.module].views.saved.content.data;
      },
    }),
    ...mapGetters({
      getModuleSchema: GET_MODULE_SCHEMA, getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME,
    }),
    field() {
      return this.condition.field;
    },
    schema() {
      const schema = this.getModuleSchema(this.module, false, true);
      if (_isEmpty(schema)) {
        return [];
      }
      /*
      Compose a schema by which to offer fields and values
      for building query expressions in the wizard
      */
      const firstSchemaWithSavedQuery = {
        ...schema[0],
        fields: [{
          name: 'saved_query',
          title: 'Saved Query',
          type: 'string',
          format: 'predefined',
          enum: this.savedViews.filter((v) => v).map((view) => ({
            name: _get(view, 'view.query.filter', ''), title: view ? view.name : '',
          })),
        }, ...schema[0].fields],
      };
      return [firstSchemaWithSavedQuery, ...schema.slice(1)];
    },
    schemaByName() {
      return {
        ...this.getDataSchemaByName(this.module),
        saved_query: this.schema[0].fields[0],
      };
    },
    fieldSchema() {
      return this.getFieldSchema(this.field);
    },
  },
  methods: {
    onChangeField(field, fieldType, filteredAdapters) {
      const value = getUpdatedValueAfterFieldChange(this.getFieldSchema(field),
        this.fieldSchema,
        this.condition.compOp,
        this.condition.value);
      const update = {
        field,
        fieldType,
        filteredAdapters,
        value,
      };
      if (field.endsWith('.id')) {
        update.compOp = 'exists';
      }
      this.$emit('update', update);
    },
    onUpdateConditionFunction(conditionFunction) {
      this.$emit('update', conditionFunction);
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

</style>
