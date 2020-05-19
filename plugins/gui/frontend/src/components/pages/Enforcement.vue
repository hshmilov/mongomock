<template>
  <XPage
    class="x-enforcement"
    :breadcrumbs="[
      { title: 'enforcement center', path: { name: 'Enforcements'}},
      { title: name }]"
  >
    <XSplitBox>
      <template slot="main">
        <div class="header">
          <label>Enforcement Set Name</label>
          <input
            v-if="id === 'new'"
            id="enforcement_name"
            ref="name"
            v-model="enforcement.name"
            :disabled="userCannotChangeThisEnforcement"
          >
          <input
            v-else
            :value="enforcement.name"
            disabled
          >
        </div>
        <div class="body">
          <div class="body-flow">
            <XAction
              id="main_action"
              v-bind="mainAction"
              :read-only="userCannotChangeThisEnforcement"
              @click="selectActionMain"
              @remove="removeActionMain"
            />
            <XActionGroup
              v-for="item in successiveActions"
              :key="item.condition"
              v-bind="item"
              :read-only="userCannotChangeThisEnforcement"
              @select="selectAction"
              @remove="removeAction"
            />
            <XTrigger
              id="trigger"
              :title="trigger.name"
              :selected="trigger.selected"
              :read-only="userCannotChangeThisEnforcement"
              @click="selectTrigger(0)"
            />
          </div>
        </div>
        <div class="footer">
          <div class="error-text">
            {{ error }}
          </div>
          <div>
            <XButton
              v-if="saved"
              id="view_tasks"
              type="emphasize"
              :disabled="userCannotViewEnforcementsTasks"
              @click="viewTasks"
            >
              View Tasks
            </XButton>
            <XButton
              v-if="userCannotChangeThisEnforcement"
              type="primary"
              @click="exit"
            >
              Exit
            </XButton>
            <template v-else>
              <XButton
                type="emphasize"
                :disabled="disableRun"
                @click="saveRun"
              >
                Save & Run
              </XButton>
              <XButton
                id="enforcement_save"
                type="primary"
                :disabled="disableSave"
                @click="saveExit"
              >
                Save & Exit
              </XButton>
            </template>
          </div>
        </div>
      </template>
      <XCard
        v-if="trigger.selected"
        slot="details"
        key="triggerConf"
        title="Trigger Configuration"
        logo="adapters/axonius"
      >
        <XTriggerConfig
          v-model="triggerInProcess.definition"
          :read-only="userCannotChangeThisEnforcement"
          @confirm="saveTrigger"
        />
      </XCard>
      <XCard
        v-else-if="currentActionName"
        slot="details"
        key="actionConf"
        :title="actionConfTitle"
        :logo="actionConfLogo"
        :reversible="currentActionReversible"
        @back="restartAction"
      >
        <XActionConfig
          v-model="actionInProcess.definition"
          :exclude="excludedNames"
          :include="allowedActionNames"
          :read-only="userCannotChangeThisEnforcement"
          @confirm="saveAction"
        />
      </XCard>
      <XCard
        v-else-if="actionInProcess.position"
        slot="details"
        key="actionLib"
        title="Action Library"
        logo="adapters/axonius"
      >
        <XActionLibrary
          :categories="actionCategories"
          @select="selectActionType"
        />
      </XCard>
    </XSplitBox>
    <XToast
      v-if="message"
      v-model="message"
    />
  </XPage>
</template>

<script>
import { mapState, mapActions } from 'vuex';

import XPage from '../axons/layout/Page.vue';
import XSplitBox from '../axons/layout/SplitBox.vue';
import XCard from '../axons/layout/Card.vue';
import XButton from '../axons/inputs/Button.vue';
import XTrigger from '../networks/enforcement/Trigger.vue';
import XTriggerConfig from '../networks/enforcement/TriggerConfig.vue';
import XAction from '../networks/enforcement/Action.vue';
import XActionGroup from '../networks/enforcement/ActionGroup.vue';
import XActionConfig from '../networks/enforcement/ActionConfig.vue';
import XActionLibrary from '../networks/enforcement/ActionLibrary.vue';
import XToast from '../axons/popover/Toast.vue';

import {
  initRecipe, initAction, initTrigger,
  FETCH_ENFORCEMENT, SAVE_ENFORCEMENT, RUN_ENFORCEMENT,
  FETCH_SAVED_ENFORCEMENTS,
} from '../../store/modules/enforcements';

