<template>
  <div class="x-condition-aggregated-data x-condition__child">
    <XSelectTypedField
      :value="field"
      :filtered-adapters="condition.filteredAdapters"
      :options="schema"
      :read-only="readOnly"
      :show-secondary-values="showSecondaryValues"
      @input="onChangeField"
    />
    <XConditionFunction
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
import XSelectTypedField from '../../inputs/SelectTypedField.vue';
import XConditionFunction from './ConditionFunction.vue';

import {
  GET_DATA_SCHEMA_BY_NAME,
  GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL,
} from '../../../../store/getters';
import { getUpdatedValueAfterFieldChange } from '../../../../logic/condition';

export default {
  name: 'XConditionAggregatedData',
  components: {
    XSelectTypedField, XConditionFunction,
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
  data() {
    return {
      disableAdaptersFilterQueriesList: [
        'internal_axon_id',
        'saved_query',
        'adapter_list_length',
        'adapters',
        'has_notes',
      ],
    };
  },
  computed: {
    ...mapState({
      savedViews(state) {
        return state[this.module].views.saved.content.data;
      },
    }),
    ...mapGetters({
      getModuleSchemaWithConnectionLabel: GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL,
      getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME,
    }),
    field() {
      return this.condition.field;
    },
    schema() {
      const schema = this.getModuleSchemaWithConnectionLabel(this.module, false, true);
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
          enum: this.savedViews.reduce((filtered, view) => {
            if (view && !view.private) {
              filtered.push({
                name: _get(view, 'view.query.filter', ''),
                title: view ? view.name : '',
              });
            }
            return filtered;
          }, []),
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
    showSecondaryValues() {
      return !this.disableAdaptersFilterQueriesList.includes(this.condition.field);
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
      if (field.endsWith('.id') && !this.condition.compOp) {
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
