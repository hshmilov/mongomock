<template>
  <XSidePanel
    :panel-class="panelClass"
    :mask="false"
    :visible="visible"
    :title="title"
    :panel-container="getSidePanelContainer"
    :close-icon-visible="false"
    @close="onCancel"
  >
    <template #panelHeader>
      <XEnforcementPanelHeader
        v-if="editAndDeleteAllowed"
        @edit="toggleEditMode"
        @delete="deleteAction"
      />
    </template>
    <template #panelContent>
      <XEnforcementActionConfig
        v-if="!actionInSavingProcess"
        ref="enforcementActionConfig"
        v-model="actionDefinition"
        :enforcement-name.sync="enforcementNameValue"
        :selected-action-library-type="selectedActionLibraryType"
        :current-action-reversible="currentActionReversible"
        :allowed-action-names="allowedActionNames"
        :action-configuration-disabled="actionConfigurationDisabled"
        :is-existing-enforcement="isExistingEnforcement"
        :is-action-undefined="isActionUndefined"
        @select-action-type="selectActionType"
        @reset-action-config="$emit('restart-action')"
        @config-validity-changed="onConfigValidityChanged"
        @config-error-message-changed="onConfigErrorMessageChanged"
      />
      <ASpin
        v-else
        size="large"
        class="loading-spinner"
      >
        <AIcon
          slot="indicator"
          type="loading"
        />
      </ASpin>
    </template>
    <template
      v-if="isEditingMode"
      #panelFooter
    >
      <div class="error-text">
        {{ errorMessage }}
      </div>
      <div class="buttons">
        <XButton
          id="cancel-changes"
          type="link"
          @click="onCancel"
        >
          {{ cancelButtonText }}
        </XButton>
        <XButton
          type="primary"
          :disabled="isSavedDisabled"
          @click="onSave"
        >Save</XButton>
      </div>
    </template>
  </XSidePanel>
</template>

<script>
import { Spin, Icon } from 'ant-design-vue';
import _cond from 'lodash/cond';
import _constant from 'lodash/constant';
import _get from 'lodash/get';
import _isEmpty from 'lodash/isEmpty';
import XSidePanel from '@networks/side-panel/SidePanel.vue';
import XEnforcementActionConfig from '@networks/enforcement/EnforcementActionConfig.vue';
import {
  mainCondition,
  createdToastMessages,
  updatedToastMessages,
  deletedToastMessages,
} from '@constants/enforcement';
import XEnforcementPanelHeader from './EnforcementPanelHeader.vue';

