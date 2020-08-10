<template>
  <div class="x-action-config">
    <div class="name">
      <label
        for="action-name"
        class="name__label"
      >Action name:</label>
      <input
        id="action-name"
        ref="name"
        v-model="name"
        type="text"
        :disabled="disableName"
        :class="{disabled: disableName}"
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
    <div
      v-if="!hideSaveButton"
      class="actions"
    >
      <div class="error-text">
        {{ nameError || formError }}
      </div>
      <XButton
        v-if="!readOnly"
        type="primary"
        :disabled="disableConfirm"
        @click="confirmAction"
      >Save</XButton>
    </div>
  </div>
</template>

<script>
import XButton from '../../axons/inputs/Button.vue';
import XForm from '../../neurons/schema/Form.vue';

import actionsMixin from '../../../mixins/actions';

export default {
  name: 'XActionConfig',
  components: {
    XButton, XForm,
  },
  mixins: [actionsMixin],
  props: {
    value: {
      type: Object,
      default: () => ({}),
    },
    exclude: {
      type: Array,
      default: () => [],
    },
    include: {
      type: Array,
      default: () => [],
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
    hideSaveButton: {
      type: Boolean,
      default: false,
    },
    focusOnActionName: {
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
      } if ((this.actionNameExists(this.name) && !this.include.includes(this.name))
                || this.exclude.includes(this.name)) {
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
    if (this.focusOnActionName) {
      this.$refs.name.focus();
    }
    if (this.hideSaveButton && this.nameError) {
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
      if (this.hideSaveButton) {
        this.$emit('action-form-error', this.formError);
      }
    },
    confirmAction() {
      this.$emit('confirm');
    },
  },
};
</script>

<style lang="scss">
  .x-action-config {
    height: 100%;
    display: grid;
    grid-template-rows: 60px calc(100% - 108px) 48px;
    align-items: flex-start;

    .name {
      display: flex;
      align-items: center;

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

    .actions {
      text-align: right;

      .error-text {
        min-height: 20px;
      }
    }
  }
</style>
