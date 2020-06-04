<template>
  <div class="x-condition-field-comparison x-condition__child">
    <XSelectTypedField
      :value="field"
      :filtered-adapters="condition.filteredAdapters"
      :options="schema"
      :read-only="readOnly"
      :auto-fill="false"
      @input="onChangeField"
    />
    <XConditionFunctionFieldComparison
      :schema="fieldSchema"
      :operator="condition.compOp"
      :argument="[condition.value, condition.subvalue]"
      :read-only="readOnly"
      @update="onUpdateConditionFunction"
    />
    <XSelectTypedField
      v-if="field"
      :value="secondField"
      :filtered-adapters="condition.filteredAdapters"
      :options="filteredOptions"
      :read-only="readOnly"
      :auto-fill="false"
      @input="(field, fieldType, filteredAdapters) => onChangeField(field, fieldType, filteredAdapters, true)"
    />
  </div>
</template>

<script>
import _isEmpty from 'lodash/isEmpty';
import { mapState, mapGetters } from 'vuex';
import XSelectTypedField from '../../inputs/SelectTypedField.vue';
import XConditionFunctionFieldComparison from './ConditionFunctionFieldComparison.vue';


import {
  GET_DATA_SCHEMA_BY_NAME,
  GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL,
} from '../../../../store/getters';

export default {
  name: 'XConditionFieldComparison',
  components: {
    XSelectTypedField, XConditionFunctionFieldComparison,
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
      secondValue: {
        field: undefined,
        fieldType: undefined,
        filteredAdapters: undefined,
      },
    };
  },
  computed: {
    ...mapState({
      savedViews(state) {
        return state[this.module].views.saved.content.data;
      },
    }),
    ...mapGetters({
      getModuleSchemaWithConnectionLabel: GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL, getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME,
    }),
    field() {
      return this.condition.field;
    },
    secondField() {
      return this.secondValue.field ? this.secondValue.field : this.condition.value;
    },
    filteredOptions() {
      // Filter second field options according to the first field type and format
      const tmpSchema = this.getModuleSchemaWithConnectionLabel(this.module, false, true).slice(1);
      const fieldType = this.getFieldSchema(this.field).type;
      const fieldFormat = this.getFieldSchema(this.field).format;
      if (fieldFormat !== undefined) {
        tmpSchema.forEach((adapter) => {
          adapter.fields = adapter.fields.filter((field) => field.type == fieldType && field.format == fieldFormat);
        });
      } else {
        tmpSchema.forEach((adapter) => {
          adapter.fields = adapter.fields.filter((field) => field.type == fieldType);
        });
      }
      return tmpSchema;
    },
    schema() {
      // The slice is in order to filter the Aggregated (axonius) adapter...
      const schema = this.getModuleSchemaWithConnectionLabel(this.module, false, true).slice(1);
      if (_isEmpty(schema)) {
        return [];
      }
      // Filter all the complex fields
      schema.forEach((adapter) => {
        let filteredFields = [];
        adapter.fields.forEach((field) => {
          if (field.type === 'array') {
            filteredFields.push(field.name);
          } else if (filteredFields.find((filtered_field) => field.name.includes(filtered_field))) {
            filteredFields.push(field.name);
          }
        });
        adapter.fields = adapter.fields.filter((field) => !filteredFields.find((filtered_field) => field.name == filtered_field));
      });
      return schema;
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
    onChangeField(field, fieldType, filteredAdapters, isSecondsField) {
      if (isSecondsField) {
        const value = field;
        if (this.fieldSchema.name !== undefined) {
          field = this.fieldSchema.name;
        }
        const update = {
          field,
          fieldType,
          filteredAdapters,
          value,
        };
        this.$emit('update', update);
        this.onChangeSecondField(value, fieldType, filteredAdapters);
        return;
      }
      const { value } = this.condition;
      const { subvalue } = this.condition;
      const update = {
        field,
        fieldType,
        filteredAdapters,
        subvalue,
        value,
      };
      if ((this.fieldSchema.format !== this.getFieldSchema(field).format) || (this.fieldSchema.type !== this.getFieldSchema(field).type)) {
        update.compOp = 'equals';
        update.value = '';
        this.onChangeSecondField('', fieldType, filteredAdapters);
      }
      this.$emit('update', update);
    },
    onChangeSecondField(field, fieldType, filteredAdapters) {
      const fieldData = this.getFieldSchema(field);
      this.secondValue.field = fieldData.name;
      this.secondValue.fieldType = fieldData.type;
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
