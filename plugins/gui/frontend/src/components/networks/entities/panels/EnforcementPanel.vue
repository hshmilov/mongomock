<template>
  <div>
    <XSidePanel
      v-if="visible"
      panel-class="enforcement-panel"
      :visible="visible"
      :title="panelTitle"
      :panel-container="getSidePanelContainer"
      @close="closePanel"
    >
      <template #panelContent>
        <AForm class="enforcement-form">
          <AFormItem :colon="false">
            <span slot="label">
              Enforcement Set Name
            </span>
            <AInput
              id="enforcement_name"
              ref="enforcement_name_input"
              v-model="enforcement.name"
              placeholder="Enter Enforcement Set name"
              @focusout.stop="setEnforcementNameFocusedOut"
            />
          </AFormItem>
        </AForm>
        <XCard
          v-if="selectedActionName"
          key="actionConf"
          :title="actionConfTitle"
          :logo="actionConfLogo"
          :reversible="true"
          transparent
          back-title="Action Library"
          @back="resetActionConfig"
        >
          <XActionConfig
            v-model="enforcement.actions.main"
            :hide-save-button="true"
            :focus-on-action-name="true"
            @action-validity-changed="onActionValidityChanged"
            @action-name-error="onActionNameErrorChanged"
            @action-form-error="onActionFormErrorChanged"
            @action-name-focused-out="onActionNameFocusedOut"
          />
        </XCard>
        <XCard
          v-else
          key="actionLib"
          title="Action Library"
          transparent
        >
          <XActionLibrary
            :categories="actionCategories"
            @select="selectActionType"
          />
        </XCard>
      </template>
      <template #panelFooter>
        <div class="error-text">
          {{ error }}
        </div>
        <XButton
          type="primary"
          :disabled="disableRun"
          @click="openEnforcementActionResult"
        >Save and Run</XButton>
      </template>
    </XSidePanel>
    <XEnforcementActionResult
      v-if="showEnforcementActionResult"
      :enforcement-action-to-run="saveAndRunEnforcement"
      @close-result="closeEnforcementActionResult"
    />
  </div>
</template>

<script>
import { Form, Input } from 'ant-design-vue';
import { mapState, mapActions } from 'vuex';
import _cond from 'lodash/cond';
import _constant from 'lodash/constant';
import XEnforcementActionResult from '@networks/entities/EnforcementActionResult.vue';
import XSidePanel from '@networks/side-panel/SidePanel.vue';
import XButton from '@axons/inputs/Button.vue';
import XCard from '@axons/layout/Card.vue';
import XActionConfig from '@networks/enforcement/ActionConfig.vue';
import XActionLibrary from '@networks/enforcement/ActionLibrary.vue';
import { actionCategories, actionsMeta } from '@constants/enforcement';
import { ENFORCEMENT_EXECUTED } from '@constants/getting-started';
import { FETCH_SAVED_ENFORCEMENTS, SAVE_ENFORCEMENT } from '@store/modules/enforcements';
import { ENFORCE_DATA } from '@store/actions';
import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '@store/modules/onboarding';

