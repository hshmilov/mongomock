<template>
  <XPage
    class="x-enforcement"
    :breadcrumbs="[
      { title: 'enforcement center', path: { name: 'Enforcements'}},
      { title: name }]"
  >
    <XSplitBox>
      <template
        v-if="isEnforcementInitialized"
        #main
      >
        <div class="body">
          <div class="body-flow">
            <XAction
              id="main_action"
              v-bind="mainAction"
              :read-only="userCannotChangeThisEnforcement"
              @click="selectActionMain"
            />
            <XActionGroup
              v-for="item in successiveActions"
              :key="item.condition"
              v-bind="item"
              :read-only="userCannotChangeThisEnforcement || !saved"
              :icons-disabled="isSuccessiveActionIconDisabled(item.items)"
              @select="selectAction"
            />
            <XTrigger
              id="trigger"
              :title="trigger.name"
              :selected="trigger.selected"
              :read-only="isTriggerReadOnly"
              @click="selectTrigger(0)"
            />
          </div>
        </div>
        <div class="footer">
          <div>
            <XButton
              class="view_tasks"
              type="emphasize"
              :disabled="userCannotViewEnforcementsTasks"
              @click="viewTasks"
            >
              View Tasks
            </XButton>
            <XButton
              class="run_enforcement"
              type="emphasize"
              :disabled="disableRun"
              @click="run"
            >
              Run
            </XButton>
          </div>
        </div>
      </template>
      <template #details>
        <XActionPanel
          v-model="actionInProcess"
          :visible.sync="actionPanelVisible"
          :enforcement-name.sync="enforcement.name"
          :actions.sync="enforcementActions"
          :is-editing-mode.sync="actionInEditingMode"
          :successive-actions-types="successiveActionsTypes"
          :main-action-selected="mainActionSelected"
          :current-selected-action-type="currentSelectedActionType"
          :user-cannot-change-this-enforcement="userCannotChangeThisEnforcement"
          :is-existing-enforcement="saved"
          :action-position="actionInProcess.position"
          @restart-action="restartAction"
          @save-enforcement-action="saveEnforcementAction"
          @save-deleted-action="saveDeletedAction"
          @select-main-action="selectActionMain"
          @select-action="selectAction"
          @reset-enforcement-data="resetEnforcementData"
        />
        <XTriggerPanel
          v-model="triggerInProcess"
          :visible="triggerPanelVisible"
          :is-editing-mode.sync="triggerInEditingMode"
          :user-cannot-change-this-enforcement="userCannotChangeThisEnforcement"
          :is-trigger-undefined="triggerNotDefined"
          @save-enforcement-trigger="saveEnforcementTrigger"
          @delete-enforcement-trigger="deleteEnforcementTrigger"
          @select-trigger="selectTrigger"
        />
      </template>
    </XSplitBox>
    <XToast
      v-if="message"
      v-model="message"
    />
  </XPage>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import _get from 'lodash/get';
import _cloneDeep from 'lodash/cloneDeep';
import _isEmpty from 'lodash/isEmpty';
import XPage from '@axons/layout/Page.vue';
import XSplitBox from '@axons/layout/SplitBox.vue';
import XTrigger from '@networks/enforcement/Trigger.vue';
import XAction from '@networks/enforcement/Action.vue';
import XActionGroup from '@networks/enforcement/ActionGroup.vue';
import XToast from '@axons/popover/Toast.vue';
import XActionPanel from '@networks/enforcement/panels/ActionPanel.vue';
import XTriggerPanel from '@networks/enforcement/panels/TriggerPanel.vue';
import {
  FETCH_ENFORCEMENT,
  FETCH_SAVED_ENFORCEMENTS,
  initAction,
  initRecipe,
  initTrigger,
  RUN_ENFORCEMENT,
  SAVE_ENFORCEMENT,
} from '@store/modules/enforcements';
import {
  failCondition,
  mainCondition,
  postCondition,
  successCondition,
} from '@constants/enforcement';
import { ENFORCEMENT_EXECUTED } from '@constants/getting-started';
import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '@store/modules/onboarding';

