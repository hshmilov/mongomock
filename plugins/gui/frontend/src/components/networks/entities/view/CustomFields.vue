<template>
  <div class="x-entity-custom-fields">
    <div
      ref="fields"
      class="custom-fields"
    >
      <x-custom-fields-row
        v-for="(field, i) in fieldConfig"
        :key="i"
        :field="field"
        :schema="fieldMap[field.name]"
        :field-options="currentFieldOptions(field.name)"
        :external-error="externalError[field.name]"
        @input="(val) => updateField(i, val)"
        @remove="() => removeField(i)"
      />
    </div>
    <div class="footer">
      <x-button
        link
        @click="addPredefinedField"
      >+ Predefined field</x-button>
      <x-button
        link
        @click="addCustomField"
      >+ New field</x-button>
      <div
        v-if="error"
        class="error-text"
      >{{ error }}</div>
    </div>
  </div>
</template>

<script>
  import xCustomFieldsRow from './CustomFieldsRow.vue'
  import xButton from '../../../axons/inputs/Button.vue'

  export default {
    name: 'XEntityCustomFields',
    components: { xCustomFieldsRow, xButton },
    props: {
      value: {
        type: Array,
        default: () => []
      },
      module: {
        type: String,
        required: true
      },
      fields: {
        type: Array,
        required: true
      },
      externalError: {
        type: Object,
        default: () => {
          return {}
        }
      }
    },
    data () {
      return {
        error: ''
      }
    },
    computed: {
      fieldConfig: {
        get() {
          return this.value.filter(field => field.name !== 'id')
        },
        set (value) {
          let valid = true
          value.forEach((field) => {
            if (!field.value && field.value !== 0 && field.value !== false) {
              // Field value is empty
              valid = false
            }
            if (!field.predefined && this.checkDuplicate(field.name)) {
              // New field's name already exists
              valid = false
              this.error = 'Custom Field Name is already in use by another field'
            } else {
              this.error = ''
            }
            if (this.fieldMap[field.name]) {
              field.title = this.fieldMap[field.name].title
            }
          })
          this.$emit('input', value)
          this.$emit('validate', valid)
        }
      },
      definedFieldNames () {
        return this.fieldConfig.map(field => field.name)
      },
      fieldOptions () {
        return this.fields
          .filter(field => !field.name.match(/\.id$/) && this.validType(field))
          .sort((first, second) => {
            if (first.dynamic) return -1
            if (second.dynamic) return 1
            return first.name > second.name
          })
          .map(field => {
            return {
              name: this.trimName(field.name), title: field.title
            }
          })
      },
      fieldMap () {
        return this.fields.reduce((map, field) => {
          map[this.trimName(field.name)] = field
          return map
        }, {})
      },
      fieldTitles () {
        return this.fieldOptions.map(field => field.title.toLowerCase())
      }
    },
    methods: {
      currentFieldOptions (fieldName) {
        return this.fieldOptions.filter(field =>
          !this.definedFieldNames.includes(field.name) || field.name === fieldName)
      },
      trimName (name) {
        return name.replace(/(adapters_data|specific_data)\.(gui|data)\./g, '')
      },
      validType (field) {
        return ['string', 'number', 'integer', 'bool']
                .includes(field.type) && (!field.format || !field.format.match(/(date|time)/))
      },
      addPredefinedField () {
        this.fieldConfig = [ ...this.fieldConfig, {
          predefined: true, new: true
        }]
      },
      addCustomField () {
        this.fieldConfig = [ ...this.fieldConfig, {
          predefined: false, new: true
        }]
      },
      updateField(index, fieldToUpdate) {
        this.fieldConfig = this.fieldConfig.map((currentField, i) => {
          return (i === index) ? fieldToUpdate : currentField
        })
      },
      removeField (index) {
        this.fieldConfig = this.fieldConfig.filter((field, i) => i !== index)
      },
      checkDuplicate (fieldName) {
        if (!fieldName) {
          return false
        }
        const fieldsByName = this.definedFieldNames.filter(currentName => {
          if (this.fieldMap[currentName]) {
            // Given a field definition, compare with its title
            return fieldName === this.fieldMap[currentName].title
          }
          // With no field definition, the name itself (given by user) will be the title
          return fieldName === currentName
        })
        return (fieldsByName.length > 1 || this.fieldTitles.includes(fieldName.toLowerCase()))
      }
    }
  }
</script>

<style lang="scss">
    .x-entity-custom-fields {
        .custom-fields {
            height: 60vh;
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