export default {
  name: 'XEnforcementPanel',
  components: {
    XSidePanel,
    XCard,
    XActionConfig,
    XActionLibrary,
    XButton,
    AInput: Input,
    AForm: Form,
    AFormItem: Form.Item,
    XEnforcementActionResult,
  },
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
    entities: {
      type: Object,
      required: true,
      default: () => ({}),
    },
    module: {
      type: String,
      required: true,
      default: '',
    },
    selectionCount: {
      type: Number,
      required: true,
      default: 0,
    },
  },
  data() {
    return {
      enforcement: {},
      actionValidation: {
        isValid: false,
        nameError: '',
        formError: '',
      },
      showEnforcementActionResult: false,
      enforcementNameFocusedOut: false,
      actionNameFocusedOut: false,
    };
  },
  computed: {
    ...mapState({
      enforcementData(state) {
        return state.enforcements.current.data;
      },
      enforcementNames(state) {
        return state.enforcements.savedEnforcements.data;
      },
      view(state) {
        return state[this.module].view;
      },
    }),
    panelTitle() {
      return `New Enforcement (${this.selectionCount} ${this.module})`;
    },
    actionConfTitle() {
      if (!this.selectedActionName) return '';
      return actionsMeta[this.selectedActionName].title;
    },
    actionConfLogo() {
      if (!this.selectedActionName) return '';
      return `actions/${this.selectedActionName}`;
    },
    actionCategories() {
      return actionCategories;
    },
    error() {
      return _cond([
        [() => !this.enforcementNameFocusedOut, _constant('')],
        [() => !this.enforcement.name, _constant('Enforcement Name is a required field')],
        [() => this.enforcementNames.includes(this.enforcement.name),
          _constant('Name already taken by another Enforcement')],
        [() => !this.actionNameFocusedOut, _constant('')],
        [() => this.actionValidation.nameError, _constant(this.actionValidation.nameError)],
        [() => this.actionValidation.formError, _constant(this.actionValidation.formError)],
        [() => !this.actionValidation.isValid && this.selectedActionName,
          _constant('Action must be correctly configured for the Enforcement')],
      ])();
    },
    disableRun() {
      return Boolean(this.error) || !this.enforcementNameFocusedOut || !this.actionNameFocusedOut;
    },
    selectedActionName: {
      get() {
        return this.enforcement.actions.main.action.action_name;
      },
      set(name) {
        this.enforcement.actions.main.action.action_name = name;
      },
    },
  },
  watch: {
    visible(isVisible) {
      if (isVisible) {
        this.resetEnforcementData('');
      }
    },
  },
  updated() {
    this.$nextTick().then(() => {
      this.$refs.enforcement_name_input.focus();
    });
  },
  created() {
    if (!this.enforcementNames || !this.enforcementNames.length) {
      this.fetchSavedEnforcements();
    }
  },
  methods: {
    ...mapActions({
      saveEnforcement: SAVE_ENFORCEMENT,
      enforceData: ENFORCE_DATA,
      fetchSavedEnforcements: FETCH_SAVED_ENFORCEMENTS,
      milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION,
    }),
    resetActionConfig() {
      this.actionNameFocusedOut = false;
      this.resetEnforcementData(this.enforcement.name);
    },
    resetEnforcementData(enforcementName) {
      this.enforcement = { ...this.enforcementData, name: enforcementName };
      this.enforcement.actions.main = { action: { action_name: '' }, name: '' };
      this.actionValidation = {
        isValid: false,
        nameError: '',
        formError: '',
      };
    },
    selectActionType(name) {
      this.selectedActionName = name;
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
    onActionNameFocusedOut() {
      this.actionNameFocusedOut = true;
    },
    closePanel(skipReset) {
      if (!skipReset) {
        this.resetEnforcementData('');
      }
      this.enforcementNameFocusedOut = false;
      this.actionNameFocusedOut = false;
      this.$emit('close');
    },
    enforceEntities() {
      const { fields, sort, colFilters } = this.view;
      return this.enforceData({
        module: this.module,
        data: {
          name: this.enforcement.name,
          view: { fields, sort, colFilters },
          selection: { ...this.entities },
        },
      });
    },
    async saveAndRunEnforcement() {
      const newEnforcementId = await this.saveEnforcement(this.enforcement);
      await this.milestoneCompleted({ milestoneName: ENFORCEMENT_EXECUTED });
      await this.enforceEntities();
      return newEnforcementId;
    },
    openEnforcementActionResult() {
      this.closePanel(true);
      this.showEnforcementActionResult = true;
    },
    closeEnforcementActionResult() {
      this.showEnforcementActionResult = false;
      this.resetEnforcementData('');
      this.$emit('done');
    },
    getSidePanelContainer() {
      return document.querySelector('.x-data-table');
    },
    setEnforcementNameFocusedOut() {
      this.enforcementNameFocusedOut = true;
    },
  },
};
</script>

<style lang="scss">
  .enforcement-panel {
    .ant-drawer-body {
      &__content {
        overflow-x: hidden;
        overflow-y: hidden !important;
        display: flex;
        flex-direction: column;
        .x-card {
          min-height: 100%;
          > .header {
            padding-bottom: 12px;
            border-bottom: 1px solid $grey-2;
          }
          .x-action-config {
            grid-template-rows: 60px calc(100% - 72px) 48px;
          }
        }
        .enforcement-form {
          border-bottom: 1px solid $grey-2;
          .ant-input {
            color: $grey-5;
          }
        }
      }
      &__footer {
        display: flex;
        justify-content: space-between;
      }
    }
  }
</style>
