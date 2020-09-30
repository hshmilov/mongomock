<template>
  <XSidePanel
    panel-class="x-trigger-panel"
    title="Trigger"
    :mask="false"
    :visible="visible"
    :panel-container="getSidePanelContainer"
    :close-icon-visible="false"
    @close="onCancel"
  >
    <template #panelHeader>
      <XEnforcementPanelHeader
        v-if="editAndDeleteAllowed"
        @edit="toggleEditMode"
        @delete="deleteTrigger"
      />
    </template>
    <template #panelContent>
      <XTriggerConfig
        v-if="!triggerInSavingProcess"
        v-model="triggerDefinition"
        :read-only="triggerConfigurationDisabled"
        @trigger-validity-changed="onTriggerValidityChanged"
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
      <XButton
        id="cancel-changes"
        type="link"
        @click="onCancel"
      >
        {{ cancelButtonText }}
      </XButton>
      <XButton
        type="primary"
        :disabled="!isTriggerValid"
        @click="onSave"
      >Save</XButton>
    </template>
  </XSidePanel>
</template>

<script>
import { Spin, Icon } from 'ant-design-vue';
import XTriggerConfig from '@networks/enforcement/TriggerConfig.vue';
import XSidePanel from '@networks/side-panel/SidePanel.vue';
import {
  createdToastMessages,
  updatedToastMessages,
  deletedToastMessages,
} from '@constants/enforcement';
import XEnforcementPanelHeader from './EnforcementPanelHeader.vue';

export default {
  name: 'XTriggerPanel',
  components: {
    XTriggerConfig,
    XSidePanel,
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
    userCannotChangeThisEnforcement: {
      type: Boolean,
      default: false,
      required: true,
    },
    isEditingMode: {
      type: Boolean,
      default: false,
      required: true,
    },
    isTriggerUndefined: {
      type: Boolean,
      default: false,
      required: true,
    },
  },
  data() {
    return {
      isTriggerValid: false,
      triggerInSavingProcess: false,
    };
  },
  computed: {
    triggerInProcess() {
      return this.value;
    },
    triggerDefinition: {
      get() {
        return this.triggerInProcess.definition;
      },
      set(modifiedTriggerDefinition) {
        this.$emit('input', { ...this.triggerInProcess, definition: modifiedTriggerDefinition });
      },
    },
    editAndDeleteAllowed() {
      return !this.isEditingMode && !this.userCannotChangeThisEnforcement
        && !this.triggerInSavingProcess;
    },
    triggerConfigurationDisabled() {
      return !this.isEditingMode || this.userCannotChangeThisEnforcement;
    },
    modifiedToastMessage() {
      if (this.isTriggerUndefined) {
        return createdToastMessages.trigger;
      }
      return updatedToastMessages.trigger;
    },
    deletedToastMessage() {
      return deletedToastMessages.trigger;
    },
    cancelButtonText() {
      return this.isTriggerUndefined ? 'Clear' : 'Cancel';
    },
  },
  watch: {
    visible(isVisible) {
      if (isVisible) {
        this.$emit('update:is-editing-mode', this.isTriggerUndefined);
      } else {
        this.isTriggerValid = false;
      }
    },
    triggerDefinition() {
      if (this.triggerInSavingProcess) {
        this.triggerInSavingProcess = false;
      }
    },
  },
  mounted() {
    this.$emit('update:is-editing-mode', this.isTriggerUndefined);
  },
  methods: {
    getSidePanelContainer() {
      return document.querySelector('.details');
    },
    deleteTrigger() {
      this.$safeguard.show({
        text: `
          This trigger will be deleted. Deleting the trigger is irreversible.
          <br />
          Do you wish to continue?
        `,
        confirmText: 'Yes, Delete',
        onConfirm: () => {
          this.removeTrigger();
        },
      });
    },
    removeTrigger() {
      this.toggleEditMode();
      this.isTriggerValid = false;
      this.$emit('delete-enforcement-trigger', this.deletedToastMessage);
      this.$emit('select-trigger', 0);
    },
    toggleEditMode() {
      this.$emit('update:is-editing-mode', !this.isEditingMode);
      this.isTriggerValid = true;
    },
    onTriggerValidityChanged(isValid) {
      this.isTriggerValid = isValid;
    },
    onCancel() {
      if (!this.isTriggerUndefined) {
        this.toggleEditMode();
      } else {
        this.isTriggerValid = false;
      }
      this.$emit('select-trigger', 0);
    },
    onSave() {
      this.triggerInSavingProcess = true;
      this.toggleEditMode();
      this.$emit('save-enforcement-trigger', this.modifiedToastMessage);
    },
  },
};
</script>

<style lang="scss">
  .v-menu__content {
    z-index: 1001 !important;
  }
  .x-side-panel.x-trigger-panel {
    .ant-drawer-body {
      padding-top: 12px;
      &__content {
        height: calc(100% - 52px);
        overflow-x: hidden;
        padding-top: 0;
        padding-bottom: 0;
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
        justify-content: flex-end;
      }
    }
  }
</style>
