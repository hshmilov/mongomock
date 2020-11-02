/*
	Common functionality for primitive controls in 'edit' mode.

	Received props include:
	 - schema - parameters configuring the functionality of the control
	 - value - current value of the control (primitive object)

	Defined data includes:
	 - data - created from given value and emitted as an input event (implementing v-model)
	 - valid - validity state of current data. Common validity test is whether empty, if data is required by schema.

	Methods to be implemented by extending components:
	 - formatData - Changes to be made to the data user inputs so it complys to the given schema
	 - checkData - Check that data user inputs cannot comply to the given schema
	 - isEmpty - If the type requires a special method to determine whether it is empty

 */
import { SIZE_OPERATOR } from '@constants/filter';

export default {
  props: ['schema', 'value', 'readOnly', 'operator'],
  data() {
    return {
      data: null,
      valid: true,
      error: '',
    };
  },
  computed: {
    enumOptions() {
      if (!this.schema.enum || this.operator === SIZE_OPERATOR) return undefined;
      return this.schema.enum.map((item, index) => {
        if (item instanceof Object && 'name' in item && 'title' in item) {
          return item;
        }
        if (this.schema.type === 'integer' && isNaN(item)) {
          return { name: index + 1, title: item };
        }
        if (typeof item !== 'string' && item.name) {
          return item;
        }
        return { name: item, title: String(item) };
      });
    },
  },
  watch: {
    value(newValue, oldValue) {
      if (newValue !== oldValue) {
        this.data = newValue;
        this.validate(true);
      }
    },
  },
  methods: {
    emitValidity() {
      this.$emit('validate', { name: this.schema.name, valid: this.valid, error: this.error });
    },
    validate(silent) {
      // Data is invalid if checkData is negative or the field is required and empty
      this.valid = this.checkData() && (!this.schema.required || !this.isEmpty());
      this.error = '';
      if (!silent && !this.valid) {
        // Error is added if the data is invalid, unless silent is set to true.
        // added check if schema has custom error message
        this.error = this.getErrorMessage();
      }
      this.emitValidity(silent);
    },
    focusout() {
      this.validate(false);
    },
    input() {
      this.data = this.formatData();
      this.$emit('input', this.data);
      // Upon input, overall validity should be affected but no need to scare the user with an error yet.
      // Validate without publishing the error
      this.validate(true);
    },
    onKeyPress(event) {
      this.$emit('keydown', event);
    },
    formatData() {
      return this.data;
    },
    checkData() {
      return true;
    },
    getErrorMessage() {
      return this.schema.errorMsg || `'${this.schema.title}' has an illegal value`;
    },
    isEmpty() {
      return !this.data;
    },
  },
  created() {
    if (this.value !== undefined && this.value !== null) {
      this.data = this.value;
    }
  },
};
