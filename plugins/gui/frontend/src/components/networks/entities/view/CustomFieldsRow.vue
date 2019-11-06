<template>
  <div class="x-custom-fields-row">
    <div class="fields-item">
      <template v-if="field.predefined">
        <x-select
          v-model="fieldName"
          :options="fieldOptions"
          placeholder="Field..."
          :searchable="true"
          :read-only="!field.new"
          :container="$refs.fields"
          :class="{'border-error': empty(fieldName) || error, 'item-name': true}"
        />
        <component
          :is="schema.type"
          v-if="fieldName"
          v-model="fieldValue"
          :schema="schema"
          :class="{'border-error': empty(fieldValue) || error, 'item-value': true}"
        />
        <div v-else />
      </template>
      <template v-else>
        <div class="item-def">
          <x-select
            v-model="fieldType"
            :options="typeOptions"
            placeholder="Type..."
            :searchable="true"
            :class="{'border-error': empty(fieldType), 'item-type': true}"
          />
          <input
            v-model="fieldName"
            type="text"
            :class="{'border-error': empty(fieldName) || error, 'item-name': true}"
            @keypress="validateFieldName"
          >
        </div>
        <component
          :is="fieldType"
          v-if="fieldType"
          v-model="fieldValue"
          :schema="{ type: fieldType }"
          :class="{'border-error': empty(fieldValue) || error, 'item-value': true}"
        />
        <div v-else />
      </template>
      <x-button
        v-if="field.new"
        link
        @click="$emit('remove')"
      >X</x-button>
      <div v-else />
    </div>
    <div
      v-if="error"
      class="fields-item"
    >
      <div />
      <div class="field-error">{{ error }}</div>
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

  import { validateFieldName } from '../../../../constants/validations'

  export default {
    name: 'XCustomFieldsRow',
    components: {
      xSelect, string, number, integer, bool, xButton
    },
    model: {
      prop: 'field',
      event: 'input'
    },
    props: {
      field: {
        type: Object,
        default: () => {
          return {}
        }
      },
      schema: {
        type: Object,
        default: () => {
          return {}
        }
      },
      fieldOptions: {
        type: Array,
        default: () => []
      },
      error: {
        type: String,
        default: ''
      }
    },
    computed: {
      fieldName: {
        get () {
          return this.field.name
        },
        set (name) {
          this.$emit('input', { ...this.field, name })
        }
      },
      fieldType: {
        get () {
          return this.field.type
        },
        set (type) {
          this.$emit('input', {
            ...this.field,
            value: type === 'bool'? false : null,
            type
          })
        }
      },
      fieldValue: {
        get () {
          return this.field.value
        },
        set (value) {
          this.$emit('input', { ...this.field, value })
        }
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
    methods: {
      empty (value) {
        return !(value || value === 0 || value === false)
      },
      validateFieldName
    }
  }
</script>

<style lang="scss">
    .x-custom-fields-row {
        .fields-item {
            display: grid;
            grid-template-columns: 1fr 1fr 20px;
            grid-gap: 12px;
            margin-bottom: 12px;
            line-height: 30px;

            .item-def {
                display: flex;

                .item-type {
                  width: 80px;
                }

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

            .field-error {
                color: $indicator-error;
            }
        }
    }
</style>