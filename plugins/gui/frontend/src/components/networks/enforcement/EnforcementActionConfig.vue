<template>
  <div
    class="x-enforcement-action-config"
    :class="{'enforcement-exists': isExistingEnforcement, 'action-exists': !isActionUndefined}"
  >
    <AForm
      v-if="!isExistingEnforcement"
      class="enforcement-form"
    >
      <AFormItem :colon="false">
        <span slot="label">
          Enforcement Set name
        </span>
        <AInput
          id="enforcement_name"
          ref="enforcement_name_input"
          v-model="enforcementNameValue"
          placeholder="Enter Enforcement Set name"
          @focusout.stop="enforcementNameFocusedOut = true"
        />
      </AFormItem>
    </AForm>
    <XCard
      v-if="selectedActionLibraryType"
      :title="actionConfTitle"
      :logo="actionConfLogo"
      :reversible="currentActionReversible"
      transparent
      back-title="Action Library"
      @back="resetActionConfig"
    >
      <XActionConfig
        v-model="actionDefinition"
        :allowed-action-names="allowedActionNames"
        :read-only="actionConfigurationDisabled"
        @action-validity-changed="onActionValidityChanged"
        @action-name-error="onActionNameErrorChanged"
        @action-form-error="onActionFormErrorChanged"
        @action-name-focused-out="actionNameFocusedOut = true"
      />
    </XCard>
    <XCard
      v-else
      title="Action Library"
      transparent
    >
      <XActionLibrary
        :categories="actionCategories"
        @select="$emit('select-action-type', $event)"
      />
    </XCard>
  </div>
</template>

<script>
import { Form, Input } from 'ant-design-vue';
import { mapState } from 'vuex';
import _cond from 'lodash/cond';
import _constant from 'lodash/constant';
import XCard from '@axons/layout/Card.vue';
import XActionConfig from '@networks/enforcement/ActionConfig.vue';
import XActionLibrary from '@networks/enforcement/ActionLibrary.vue';
import {
  actionCategories,
  actionsMeta,
} from '@constants/enforcement';

export default {
  name: 'XEnforcementActionConfig',
  components: {
    XCard,
    XActionConfig,
    XActionLibrary,
    AInput: Input,
    AForm: Form,
    AFormItem: Form.Item,
  },
  props: {
    value: {
      type: Object,
      default: () => ({}),
      required: true,
    },
    enforcementName: {
      type: String,
      default: '',
      required: true,
    },
    selectedActionLibraryType: {
      type: String,
      default: '',
      required: true,
    },
    currentActionReversible: {
      type: Boolean,
      default: true,
    },
    allowedActionNames: {
      type: Array,
      default: () => ([]),
    },
    actionConfigurationDisabled: {
      type: Boolean,
      default: false,
    },
    isExistingEnforcement: {
      type: Boolean,
      default: false,
    },
    isActionUndefined: {
      type: Boolean,
      default: true,
    },
    focusOnEnforcementName: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      actionValidation: {
        isValid: false,
        nameError: '',
        formError: '',
      },
      enforcementNameFocusedOut: false,
      actionNameFocusedOut: false,
    };
  },
  computed: {
    ...mapState({
      enforcementNames(state) {
        return state.enforcements.savedEnforcements.data;
      },
    }),
    actionDefinition: {
      get() {
        return this.value;
      },
      set(modifiedActionDefinition) {
        this.$emit('input', { ...modifiedActionDefinition });
      },
    },
    actionCategories() {
      return actionCategories;
    },
    error() {
      return _cond([
        [() => !this.enforcementNameFocusedOut, _constant('')],
        [() => !this.enforcementName, _constant('Enforcement Name is a required field')],
        [() => this.enforcementNames.includes(this.enforcementNameValue)
          && !this.isExistingEnforcement, _constant('Name already taken by another Enforcement')],
        [() => !this.actionNameFocusedOut, _constant('')],
        [() => this.actionValidation.nameError, _constant(this.actionValidation.nameError)],
        [() => this.actionValidation.formError, _constant(this.actionValidation.formError)],
      ])();
    },
    disableSave() {
      return Boolean(this.error)
        || !this.enforcementNameFocusedOut || !this.actionValidation.isValid;
    },
    enforcementNameValue: {
      get() {
        return this.enforcementName;
      },
      set(modifiedEnforcementName) {
        this.$emit('update:enforcement-name', modifiedEnforcementName);
      },
    },
    actionConfTitle() {
      if (!this.selectedActionLibraryType) return '';
      return actionsMeta[this.selectedActionLibraryType].title;
    },
    actionConfLogo() {
      if (!this.selectedActionLibraryType) return '';
      return `actions/${this.selectedActionLibraryType}`;
    },
  },
  watch: {
    disableSave(isSaveDisabled) {
      this.$emit('config-validity-changed', isSaveDisabled);
    },
    error(errorMessage) {
      this.$emit('config-error-message-changed', errorMessage);
    },
  },
  mounted() {
    this.setFocusOnEnforcementName();
    this.enforcementNameFocusedOut = false;
    this.actionNameFocusedOut = false;
    this.$emit('config-error-message-changed', this.errorMessage);
  },
  methods: {
    initConfigValidations() {
      this.setFocusOnEnforcementName();
      this.$emit('config-validity-changed', this.disableSave);
      if (this.isExistingEnforcement) {
        this.enforcementNameFocusedOut = true;
        if (this.isActionUndefined) {
          this.actionNameFocusedOut = false;
          this.resetActionValidations();
        } else {
          this.actionNameFocusedOut = true;
        }
      }
    },
    cancelConfig() {
      this.setFocusOnEnforcementName();
      this.resetActionValidations();
      this.actionNameFocusedOut = false;
      if (!this.isExistingEnforcement) {
        this.enforcementNameFocusedOut = false;
        this.enforcementNameValue = '';
      }
    },
    resetActionConfig() {
      this.resetActionValidations();
      this.actionNameFocusedOut = false;
      this.$emit('reset-action-config');
    },
    resetActionValidations() {
      this.actionValidation = {
        isValid: false,
        nameError: '',
        formError: '',
      };
    },
    onActionNameErrorChanged(actionNameError) {
      this.actionValidation.nameError = actionNameError;
    },
    onActionFormErrorChanged(actionFormError) {
      this.actionValidation.formError = actionFormError;
    },
    onActionValidityChanged(isValid) {
      this.actionValidation.isValid = isValid;
    },
    setFocusOnEnforcementName() {
      if (!this.isExistingEnforcement && this.focusOnEnforcementName) {
        this.$nextTick().then(() => {
          this.$refs.enforcement_name_input.focus();
        });
      }
    },
  },
};
</script>

<style lang="scss">
  .x-enforcement-action-config {
    height: 100%;
    .x-card {
      height: 100%;
      > .header {
        padding-bottom: 12px;
        border-bottom: 1px solid $grey-2;
      }
      .body {
        height: calc(100% - 196px);
      }
      .x-action-config {
        height: calc(100% - 16px);
        .x-array-edit .object.expand {
          width: 96%;
        }
      }
    }
    .enforcement-form {
      border-bottom: 1px solid $grey-2;
      .ant-input {
        color: $grey-5;
      }
      .ant-form-item {
        margin-bottom: 8px;
      }
    }
    &.enforcement-exists {
      .x-card {
        > .header {
          padding-top: 0;
        }
        .body {
          height: calc(100% - 96px);
        }
      }
    }
    &.action-exists {
      .x-card {
        .body {
          height: calc(100% - 50px);
        }
      }
    }
  }
</style>
