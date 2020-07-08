<template>
  <div class="x-custom-fields-row">
    <div class="fields-item">
      <template v-if="field.predefined">
        <XSelect
          v-model="fieldName"
          :options="fieldOptions"
          placeholder="Field..."
          :searchable="true"
          :read-only="!field.isNew"
          :container="$refs.fields"
          :class="{'border-error': empty(fieldName) || error, 'item-name': true}"
        />
        <Component
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
          <XSelect
            v-model="fieldType"
            :options="typeOptions"
            placeholder="Type..."
            :searchable="true"
            :class="{'border-error': empty(fieldType), 'item-type': true}"
          />
          <input
            v-model="fieldTitle"
            type="text"
            :class="{'border-error': empty(fieldName) || error, 'item-name': true}"
            @keypress="validateFieldName"
          >
        </div>
        <Component
          :is="fieldType"
          v-if="fieldType"
          v-model="fieldValue"
          :schema="{ type: fieldType }"
          :class="{'border-error': empty(fieldValue) || error, 'item-value': true}"
        />
        <div v-else />
      </template>
      <XButton
        v-if="field.isNew"
        type="link"
        @click="$emit('remove')"
      >X</XButton>
      <div v-else />
    </div>
    <div
      v-if="error"
      class="fields-item"
    >
      <div />
      <div class="field-error">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script>
import XSelect from '../../../axons/inputs/select/Select.vue';
import string from '../../../neurons/schema/types/string/StringEdit.vue';
import number from '../../../neurons/schema/types/numerical/NumberEdit.vue';
import integer from '../../../neurons/schema/types/numerical/IntegerEdit.vue';
import bool from '../../../neurons/schema/types/boolean/BooleanEdit.vue';
import XButton from '../../../axons/inputs/Button.vue';

import { validateFieldName } from '../../../../constants/validations';

export default {
  name: 'XCustomFieldsRow',
  components: {
    XSelect, string, number, integer, bool, XButton,
  },
  model: {
    prop: 'field',
    event: 'input',
  },
  props: {
    field: {
      type: Object,
      default: () => ({}),
    },
    schema: {
      type: Object,
      default: () => ({}),
    },
    fieldOptions: {
      type: Array,
      default: () => [],
    },
    error: {
      type: String,
      default: '',
    },
  },
  computed: {
    fieldName: {
      get() {
        return this.field.name;
      },
      set(name) {
        this.$emit('input', { ...this.field, name });
      },
    },
    fieldTitle: {
      get() {
        return this.field.title || this.field.name;
      },
      set(name) {
        this.$emit('input', { ...this.field, name });
      },
    },
    fieldType: {
      get() {
        return this.field.type || this.schema.type;
      },
      set(type) {
        this.$emit('input', {
          ...this.field,
          value: type === 'bool' ? false : null,
          type,
        });
      },
    },
    fieldValue: {
      get() {
        return this.field.value;
      },
      set(value) {
        this.$emit('input', { ...this.field, value });
      },
    },
    typeOptions() {
      return [
        {
          name: 'string', title: 'String',
        }, {
          name: 'number', title: 'Float',
        }, {
          name: 'integer', title: 'Integer',
        }, {
          name: 'bool', title: 'Bool',
        },
      ];
    },
  },
  methods: {
    empty(value) {
      return !(value || value === 0 || value === false);
    },
    validateFieldName,
  },
};
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

                .item-name {
                  width: auto;
                }
            }

            .item-value {
              &.string-input-container {
                height: 32px;

                input {
                  height: 100%;
                }
              }
            }

            .x-button.ant-btn-link {
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