import {
  successCondition, failCondition, postCondition, mainCondition, actionCategories, actionsMeta,
} from '../../constants/enforcement';
import { ENFORCEMENT_EXECUTED } from '../../constants/getting-started';
import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '../../store/modules/onboarding';

export default {
  name: 'XEnforcement',
  components: {
    XPage,
    XSplitBox,
    XCard,
    XButton,
    XTrigger,
    XTriggerConfig,
    XAction,
    XActionGroup,
    XActionConfig,
    XActionLibrary,
    XToast,
  },
  data() {
    return {
      enforcement: {},
      actionInProcess: {
        position: null, definition: null,
      },
      triggerInProcess: {
        position: null, definition: null,
      },
      allowedActionNames: [],
      message: '',
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
      if (!this.enforcementData || !this.enforcementData.name) return 'New Enforcement Set';

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
    userCannotViewEnforcementsTasks() {
      return this.$cannot(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.View, this.$permissionConsts.categories.Tasks);
    },
    error() {
      if (!this.enforcement.name) {
        return 'Enforcement Name is a required field';
      }
      if (!this.enforcementData.name && this.enforcementNames.includes(this.enforcement.name)) {
        return 'Name already taken by another Enforcement';
      }
      if (!this.mainAction.name) {
        return 'A Main Action is required for Enforcement';
      }
      return '';
    },
    disableSave() {
      return Boolean(this.error);
    },
    disableRun() {
      return this.disableSave || !this.trigger || !this.trigger.view || !this.trigger.view.name;
    },
    actions() {
      if (!this.enforcement || !this.enforcement.actions) return { ...initRecipe };

      return this.enforcement.actions;
    },
    mainAction() {
      const main = this.actions[mainCondition];
      const mainAction = {
        condition: mainCondition,
        key: mainCondition,
        selected: this.mainActionSelected,
        readOnly: this.userCannotChangeThisEnforcement,
        titlePrefix: 'action',
      };
      if (!main || !main.name) return mainAction;
      return {
        ...mainAction,
        name: main.action.action_name,
        title: main.name,
      };
    },
    mainActionSelected() {
      return this.actionInProcess.position
        && this.actionInProcess.position.condition === mainCondition;
    },
    successiveActions() {
      return [successCondition, failCondition, postCondition].map((condition) => ({
        condition,
        id: `${condition}_action`,
        selected: this.selectedAction(condition),
        items: this.actions[condition],
        readOnly: this.userCannotChangeThisEnforcement,
      }));
    },
    actionConfTitle() {
      if (!this.currentActionName) return '';
      return `Action Library / ${actionsMeta[this.currentActionName].title}`;
    },
    actionConfLogo() {
      if (!this.currentActionName) return '';
      return `actions/${this.currentActionName}`;
    },
    currentActionName() {
      if (!this.actionInProcess.definition || !this.actionInProcess.definition.action
                || !this.actionInProcess.position) return '';

      return this.actionInProcess.definition.action.action_name;
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
    actionCategories() {
      return actionCategories;
    },
    excludedNames() {
      const allNames = [successCondition, failCondition, postCondition]
        .map((condition) => this.actions[condition]
          .filter((action, i) => action.name
            && (this.actionInProcess.position.condition !== condition
              || this.actionInProcess.position.i !== i))
          .map((action) => action.name))
        .reduce((acc, actionNames) => acc.concat(actionNames), []);

      if (!this.actions[mainCondition] || !this.actions[mainCondition].name
                || this.actionInProcess.position.condition === mainCondition) return allNames;
      return [...allNames, this.actions[mainCondition].name];
    },
    currentActionReversible() {
      const { position } = this.actionInProcess;
      if (!position) return false;
      return (this.mainActionSelected && !this.mainAction.name)
        || (!this.mainActionSelected && this.actions[position.condition].length === position.i);
    },
    saved() {
      return this.enforcement.uuid !== undefined;
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
    if (this.$refs.name) {
      this.$refs.name.focus();
    }
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
      this.enforcement = { ...this.enforcementData };
      this.selectActionMain();
    },
    async saveRun() {
      await this.saveEnforcement(this.enforcement).then(async (response) => {
        if (!this.enforcement.uuid) {
          this.enforcement.uuid = response;
        }
        await this.runEnforcement(this.enforcement.uuid);
        this.message = 'Enforcement Task is in progress';
        await this.milestoneCompleted({ milestoneName: ENFORCEMENT_EXECUTED });
      });
    },
    saveExit() {
      this.saveEnforcement(this.enforcement).then(() => this.exit());
    },
    viewTasks() {
      this.$router.push({ name: 'EnforcementTasks', params: { id: this.enforcement.uuid } });
    },
    exit() {
      this.$router.push({ name: 'Enforcements' });
    },
    selectedAction(condition) {
      if (!this.actionInProcess.position
        || this.actionInProcess.position.condition !== condition) return -1;

      return this.actionInProcess.position.i;
    },
    selectAction(condition, i) {
      this.actionInProcess.position = { condition, i };
      this.actionInProcess.definition = (this.actions[condition]
        && this.actions[condition].length > i)
        ? { ...this.actions[condition][i] }
        : { ...initAction, action: { ...initAction.action } };
      this.triggerInProcess.position = null;
    },
    selectActionMain() {
      this.actionInProcess.position = { condition: mainCondition };
      this.actionInProcess.definition = (this.mainAction && this.mainAction.name)
        ? { ...this.actions.main, action: { ...this.actions.main.action } }
        : { ...initAction, action: { ...initAction.action } };
      this.triggerInProcess.position = null;
    },
    restartAction() {
      this.selectAction(this.actionInProcess.position.condition, this.actionInProcess.position.i);
    },
    removeAction(condition, i) {
      if (this.actions[condition][i].name) {
        this.allowedActionNames.push(this.actions[condition][i].name);
      }
      this.actions[condition].splice(i, 1);
      if (condition === this.actionInProcess.position.condition) {
        this.selectAction(this.actionInProcess.position.condition, this.actionInProcess.position.i);
      }
    },
    removeActionMain() {
      if (this.actions[mainCondition].name) {
        this.allowedActionNames.push(this.actions[mainCondition].name);
      }
      this.actions[mainCondition] = null;
      if (this.mainActionSelected) {
        this.selectActionMain();
      }
    },
    selectActionType(name) {
      this.actionInProcess.definition.action.action_name = name;
      this.actionInProcess.definition.action.config = null;
    },
    saveAction() {
      if (!this.actionInProcess.position) {
        return;
      }
      const { condition } = this.actionInProcess.position;
      const { i } = this.actionInProcess.position;
      if (condition === mainCondition) {
        this.actions[condition] = this.actionInProcess.definition;
        this.selectTrigger(0);
        return;
      }
      if (this.actions[condition].length <= i) {
        this.actions[condition].push(this.actionInProcess.definition);
      } else {
        this.actions[condition][i] = this.actionInProcess.definition;
      }
      if (!this.mainAction.name) {
        this.selectActionMain();
        return;
      }
      this.selectAction(condition, i + 1);
    },
    selectTrigger(i) {
      this.actionInProcess.position = null;
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
      this.triggerInProcess.definition = { ...this.enforcement.triggers[i] };
      this.actionInProcess.position = null;
    },
    saveTrigger() {
      if (this.triggerInProcess.position === null) return;

      const { position } = this.triggerInProcess;
      if (this.triggerCount <= position) {
        this.enforcement.triggers.push(this.triggerInProcess.definition);
      } else {
        this.enforcement.triggers[position] = this.triggerInProcess.definition;
      }
      this.triggerInProcess.position = null;
      this.selectAction(successCondition, 0);
    },
  },
};
</script>

<style lang="scss">
  .x-enforcement {
    .x-split-box {
      > .main {
        display: grid;
        grid-template-rows: 48px auto 48px;
        align-items: flex-start;

        .header {
          display: grid;
          grid-template-columns: 1fr 2fr;
          grid-gap: 8px;
          align-items: center;
        }

        > .body {
          overflow: auto;
          max-height: 100%;

          .body-flow {
            display: grid;
            grid-template-rows: min-content;
            grid-gap: 24px 0;
          }
        }

        > .footer {
          text-align: right;
          align-self: end;
          display: flex;
          flex-direction: column;
        }
      }

      .details {
        .x-card {
          height: 100%;

          > .header {
            padding-bottom: 12px;
            border-bottom: 1px solid $grey-2;
          }

        }
      }
    }
  }
</style>