export default {
  name: 'XEnforcement',
  components: {
    XPage,
    XSplitBox,
    XTrigger,
    XAction,
    XActionGroup,
    XToast,
    XActionPanel,
    XTriggerPanel,
  },
  data() {
    return {
      enforcement: {},
      actionInProcess: {
        position: {}, definition: {},
      },
      triggerInProcess: {
        position: {}, definition: {},
      },
      message: '',
      actionInEditingMode: false,
      triggerInEditingMode: false,
      actionPanelVisible: false,
      triggerPanelVisible: false,
    };
  },
  computed: {
    ...mapState({
      enforcementData(state) {
        return state.enforcements.current.data;
      },
      enforcementFetching(state) {
        return state.enforcements.current.fetching;
      },
      enforcementNames(state) {
        return state.enforcements.savedEnforcements.data;
      },
    }),
    id() {
      return this.$route.params.id;
    },
    name() {
      if (!this.enforcementData || !this.enforcementData.name) return 'New enforcement set';

      return this.enforcementData.name;
    },
    userCannotChangeThisEnforcement() {
      if (this.id === 'new') {
        return this.userCannotAddEnforcements;
      }
      return this.userCannotEditEnforcements;
    },
    userCannotAddEnforcements() {
      return this.$cannot(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.Add);
    },
    userCannotEditEnforcements() {
      return this.$cannot(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.Update);
    },
    userCannotRunEnforcements() {
      return this.$cannot(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.Run);
    },
    userCannotViewEnforcementsTasks() {
      return this.$cannot(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.View, this.$permissionConsts.categories.Tasks);
    },
    isTriggerReadOnly() {
      return (this.userCannotEditEnforcements && this.triggerNotDefined)
        || !this.saved;
    },
    triggerNotDefined() {
      return !this.trigger || !this.trigger.view || !this.trigger.view.id;
    },
    disableRun() {
      return this.triggerNotDefined
        || (this.actionInEditingMode && this.actionPanelVisible)
        || (this.triggerInEditingMode && this.triggerPanelVisible)
        || this.userCannotRunEnforcements;
    },
    enforcementActions: {
      get() {
        if (!this.enforcement || !this.enforcement.actions) return { ...initRecipe };
        return this.enforcement.actions;
      },
      set(modifiedActions) {
        this.enforcement.actions = modifiedActions;
      },
    },
    currentSelectedActionType() {
      return _get(this.actionInProcess, 'position.condition', '');
    },
    mainActionSelected() {
      return this.currentSelectedActionType === mainCondition;
    },
    mainAction() {
      const main = this.enforcementActions[mainCondition];
      const mainAction = {
        condition: mainCondition,
        key: mainCondition,
        selected: this.mainActionSelected,
        readOnly: this.userCannotChangeThisEnforcement,
        titlePrefix: 'action',
        capitalized: this.isMainActionUndefined,
      };
      if (!main || !main.name) return mainAction;
      return {
        ...mainAction,
        name: main.action.action_name,
        title: main.name,
      };
    },
    isMainActionUndefined() {
      return this.enforcementActions && !this.enforcementActions.main;
    },
    successiveActionsTypes() {
      return [successCondition, failCondition, postCondition];
    },
    successiveActions() {
      return this.successiveActionsTypes.map((condition) => ({
        condition,
        id: `${condition}_action`,
        selected: this.selectedAction(condition),
        items: this.enforcementActions[condition],
        readOnly: this.userCannotChangeThisEnforcement,
      }));
    },
    trigger() {
      const selected = this.triggerInProcess.position === 0;
      if (!this.enforcement.triggers || !this.enforcement.triggers.length) return { selected };
      return { ...this.enforcement.triggers[0], selected };
    },
    triggerCount() {
      if (!this.enforcement.triggers) return 0;
      return this.enforcement.triggers.length;
    },
    enforcementId() {
      return this.enforcement.uuid;
    },
    saved() {
      return this.id !== 'new' || this.enforcementId !== undefined;
    },
    isEnforcementInitialized() {
      return !_isEmpty(this.enforcement);
    },
  },
  created() {
    if (this.enforcementFetching || this.id === 'new') {
      this.initData();
    } else {
      this.fetchEnforcement(this.id).then(() => this.initData());
    }
  },
  mounted() {
    if (!this.enforcementNames || !this.enforcementNames.length) {
      this.fetchSavedEnforcements();
    }
  },
  methods: {
    ...mapActions({
      fetchEnforcement: FETCH_ENFORCEMENT,
      saveEnforcement: SAVE_ENFORCEMENT,
      runEnforcement: RUN_ENFORCEMENT,
      fetchSavedEnforcements: FETCH_SAVED_ENFORCEMENTS,
      milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION,
    }),
    initData() {
      this.setEnforcementData();
      this.selectActionMain();
      this.actionPanelVisible = true;
    },
    async run() {
      await this.runEnforcement({
        enforcementId: this.enforcementId,
        isRunFromEnforcementPage: true,
      });
      this.displayMessage('Enforcement Task is in progress');
      await this.milestoneCompleted({ milestoneName: ENFORCEMENT_EXECUTED });
    },
    viewTasks() {
      if (this.saved) {
        this.$router.push({ name: 'EnforcementTasks', params: { id: this.enforcementId } });
      } else {
        this.$router.push({ name: 'Tasks' });
      }
    },
    selectedAction(condition) {
      if (!this.actionInProcess.position
        || this.actionInProcess.position.condition !== condition) return -1;

      return this.actionInProcess.position.i;
    },
    selectAction(condition, i) {
      this.actionPanelVisible = true;
      this.triggerPanelVisible = false;
      this.actionInProcess.position = { condition, i };
      this.actionInProcess.definition = (this.enforcementActions[condition]
        && this.enforcementActions[condition].length > i)
        ? { ...this.enforcementActions[condition][i] }
        : { ...initAction, action: { ...initAction.action } };
      this.triggerInProcess.position = null;
    },
    selectActionMain() {
      this.actionPanelVisible = true;
      this.triggerPanelVisible = false;
      this.setActionMain();
    },
    setActionMain() {
      this.actionInProcess.position = { condition: mainCondition };
      this.actionInProcess.definition = (this.mainAction && this.mainAction.name)
        ? { ...this.enforcementActions.main, action: { ...this.enforcementActions.main.action } }
        : { ...initAction, action: { ...initAction.action } };
      this.triggerInProcess.position = null;
    },
    restartAction() {
      this.selectAction(this.actionInProcess.position.condition, this.actionInProcess.position.i);
    },
    async saveEnforcementAction(successMessage) {
      let enforcementIsNew = false;
      this.setModifiedActionDefinition();
      const newEnforcementId = await this.saveEnforcement(this.enforcement);
      this.displayMessage(successMessage);
      // If enforcement was created
      if (!this.enforcementId) {
        // 'uuid' prop needs to be reactive
        this.$set(this.enforcement, 'uuid', newEnforcementId);
        enforcementIsNew = true;
      }
      await this.resetEnforcementData();
      this.selectRelevantAction(enforcementIsNew);
    },
    async saveDeletedAction(successMessage) {
      await this.saveEnforcement(this.enforcement);
      this.displayMessage(successMessage);
      await this.resetEnforcementData();
    },
    async resetEnforcementData() {
      await this.fetchEnforcement(this.enforcementId);
      this.setEnforcementData();
    },
    setEnforcementData() {
      this.enforcement = { ...this.enforcementData };
    },
    async saveEnforcementTrigger(successMessage) {
      this.setModifiedTriggerDefinition();
      await this.saveEnforcement(this.enforcement);
      this.message = successMessage;
      const { position } = this.triggerInProcess;
      this.selectTrigger(position);
    },
    async deleteEnforcementTrigger(successMessage) {
      this.enforcement.triggers = [];
      await this.saveEnforcement(this.enforcement);
      this.message = successMessage;
    },
    setModifiedActionDefinition() {
      const { condition } = this.actionInProcess.position;
      const { i } = this.actionInProcess.position;
      if (condition === mainCondition) {
        this.enforcementActions[condition] = this.actionInProcess.definition;
      } else if (this.enforcementActions[condition].length <= i) {
        this.enforcementActions[condition].push(this.actionInProcess.definition);
      } else {
        this.enforcementActions[condition][i] = this.actionInProcess.definition;
      }
    },
    selectRelevantAction(enforcementIsNew) {
      const { condition } = this.actionInProcess.position;
      const { i } = this.actionInProcess.position;
      if (condition === mainCondition) {
        if (enforcementIsNew) {
          this.selectTrigger(0);
        } else {
          this.selectActionMain();
        }
      } else {
        this.selectAction(condition, i);
      }
    },
    selectTrigger(i) {
      this.actionPanelVisible = false;
      this.triggerPanelVisible = true;
      if (!_isEmpty(this.actionInProcess.position)) {
        this.actionInProcess.position = {};
      }
      if (i === undefined || i >= this.triggerCount) {
        this.triggerInProcess.position = this.triggerCount;
        this.triggerInProcess.definition = {
          ...initTrigger,
          name: 'Trigger',
          view: { ...initTrigger.view },
          conditions: { ...initTrigger.conditions },
        };
        return;
      }
      this.triggerInProcess.position = i;
      this.triggerInProcess.definition = _cloneDeep(this.enforcement.triggers[i]);
    },
    setModifiedTriggerDefinition() {
      if (this.triggerInProcess.position === null) return;

      const { position } = this.triggerInProcess;
      if (this.triggerCount <= position) {
        this.enforcement.triggers.push(this.triggerInProcess.definition);
      } else {
        this.enforcement.triggers[position] = this.triggerInProcess.definition;
      }
    },
    displayMessage(message) {
      this.message = message;
    },
    isSuccessiveActionIconDisabled(successiveActionItems) {
      return (this.userCannotEditEnforcements && _isEmpty(successiveActionItems))
        || !this.saved;
    },
  },
};
</script>

<style lang="scss">
  .x-enforcement {
    .view_tasks {
      width: 120px;
    }
    .run_enforcement {
      width: 120px;
    }
    .ant-drawer > * {
      transition: none;
    }
    .x-split-box {
      > .main {
        display: grid;
        align-items: flex-start;

        > .body {
          overflow: auto;
          max-height: 100%;

          .body-flow {
            display: grid;
            grid-template-rows: min-content;
            grid-gap: 24px 0;
            .x-action, .x-trigger {
              width: fit-content;
            }
          }
        }

        > .footer {
          text-align: left;
          align-self: end;
          display: flex;
          flex-direction: column;
          position: absolute;
          padding: 5px 30px 0 30px;
          bottom: 0;
          left: 0;
          height: 50px;
        }
      }

      .details {
        .x-card {
          > .header {
            padding-bottom: 12px;
            border-bottom: 1px solid $grey-2;
          }
        }
      }
    }
  }
</style>
