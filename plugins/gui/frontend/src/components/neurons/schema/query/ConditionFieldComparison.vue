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
    <div
      v-if="field"
      class="expression-actions"
    >
      <XButton
        :disabled="!secondField"
        type="link"
        class="child-toggle-column"
        :title="isColumnInTable ? 'Remove Field from Columns' : 'Add Field to Columns'"
        @click="$emit('toggle-column', secondField)"
      >
        <XIcon
          family="action"
          :type="isColumnInTable ? 'removeColumn' : 'addColumn'"
        />
      </XButton>
    </div>
  </div>
</template>

<script>
import _isEmpty from 'lodash/isEmpty';
import { mapState, mapGetters } from 'vuex';
import XSelectTypedField from '@neurons/inputs/SelectTypedField.vue';
import XConditionFunctionFieldComparison from '@neurons/schema/query/ConditionFunctionFieldComparison.vue';
import {
  GET_DATA_SCHEMA_BY_NAME,
  GET_MODULE_SCHEMA,
} from '@store/getters';


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
    viewFields: {
      type: Array,
      default: () => ([]),
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
      getModuleSchema: GET_MODULE_SCHEMA, getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME,
    }),
    field() {
      return this.condition.field;
    },
    secondField() {
      return this.secondValue.field ? this.secondValue.field : this.condition.value;
    },
    filteredOptions() {
      // Filter second field options according to the first field type and format
      const tmpSchema = this.getModuleSchema(this.module, false, true).slice(1);
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
      const schema = this.getModuleSchema(this.module, false, true).slice(1);
      if (_isEmpty(schema)) {
        return [];
      }
      // Filter all the complex fields
      schema.forEach((adapter) => {
        const filteredFields = [];
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
    isColumnInTable() {
      return this.viewFields.includes(this.secondField);
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
.x-condition__child.x-condition-field-comparison {
  grid-template-columns: 240px auto;
  .child-toggle-column {
    margin-left: auto;
  }
}
</style>
