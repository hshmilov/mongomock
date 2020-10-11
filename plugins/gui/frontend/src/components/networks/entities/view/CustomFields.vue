<template>
  <div class="x-entity-custom-fields">
    <div
      ref="fields"
      class="custom-fields"
    >
      <XCustomFieldsRow
        v-for="(field, i) in fieldConfig"
        :key="i"
        :field="field"
        :schema="getFieldSchema(field.name, field.predefined)"
        :field-options="currentFieldOptions(field.name, field.predefined)"
        :external-error="externalError[field.name]"
        @input="(val) => updateField(i, val)"
        @remove="() => removeField(i)"
      />
    </div>
    <div class="footer">
      <XButton
        type="link"
        @click="addPredefinedField"
      >Add Predefined field</XButton>
      <XButton
        type="link"
        @click="addCustomField"
      >Add New field</XButton>
      <div
        v-if="error"
        class="error-text"
      >{{ error }}</div>
    </div>
  </div>
</template>

<script>
import _filter from 'lodash/filter';
import _find from 'lodash/find';
import _orderBy from 'lodash/orderBy';
import _get from 'lodash/get';
import _isEmpty from 'lodash/isEmpty';
import XCustomFieldsRow from './CustomFieldsRow.vue';

export default {
  name: 'XEntityCustomFields',
  components: { XCustomFieldsRow },
  props: {
    value: {
      type: Array,
      default: () => [],
    },
    module: {
      type: String,
      required: true,
    },
    fields: {
      type: Object,
      required: true,
    },
    externalError: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      error: '',
    };
  },
  computed: {
    fieldConfig: {
      get() {
        const valuesToDisplay = this.value.filter((field) => field.name !== 'specific_data.data.id');
        const newValues = valuesToDisplay.filter((field) => field.isNew);
        const existingValues = valuesToDisplay.filter((field) => !field.isNew).map((field) => ({
          ...field,
          title: this.customFieldsMap[this.trimName(field.name)].title,
        }));
        return [..._orderBy(existingValues, ['predefined', 'title'], ['desc', 'asc']), ...newValues];
      },
      set(value) {
        let valid = true;
        this.error = '';

        const fieldsWithType = value.map((field) => ({
          ...field,
          type: field.name
            ? _get(this.customFieldsMap[this.trimName(field.name)], 'type', null) || field.type
            : field.type,
        }));

        for (let i = 0; i < fieldsWithType.length; i++) {
          const field = fieldsWithType[i];

          if (!field.name) {
            valid = false;
            break;
          }

          if (!field.predefined) {
            const validationResult = this.checkExistingTypeCompatibility(field.name, field.type, field.isNew);
            if (validationResult.duplicated) {
              // New field's name already exists
              valid = false;
              this.error = validationResult.error;
              break;
            }
          }

          if (!field.value && field.value !== 0 && field.value !== false) {
            // Field value is empty
            valid = false;
            break;
          }
        }

        const duplicationResult = this.areNewFieldsUnique(fieldsWithType);
        if (duplicationResult.duplicated) {
          valid = false;
          this.error = duplicationResult.error;
        }
        this.$emit('input', fieldsWithType);
        this.$emit('validate', valid);
      },
    },
    definedFieldNames() {
      return this.fieldConfig.map((field) => field.name);
    },
    fieldOptions() {
      const filterFields = (field) => !field.name.match(/\.id$/) && this.validType(field);
      const sortFields = (first, second) => {
        if (first.dynamic) return -1;
        if (second.dynamic) return 1;
        return first.name > second.name;
      };

      const predefined = this.fields.predefined
        .filter(filterFields)
        .sort(sortFields)
        .map((field) => ({
          name: field.name, title: field.title, type: field.type,
        }));

      const custom = this.fields.custom
        .filter(filterFields)
        .sort(sortFields)
        .map((field) => ({
          name: this.trimName(field.name), title: field.title, type: field.type,
        }));

      return { predefined, custom };
    },
    guiCustomFields() {
      // Gui custom fields are undefined in case no fields where added yet.
      return _isEmpty(this.fieldOptions.custom) ? this.fieldOptions.predefined : this.fieldOptions.custom;
    },
    predefinedFieldsMap() {
      return this.fieldOptions.predefined.reduce((map, field) => ({ ...map, [field.name]: field }), {});
    },
    customFieldsMap() {
      return this.guiCustomFields.reduce((map, field) => ({ ...map, [this.trimName(field.name)]: field }), {});
    },
    fieldTitlesToNameMap() {
      return this.guiCustomFields.reduce((result, field) => ({
        ...result, [field.title.toLowerCase()]: field.name,
      }), {});
    },
  },
  methods: {
    getFieldSchema(fieldName, predefined) {
      return predefined ? this.predefinedFieldsMap[fieldName] : this.customFieldsMap[fieldName];
    },
    currentFieldOptions(fieldName, predefined) {
      const fields = predefined ? this.fieldOptions.predefined : this.fieldOptions.custom;
      return fields.filter((field) => !this.definedFieldNames.includes(field.name) || field.name === fieldName);
    },
    trimName(name) {
      return name.replace(/(adapters_data|specific_data)\.(gui|data)\./g, '');
    },
    validType(field) {
      return ['string', 'number', 'integer', 'bool']
        .includes(field.type) && (!field.format || !field.format.match(/(date|time)/));
    },
    addPredefinedField() {
      this.fieldConfig = [...this.fieldConfig, {
        predefined: true, isNew: true,
      }];
    },
    addCustomField() {
      this.fieldConfig = [...this.fieldConfig, {
        predefined: false, isNew: true,
      }];
    },
    updateField(index, fieldToUpdate) {
      this.fieldConfig = this.fieldConfig.map((currentField, i) => ((i === index) ? fieldToUpdate : currentField));
    },
    removeField(index) {
      this.fieldConfig = this.fieldConfig.filter((field, i) => i !== index);
    },
    convertToCustomField(field, newField) {
      if (!field) return '';
      return newField ? `custom_${field.toLowerCase().replace(/ /g, '_')}` : field;
    },
    checkExistingTypeCompatibility(fieldName, fieldType, newField) {
      const error = null;
      if (!fieldName) {
        return { duplicated: false, error };
      }

      const customField = this.convertToCustomField(fieldName, newField);
      const existingField = this.customFieldsMap[customField];
      if (existingField) {
        // Given a field definition, compare with its title
        const duplicated = fieldName === existingField.title
                && fieldType !== existingField.type;
        if (duplicated) {
          // Field already exists with different type.
          return {
            duplicated: true,
            error: `Error: ${fieldName} already exists as ${existingField.type}`,
          };
        }
      } else if (this.fieldTitlesToNameMap[fieldName.toLowerCase()]) {
        const predefinedFieldName = this.fieldTitlesToNameMap[fieldName.toLowerCase()];
        const existingPredefinedField = this.customFieldsMap[predefinedFieldName];
        const errorMessage = existingPredefinedField
          ? `Error: predefined field - ${fieldName} already exists as ${existingPredefinedField.type}`
          : `Error: predefined field - ${fieldName} already exists`;
        return {
          duplicated: true,
          error: errorMessage,
        };
      }
      return { duplicated: false, error };
    },
    areNewFieldsUnique(newFields) {
      let duplicated = false;
      let error = null;
      const fieldsNames = newFields.map((field) => ({
        name: this.convertToCustomField(field.name, field.isNew),
        type: field.type,
        title: field.title || field.name,
      }));
      const res = _filter(fieldsNames, (val, i, iteratee) => _find(iteratee, { name: val.name }, i + 1));
      if (res.length) {
        duplicated = true;
        error = `Error: ${res[0].title} already exists as ${res[0].type}`;
      }
      return {
        duplicated,
        error,
      };
    },
  },
};
</script>

<style lang="scss">
    .x-entity-custom-fields {
        .custom-fields {
            height: 55vh;
            overflow-y: auto;
        }

        .footer {
            display: flex;

            .error-text {
                margin-left: 24px;
                flex: 1 0 auto;
                line-height: 28px;
                text-align: right;
            }
        }
    }
</style>
