<template>
  <div>
    <XSidePanel
      panel-class="enforcement-panel"
      :visible="visible"
      :title="panelTitle"
      :panel-container="getSidePanelContainer"
      @close="closePanel"
    >
      <template #panelContent v-if="enforcement">
        <XEnforcementActionConfig
          v-model="enforcement.actions.main"
          :enforcement-name.sync="enforcement.name"
          :selected-action-library-type="selectedActionLibraryType"
          :focus-on-enforcement-name="false"
          @select-action-type="selectActionType"
          @reset-action-config="resetActionConfig"
          @config-validity-changed="onConfigValidityChanged"
          @config-error-message-changed="onConfigErrorMessageChanged"
        />
      </template>
      <template #panelFooter>
        <div class="error-text">
          {{ errorMessage }}
        </div>
        <XButton
          type="primary"
          :disabled="isRunDisabled"
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
import { mapState, mapActions } from 'vuex';
import _get from 'lodash/get';
import XEnforcementActionResult from '@networks/entities/EnforcementActionResult.vue';
import XSidePanel from '@networks/side-panel/SidePanel.vue';
import XEnforcementActionConfig from '@networks/enforcement/EnforcementActionConfig.vue';
import { ENFORCEMENT_EXECUTED } from '@constants/getting-started';
import { FETCH_SAVED_ENFORCEMENTS, SAVE_ENFORCEMENT } from '@store/modules/enforcements';
import { ENFORCE_DATA } from '@store/actions';
import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '@store/modules/onboarding';

export default {
  name: 'XEnforcementPanel',
  components: {
    XSidePanel,
    XEnforcementActionResult,
    XEnforcementActionConfig,
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
      enforcement: null,
      showEnforcementActionResult: false,
      isRunDisabled: true,
      errorMessage: '',
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
    selectedActionLibraryType: {
      get() {
        return _get(this.enforcement, 'actions.main.action.action_name', '');
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
        this.isRunDisabled = true;
      }
    },
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
    onConfigValidityChanged(isRunDisabled) {
      this.isRunDisabled = isRunDisabled;
    },
    onConfigErrorMessageChanged(errorMessage) {
      this.errorMessage = errorMessage;
    },
    resetActionConfig() {
      this.resetEnforcementData(this.enforcement.name);
    },
    resetEnforcementData(enforcementName) {
      this.enforcement = { ...this.enforcementData, name: enforcementName };
      this.enforcement.actions.main = { action: { action_name: '' }, name: '' };
    },
    selectActionType(name) {
      this.selectedActionLibraryType = name;
    },
    closePanel(skipReset) {
      if (!skipReset) {
        this.resetEnforcementData('');
      }
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
  },
};
</script>

<style lang="scss">
  .x-side-panel.enforcement-panel {
    .ant-drawer-body {
      padding-top: 12px;
      &__content {
        padding-top: 0;
        padding-bottom: 0;
        overflow-x: hidden;
        overflow-y: hidden !important;
      }
      &__footer {
        display: flex;
        justify-content: space-between;
      }
    }
  }
</style>
