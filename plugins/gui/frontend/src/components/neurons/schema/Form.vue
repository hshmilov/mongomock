<template>
  <form
    class="x-form"
    @keyup.enter.stop="submitIfValid"
    @submit.prevent
  >
    <XArrayEdit
      v-model="data"
      :schema="schema"
      :api-upload="apiUpload"
      :read-only="readOnly"
      :use-vault="passwordsVaultEnabled"
      :list-collapsible="listCollapsible"
      @validate="onValidate"
      @remove-validate="onRemoveValidate"
    />
    <div
      v-if="!silent"
      class="form-error"
    >
      <template v-if="error">
        {{ error }}
      </template>
      <template v-else-if="validity.error">
        {{ validity.error }}
      </template>
      <template v-else>
      &nbsp;
      </template>
    </div>
  </form>
</template>

<script>
import _differenceBy from 'lodash/differenceBy';
import XArrayEdit from './types/array/ArrayEdit.vue';

/*
  Dynamically built form, according to given schema.
  Hitting the 'Enter' key from any field in the form, sends 'submit' event.
  Form elements are composed by an editable array. Therefore,
  schema is expected to be of type array.
  'input' event is captured and bubbled, with current data, to implement v-model.
  'validate' event is emitted with the value true if no invalid
  field was found and false otherwise.
*/
export default {
  name: 'XForm',
  components: { XArrayEdit },
  props: {
    value: {
      type: Object,
      default: null,
    },
    schema: {
      type: Object,
      default: () => {},
    },
    error: {
      type: String,
      default: '',
    },
    apiUpload: {
      type: String,
      default: null,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
    silent: {
      type: Boolean,
      default: false,
    },
    passwordsVaultEnabled: {
      type: Boolean,
      default: false,
    },
    listCollapsible: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      validity: {
        fields: [], error: '',
      },
    };
  },
  computed: {
    data: {
      get() {
        return this.value;
      },
      set(value) {
        this.$emit('input', value);
      },
    },
    isFormValid() {
      return this.validity.fields.every((field) => field.valid);
    },
  },
  created() {
    if (!Object.keys(this.data).length) {
      this.schema.items.forEach((item) => {
        this.data[item.name] = undefined;
      });
    }
  },
  methods: {
    submitIfValid() {
      if (this.isFormValid) {
        this.$emit('submit');
      }
    },
    onValidate(field) {
      /*
        field: {
            name: <string>, valid: <boolean>, error: <string>
        }
        The field is added to the validity fields list, if it is invalid. Otherwise, removed.
        The field's error, if exists, is set as the current error. Otherwise,
        next found error is set.
        A field can be invalid but not have an error in cases where the user should not be able
        to continue but also did not yet make a mistake.
        */
      this.validity.fields = this.validity.fields.filter((x) => x.name !== field.name);
      if (!field.valid) {
        this.validity.fields.push(field);
      }
      if (field.error) {
        this.validity.error = field.error;
      } else {
        const nextInvalidField = this.validity.fields.find((x) => x.error);
        this.validity.error = nextInvalidField ? nextInvalidField.error : '';
      }
      this.$emit('validate', this.validity.fields.length === 0);
    },
    onRemoveValidate(arrFieldNames) {
      /*
        arrFieldNames: Array of field names.
        Each field is an object containing the name of the field.
        This method is used to remove a given array of fields from validation.
        The field is removed from the validity fields list along with its error message (if existed)
        */
      this.validity.fields = _differenceBy(this.validity.fields, arrFieldNames, 'name');
      const nextInvalidField = this.validity.fields.find((x) => x.error);
      this.validity.error = nextInvalidField ? nextInvalidField.error : '';
      this.$emit('validate', this.validity.fields.length === 0);
    },
  },
};
</script>

<style lang="scss">
  .x-form {
    font-size: 14px;

    > .x-array-edit {
      > div > div > .list {
        display: grid;
        grid-template-columns: 1fr 1fr;
        grid-gap: 12px 24px;
      }
      input, select, textarea {

        &.error-border {
          border-color: $indicator-error;
        }
      }

      .error-border:not(.md-field) {
        border: 1px solid $indicator-error;
      }
    }

    .form-error {
      color: $indicator-error;
      margin-top: 12px;
    }
  }
</style>
