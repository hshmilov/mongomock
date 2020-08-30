<template>
  <div class="x-action-config">
    <div
      v-if="!disableName"
      class="name"
    >
      <label
        for="action-name"
        class="name__label"
      >Action name:</label>
      <input
        id="action-name"
        ref="name"
        v-model="name"
        type="text"
        @focusout.stop="$emit('action-name-focused-out')"
      >
    </div>
    <div class="config">
      <template v-if="actionSchema && actionSchema.type">
        <h4 class="config__title">
          Configuration
        </h4>
        <XForm
          ref="form"
          v-model="config"
          :schema="actionSchema"
          api-upload="enforcements/actions"
          :read-only="readOnly"
          silent
          @validate="validateForm"
        />
      </template>
    </div>
  </div>
</template>

<script>
import XForm from '../../neurons/schema/Form.vue';
import actionsMixin from '../../../mixins/actions';

export default {
  name: 'XActionConfig',
  components: { XForm },
  mixins: [actionsMixin],
  props: {
    value: {
      type: Object,
      default: () => ({}),
    },
    allowedActionNames: {
      type: Array,
      default: () => [],
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      nameValid: false,
      formValid: false,
    };
  },
  computed: {
    disableConfirm() {
      return (!this.formValid || !this.nameValid);
    },
    disableName() {
      return this.value && this.value.uuid;
    },
    name: {
      get() {
        if (!this.value) return '';
        return this.value.name;
      },
      set(name) {
        this.$emit('input', {
          ...this.value,
          name,
          action: {
            ...this.value.action, config: this.config,
          },
        });
      },
    },
    config: {
      get() {
        if (!this.value || !this.value.action.config) return this.actionConfig.default || {};
        return this.value.action.config;
      },
      set(config) {
        this.$emit('input', {
          ...this.value,
          name: this.name,
          action: {
            ...this.value.action, config,
          },
        });
      },
    },
    actionName() {
      if (!this.value || !this.value.action) return '';

      return this.value.action.action_name;
    },
    actionConfig() {
      if (!this.actionsDef || !this.actionName) return {};

      return this.actionsDef[this.actionName];
    },
    actionSchema() {
      if (!this.actionConfig) return {};

      return this.actionConfig.schema;
    },
    nameError() {
      if (this.disableName) return '';
      if (this.name === '') {
        return 'Action name is a required field';
      }
      if (this.actionNameExists(this.name) && !this.allowedActionNames.includes(this.name)) {
        return 'Name already taken by another saved Action';
      }
      return '';
    },
    formError() {
      if (this.formValid || !this.$refs.form) return '';
      return this.$refs.form.validity.error;
    },
  },
  watch: {
    nameError(newVal) {
      this.nameValid = !newVal;
      this.$emit('action-name-error', newVal);
    },
    disableConfirm(isError) {
      this.$emit('action-validity-changed', !isError);
    },
  },
  mounted() {
    if (!this.disableName) {
      this.$refs.name.focus();
    }
    if (this.nameError) {
      this.$emit('action-name-error', this.nameError);
    }
    this.nameValid = !this.nameError;
    if (!this.$refs.form) {
      this.formValid = true;
    }
  },
  methods: {
    validateForm(valid) {
      this.formValid = valid;
      this.$emit('action-form-error', this.formError);
    },
  },
};
</script>

<style lang="scss">
  .x-action-config {
    height: 100%;

    .name {
      display: flex;
      align-items: center;
      margin-bottom: 24px;

      &__label {
        flex: 1 0 auto;
      }

      #action-name {
        margin-left: 12px;

        &.disabled {
          opacity: 0.6;
        }
      }
    }

    .config {
      @include y-scrollbar;
      overflow: auto;
      height: 100%;

      .config__title {
        margin-top: 0;
        margin-bottom: 12px;
      }

      .x-form > .x-array-edit > div > div > .list {
        grid-template-columns: 1fr;
        grid-gap: 24px 0;
        display: grid;

        .item_field_on {
          .x-select {
            width: 200px;
          }
        }
      }
    }
  }
</style>
