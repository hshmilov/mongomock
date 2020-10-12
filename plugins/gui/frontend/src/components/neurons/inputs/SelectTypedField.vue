<template>
  <div class="x-select-typed-field">
    <XSelectSymbol
      v-model="filterTypeWithFilters"
      :read-only="readOnly"
      :options="options"
      :minimal="minimal"
      @input="updateAutoField"
      :show-secondary-values="showSecondaryValues"
    />
    <XSelect
      :id="id"
      :read-only="readOnly"
      :options="currentFields"
      :value="value"
      placeholder="field..."
      :searchable="true"
      class="field-select"
      @input="onChangedField"
    />
  </div>
</template>

<script>
import XSelectSymbol from './SelectSymbol.vue';
import XSelect from '../../axons/inputs/select/Select.vue';
import { getTypeFromField } from '../../../constants/utils';

export default {
  name: 'XSelectTypedField',
  components: { XSelectSymbol, XSelect },
  props: {
    options: {
      type: Array,
      required: true,
    },
    value: {
      type: String,
      default: '',
    },
    filteredAdapters: {
      type: Object,
      default: () => {},
    },
    id: {
      type: String,
      default: undefined,
    },
    minimal: {
      type: Boolean,
      default: true,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
    autoFill: {
      type: Boolean,
      default: true,
    },
    showSecondaryValues: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      fieldType: '',
      excludedFields: ['specific_data.data.correlation_reasons'],
    };
  },
  computed: {
    currentFields() {
      if (!this.options || !this.options.length) {
        return [];
      }
      if (!this.fieldType) {
        return this.options[0].fields;
      }
      // Filter '_preferred' fields because theyre not in the mongo but calculated dynamiclly
      const { fields } = this.options.find((item) => item.name === this.fieldType);
      return fields.filter((item) => !this.excludedFields.includes(item.name));
    },
    firstType() {
      if (!this.options || !this.options.length) return 'axonius';
      return this.options[0].name;
    },
    filterTypeWithFilters: {
      get() {
        return { value: this.fieldType, secondaryValues: this.filteredAdapters };
      },
      set(value) {
        this.updateAutoField(value);
      },
    },
  },
  watch: {
    value(newValue, oldValue) {
      if (newValue && newValue !== oldValue) {
        this.updateFieldType();
      } else if (!newValue && this.autoFill) {
        this.fieldType = this.firstType;
      }
    },
    currentFields(newCurrentFields) {
      if (!this.value) return;
      if (this.autoFill && !newCurrentFields.filter((field) => field.name === this.value).length) {
        this.$emit('input', '', this.fieldType, this.filteredAdapters);
      }
    },
    firstType(newFirstType) {
      this.fieldType = newFirstType;
    },
  },
  created() {
    this.fieldType = this.firstType;
    if (this.value) {
      this.updateFieldType();
      this.$emit('input', this.value, this.fieldType, this.filteredAdapters);
    }
  },
  methods: {
    updateFieldType() {
      this.fieldType = getTypeFromField(this.value);
    },
    updateAutoField(value) {
      let secondaryValues = null;
      if (typeof (value) === 'string') {
        this.fieldType = value;
      } else {
        this.fieldType = value.value;
        secondaryValues = value.secondaryValues;
      }

      if (this.fieldType === '' || this.fieldType === 'axonius') {
        if (secondaryValues) {
          this.$emit('input', this.value, this.fieldType, secondaryValues);
        }
        return;
      }
      if (this.value) {
        const fieldMatch = /\w+_data\.\w+(\.\w+)/.exec(this.value);
        if (fieldMatch && fieldMatch[1] !== '.id' && fieldMatch.length > 1) {
          const currentField = this.currentFields.find((field) => field.name.includes(fieldMatch[1]));
          if (currentField) {
            this.$emit('input', currentField.name, this.fieldType, secondaryValues);
            return;
          } if (!this.autoFill) {
            this.$emit('input', '', this.fieldType, secondaryValues);
            return;
          }
        }
      }
      if (this.autoFill && this.currentFields.find((field) => field.name.includes('.id'))) {
        this.$emit('input', `adapters_data.${this.fieldType}.id`, this.fieldType, secondaryValues);
      }
    },
    onChangedField(value) {
      this.$emit('input', value, this.fieldType, this.filteredAdapters);
    },
  },
};
</script>

<style lang="scss">
    .x-select-typed-field {
        display: flex;
        width: 100%;

        .x-select-symbol {
            border-bottom-right-radius: 0;
            border-top-right-radius: 0;
        }
        .field-select {
            flex: 1 0 auto;
            width: 180px;
            margin-left: -1px;
            border-bottom-left-radius: 0;
            border-top-left-radius: 0;
        }
    }
</style>
