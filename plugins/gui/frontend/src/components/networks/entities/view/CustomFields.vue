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
import XCustomFieldsRow from './CustomFieldsRow.vue';
import XButton from '../../../axons/inputs/Button.vue';

export default {
  name: 'XEntityCustomFields',
  components: { XCustomFieldsRow, XButton },
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
        return this.value.filter((field) => field.name !== 'specific_data.data.id');
      },
      set(value) {
        let valid = true;
        value.forEach((field) => {
          if (!field.value && field.value !== 0 && field.value !== false) {
            // Field value is empty
            valid = false;
          }
          if (!field.predefined && this.checkDuplicate(field.name)) {
            // New field's name already exists
            valid = false;
            this.error = 'Custom Field Name is already in use by another field';
          } else {
            this.error = '';
          }
        });
        this.$emit('input', value);
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
          name: field.name, title: field.title,
        }));

      const custom = this.fields.custom
        .filter(filterFields)
        .sort(sortFields)
        .map((field) => ({
          name: this.trimName(field.name), title: field.title,
        }));

      return { predefined, custom };
    },
    predefinedFieldsMap() {
      return this.fields.predefined.reduce((map, field) => ({ ...map, [field.name]: field }), {});
    },
    customFieldsMap() {
      return this.fields.custom.reduce((map, field) => ({ ...map, [this.trimName(field.name)]: field }), {});
    },
    customFieldTitles() {
      const createTitles = (field) => field.title.toLowerCase();
      return this.fieldOptions.custom.map(createTitles);
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
        predefined: true, new: true,
      }];
    },
    addCustomField() {
      this.fieldConfig = [...this.fieldConfig, {
        predefined: false, new: true,
      }];
    },
    updateField(index, fieldToUpdate) {
      this.fieldConfig = this.fieldConfig.map((currentField, i) => ((i === index) ? fieldToUpdate : currentField));
    },
    removeField(index) {
      this.fieldConfig = this.fieldConfig.filter((field, i) => i !== index);
    },
    checkDuplicate(fieldName) {
      if (!fieldName) {
        return false;
      }
      const fieldsByName = this.definedFieldNames.filter((currentName) => {
        if (this.customFieldsMap[currentName]) {
          // Given a field definition, compare with its title
          return fieldName === this.customFieldsMap[currentName].title;
        }
        // With no field definition, the name itself (given by user) will be the title
        return fieldName === currentName;
      });
      return (fieldsByName.length > 1 || this.customFieldTitles.includes(fieldName.toLowerCase()));
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
