<template>
  <div class="x-entity-custom-fields">
    <div
      ref="fields"
      class="custom-fields"
    >
      <template v-for="(field, i) in fieldConfig">
        <div
          :key="i"
          class="fields-item"
        >
          <template v-if="field.predefined">
            <x-select
              v-model="field.name"
              :options="currentFieldOptions(field.name)"
              placeholder="Field..."
              :searchable="true"
              :read-only="!field.new"
              :container="$refs.fields"
              :class="{'border-error': hasFieldError(field), 'item-name': true}"
              @input="onInputValue"
            />
            <component
              :is="fieldMap[field.name].type"
              v-if="field.name"
              v-model="field.value"
              :schema="fieldMap[field.name]"
              :class="{'border-error': hasFieldError(field), 'item-value': true}"
              @input="onInputValue"
            />
            <div v-else />
          </template>
          <template v-else>
            <div class="item-type">
              <x-select
                v-model="field.type"
                :options="typeOptions"
                placeholder="Type..."
                :searchable="true"
                :class="{'border-error': empty(field.type) , 'item-type': true}"
              />
              <input
                v-model="field.name"
                type="text"
                :class="{'border-error': duplicateFieldName(field.name) || hasFieldError(field), 'item-name': true}"
                @keypress="validateFieldName"
                @input="onInputValue"
              >
            </div>
            <component
              :is="field.type"
              v-if="field.type"
              v-model="field.value"
              :schema="{ type: field.type }"
              :class="{'border-error': hasFieldError(field), 'item-value': true}"
              @input="onInputValue"
            />
            <div v-else />
          </template>
          <x-button
            v-if="field.new"
            link
            @click="removeField(i)"
          >X</x-button>
          <div v-else />
        </div>
        <div
          v-if="hasFieldError(field) && getExternalError(field)"
          :key="`${i}_error`"
          class="fields-item"
        >
          <div />
          <div class="error">{{ getExternalError(field) }}</div>
        </div>
      </template>
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
  import xSelect from '../../../axons/inputs/Select.vue'
  import string from '../../../neurons/schema/types/string/StringEdit.vue'
  import number from '../../../neurons/schema/types/numerical/NumberEdit.vue'
  import integer from '../../../neurons/schema/types/numerical/IntegerEdit.vue'
  import bool from '../../../neurons/schema/types/boolean/BooleanEdit.vue'
  import xButton from '../../../axons/inputs/Button.vue'

  export default {
    name: 'XEntityCustomFields',
    components: { xSelect, string, number, integer, bool, xButton },
    props: {
      value: {
        type: Object,
        default: null
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
        type: [Object, String],
        default: null
      }
    },
    data () {
      return {
        fieldConfig: [],
        error: ''
      }
    },
    computed: {
      definedFields () {
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
      },
      typeOptions () {
        return [
          {
            name: 'string', title: 'String'
          }, {
            name: 'number', title: 'Float'
          }, {
            name: 'integer', title: 'Integer'
          }, {
            name: 'bool', title: 'Bool'
          }
        ]
      }
    },
    created () {
      this.fieldConfig = Object.keys(this.value).map(fieldName => {
        return {
          name: fieldName, value: this.value[fieldName], predefined: true
        }
      })
      this.error = ''
    },
    methods: {
      currentFieldOptions (fieldName) {
        return this.fieldOptions.filter(field =>
          !this.definedFields.includes(field.name) || field.name === fieldName)
      },
      trimName (name) {
        return name.replace(/(adapters_data|specific_data)\.(gui|data)\./g, '')
      },
      validType (field) {
        return ['string', 'bool', 'number', 'integer'].includes(field.type) &&
          (!field.format || !field.format.match(/(date|time)/))
      },
      addPredefinedField () {
        this.fieldConfig.push({
          predefined: true, new: true
        })
        this.$emit('validate', false)
      },
      addCustomField () {
        this.fieldConfig.push({
          predefined: false, new: true
        })
        this.$emit('validate', false)
      },
      onInputValue () {
        let valid = true
        this.$emit('input', this.fieldConfig.reduce((map, field) => {
          if (this.empty(field.name) || this.empty(field.value)
            || (!field.predefined && this.duplicateFieldName(field.name))) valid = false

          if (field.value !== undefined && field.value !== null) {
            map[field.name] = field.value
          }
          return map
        }, {}))
        if (valid) this.error = ''
        this.$emit('validate', valid)
      },
      removeField (index) {
        this.fieldConfig.splice(index, 1)
        this.onInputValue()
      },
      empty (value) {
        let isEmpty = (value === undefined || value === null || value === '')
        if (isEmpty) {
          this.$emit('validate', false)
        }
        return isEmpty
      },
      validateFieldName (event) {
        event = (event) ? event : window.event
        let charCode = (event.which) ? event.which : event.keyCode
        if ((charCode >= 48 && charCode <= 57) || (charCode >= 65 && charCode <= 90)
          || (charCode >= 97 && charCode <= 122) || charCode === 32 || charCode === 95 || charCode === 8) {
          return true
        }
        event.preventDefault()
      },
      duplicateFieldName (fieldName) {
        if (!fieldName) {
          return false
        }
        if (this.definedFields.filter(field => {
          if (this.fieldMap[field]) {
            return this.fieldMap[field].title === fieldName
          }
          return field === fieldName
        }).length > 1 || this.fieldTitles.includes(fieldName.toLowerCase())) {
          this.error = 'Custom Field Name is already in use by another field'
          return true
        }
        this.error = ''
        return false
      },
      hasFieldError (field) {
        return !!(this.empty(field.value) || (this.externalError && this.externalError[field.name]))
      },
      getExternalError (field) {
        if (!this.externalError) {
          return ''
        }
        if (!field) {
          return Object.values(this.externalError).join(', ')
        } else {
          return this.externalError[field.name]
        }
      }
    }
  }
</script>

<style lang="scss">
    .x-entity-custom-fields {
        .custom-fields {
            height: 60vh;
            overflow-y: auto;

            .fields-item {
                display: grid;
                grid-template-columns: 1fr 1fr 20px;
                grid-gap: 12px;
                margin-bottom: 12px;
                line-height: 30px;

                .item-type {
                    display: flex;

                    input {
                        flex: 1 0 auto;
                    }
                }

                .x-button.link {
                    line-height: 30px;
                    padding: 0;
                }

                .border-error {
                    border: 1px solid $indicator-error;
                }

                .error {
                    color: $indicator-error;
                }
            }
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