export default {
  name: 'XActionPanel',
  components: {
    XSidePanel,
    XEnforcementActionConfig,
    XEnforcementPanelHeader,
    ASpin: Spin,
    AIcon: Icon,
  },
  props: {
    visible: {
      type: Boolean,
      default: false,
      required: true,
    },
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
    actions: {
      type: Object,
      default: () => ({}),
      required: true,
    },
    userCannotChangeThisEnforcement: {
      type: Boolean,
      default: false,
      required: true,
    },
    isExistingEnforcement: {
      type: Boolean,
      default: false,
      required: true,
    },
    isEditingMode: {
      type: Boolean,
      default: false,
      required: true,
    },
    successiveActionsTypes: {
      type: Array,
      default: () => ([]),
      required: true,
    },
    mainActionSelected: {
      type: Boolean,
      default: false,
      required: true,
    },
    currentSelectedActionType: {
      type: String,
      default: '',
      required: true,
    },
    actionPosition: {
      type: Object,
      default: () => ({}),
      required: true,
    },
  },
  data() {
    return {
      allowedActionNames: [],
      isSavedDisabled: true,
      errorMessage: '',
      actionInSavingProcess: false,
    };
  },
  computed: {
    panelClass() {
      return `x-action-panel${!this.mainActionSelected ? ' successive' : ''}`;
    },
    actionInProcess() {
      return this.value;
    },
    actionDefinition: {
      get() {
        return this.actionInProcess.definition;
      },
      set(modifiedActionDefinition) {
        this.$emit('input', { ...this.actionInProcess, definition: modifiedActionDefinition });
      },
    },
    enforcementNameValue: {
      get() {
        return this.enforcementName;
      },
      set(modifiedEnforcementName) {
        this.$emit('update:enforcement-name', modifiedEnforcementName);
      },
    },
    editAndDeleteAllowed() {
      return !this.isEditingMode && !this.userCannotChangeThisEnforcement
        && !this.actionInSavingProcess;
    },
    actionConfigurationDisabled() {
      return !this.isEditingMode || this.userCannotChangeThisEnforcement;
    },
    selectedActionLibraryType() {
      if (!this.actionDefinition || !this.actionDefinition.action
              || !this.actionPosition) return '';

      return this.actionDefinition.action.action_name;
    },
    isActionUndefined() {
      return (this.mainActionSelected && !this.actions.main)
      || (this.successiveActionSelected && !this.successiveActionSelectedAndDefined);
    },
    successiveActionSelected() {
      return this.successiveActionsTypes.includes(this.currentSelectedActionType);
    },
    successiveActionSelectedAndDefined() {
      return this.successiveActionSelected
              && this.actions[this.currentSelectedActionType][this.actionPosition.i];
    },
    selectedActionTitle() {
      if (!this.currentSelectedActionType) {
        return '';
      }
      return `${this.currentSelectedActionType[0].toUpperCase()
      + this.currentSelectedActionType.slice(1)} Action`;
    },
    selectedActionName() {
      return _get(this.actionInProcess, 'definition.name', '');
    },
    mainActionTypeName() {
      return !this.isActionUndefined
        && _get(this.actions[mainCondition], 'action.action_name', '');
    },
    title() {
      return _cond([
        [() => this.mainActionSelected && this.actions.main,
          _constant(this.selectedActionName)],
        [() => this.mainActionSelected, _constant(this.selectedActionTitle)],
        [() => this.successiveActionSelectedAndDefined,
          _constant(this.selectedActionName)],
        [() => this.successiveActionSelected, _constant(this.selectedActionTitle)],
      ])();
    },
    modifiedToastMessage() {
      if (this.isActionUndefined) {
        return createdToastMessages[this.currentSelectedActionType];
      }
      return updatedToastMessages[this.currentSelectedActionType];
    },
    deletedToastMessage() {
      return deletedToastMessages[this.currentSelectedActionType];
    },
    currentActionReversible() {
      const { position } = this.actionInProcess;
      if (_isEmpty(position)) return false;
      return (this.mainActionSelected && !this.mainActionTypeName)
        || (!this.mainActionSelected && this.actions[position.condition].length === position.i);
    },
    isMainActionDeleted() {
      return this.isExistingEnforcement && this.actions[mainCondition] === null;
    },
    cancelButtonText() {
      return this.isActionUndefined ? 'Clear' : 'Cancel';
    },
  },
  watch: {
    actionPosition() {
      this.isSavedDisabled = true;
      this.$emit('update:is-editing-mode', this.isActionUndefined);
      this.$nextTick(() => {
        const { enforcementActionConfig } = this.$refs;
        if (enforcementActionConfig) {
          enforcementActionConfig.initConfigValidations();
        }
      });
      // If main action was deleted and not recreated,
      // we have to fetch the original main action data again
      if (this.isMainActionDeleted && !this.mainActionSelected) {
        this.$emit('reset-enforcement-data');
      }
    },
    actionDefinition() {
      if (this.actionInSavingProcess) {
        this.actionInSavingProcess = false;
      }
    },
    isMainActionDeleted(deleted) {
      if (!deleted) {
        this.allowedActionNames = [];
      }
    },
  },
  mounted() {
    this.$emit('update:is-editing-mode', !this.isExistingEnforcement);
  },
  methods: {
    onConfigValidityChanged(isSaveDisabled) {
      this.isSavedDisabled = isSaveDisabled;
    },
    onConfigErrorMessageChanged(errorMessage) {
      this.errorMessage = errorMessage;
    },
    getSidePanelContainer() {
      return document.querySelector('.details');
    },
    selectActionType(name) {
      this.actionDefinition = {
        ...this.actionDefinition,
        action: {
          action_name: name,
          config: null,
        },
      };
    },
    toggleEditMode() {
      this.$emit('update:is-editing-mode', !this.isEditingMode);
    },
    onCancel() {
      if (!this.isActionUndefined) {
        this.toggleEditMode();
      } else {
        this.$refs.enforcementActionConfig.cancelConfig();
      }
      if (this.mainActionSelected) {
        this.$emit('select-main-action');
      } else {
        this.$emit('select-action', this.actionPosition.condition, this.actionPosition.i);
      }
    },
    onSave() {
      this.actionInSavingProcess = true;
      this.toggleEditMode();
      this.$emit('save-enforcement-action', this.modifiedToastMessage);
    },
    deleteAction() {
      const confirmText = 'Yes, Delete';
      let text;
      let confirmFunction;
      if (this.mainActionSelected) {
        text = 'This action will be deleted. <br/> Do you wish to continue?';
        confirmFunction = () => { this.removeActionMain(); };
      } else {
        text = 'This action will be deleted. Deleting the action is irreversible. '
                + '<br/> Do you wish to continue?';
        confirmFunction = () => {
          this.removeAction(this.actionPosition.condition, this.actionPosition.i);
        };
      }

      this.$safeguard.show({
        text,
        confirmText,
        onConfirm: confirmFunction,
      });
    },
    removeAction(condition, i) {
      this.$emit('update:actions', {
        ...this.actions,
        [condition]: this.actions[condition].filter((elem, index) => index !== i),
      });
      if (condition === this.actionPosition.condition) {
        this.$emit('select-action', this.actionPosition.condition, this.actionPosition.i);
      }
      this.$emit('save-deleted-action', this.deletedToastMessage);
    },
    removeActionMain() {
      this.allowedActionNames.push(this.actions[mainCondition].name);
      this.toggleEditMode();
      this.$emit('update:actions', { ...this.actions, [mainCondition]: null });
      this.$emit('select-main-action');
    },
  },
};
</script>

<style lang="scss">
  .x-side-panel.x-action-panel {
    .ant-drawer-body {
      padding-top: 12px;
      &__content {
        padding-top: 0;
        padding-bottom: 0;
        overflow-x: hidden;
        overflow-y: hidden !important;
        .loading-spinner {
          position: absolute;
          left: 50%;
          top: 50%;
          -webkit-transform: translate(-50%, -50%);
          transform: translate(-50%, -50%);
          margin: auto;
          color: $theme-orange;
        }
      }
      &__footer {
        display: flex;
        justify-content: space-between;
        .buttons {
          display: flex;
          justify-content: flex-end;
        }
      }
    }
  }
</style>
