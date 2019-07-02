<template>
  <x-page
    class="x-enforcement"
    :breadcrumbs="[
      { title: 'enforcement center', path: { name: 'Enforcements'}},
      { title: name }]"
  >
    <x-split-box>
      <template slot="main">
        <div class="header">
          <label>Enforcement Set Name</label>
          <input
            v-if="id === 'new'"
            id="enforcement_name"
            ref="name"
            v-model="enforcement.name"
            :disabled="isReadOnly"
            @input="onNameInput"
          >
          <input
            v-else
            :value="enforcement.name"
            disabled
          >
        </div>
        <div class="body">
          <div class="body-flow">
            <x-action
              id="main_action"
              v-bind="mainAction"
              @click="selectActionMain"
              @remove="removeActionMain"
            />
            <x-action-group
              v-for="item in successiveActions"
              :key="item.condition"
              v-bind="item"
              @select="selectAction"
              @remove="removeAction"
            />
            <x-trigger
              id="trigger"
              :title="trigger.name"
              :selected="trigger.selected"
              @click="selectTrigger(0)"
            />
          </div>
        </div>
        <div class="footer">
          <div class="error-text">
            {{ error }}
          </div>
          <div>
            <x-button
              v-if="saved"
              emphasize
              @click="viewTasks"
            >View Tasks</x-button>
            <x-button
              v-if="isReadOnly"
              @click="exit"
            >Exit</x-button>
            <template v-else>
              <x-button
                emphasize
                :disabled="disableRun"
                @click="saveRun"
              >Save & Run</x-button>
              <x-button
                id="enforcement_save"
                :disabled="disableSave"
                @click="saveExit"
              >Save & Exit</x-button>
            </template>
          </div>
        </div>
      </template>
      <x-card
        v-if="trigger.selected"
        slot="details"
        key="triggerConf"
        title="Trigger Configuration"
        logo="adapters/axonius"
      >
        <x-trigger-config
          v-model="triggerInProcess.definition"
          :read-only="isReadOnly"
          @confirm="saveTrigger"
        />
      </x-card>
      <x-card
        v-else-if="currentActionName"
        slot="details"
        key="actionConf"
        :title="actionConfTitle"
        :logo="actionConfLogo"
        :reversible="currentActionReversible"
        @back="restartAction"
      >
        <x-action-config
          v-model="actionInProcess.definition"
          :exclude="excludedNames"
          :include="allowedActionNames"
          :read-only="isReadOnly"
          @confirm="saveAction"
        />
      </x-card>
      <x-card
        v-else-if="actionInProcess.position"
        slot="details"
        key="actionLib"
        title="Action Library"
        logo="adapters/axonius"
      >
        <x-action-library
          :categories="actionCategories"
          @select="selectActionType"
        />
      </x-card>
    </x-split-box>
    <x-toast v-if="message" v-model="message" />
  </x-page>
</template>

<script>
  import xPage from '../axons/layout/Page.vue'
  import xSplitBox from '../axons/layout/SplitBox.vue'
  import xCard from '../axons/layout/Card.vue'
  import xButton from '../axons/inputs/Button.vue'
  import xTrigger from '../networks/enforcement/Trigger.vue'
  import xTriggerConfig from '../networks/enforcement/TriggerConfig.vue'
  import xAction from '../networks/enforcement/Action.vue'
  import xActionGroup from '../networks/enforcement/ActionGroup.vue'
  import xActionConfig from '../networks/enforcement/ActionConfig.vue'
  import xActionLibrary from '../networks/enforcement/ActionLibrary.vue'
  import xToast from '../axons/popover/Toast.vue'

  import { mapState, mapMutations, mapActions } from 'vuex'
  import { CHANGE_TOUR_STATE } from '../../store/modules/onboarding'
  import { UPDATE_DATA_VIEW } from '../../store/mutations'
  import {
    initRecipe, initAction, initTrigger,
    FETCH_ENFORCEMENT, SAVE_ENFORCEMENT, RUN_ENFORCEMENT,
    FETCH_SAVED_ENFORCEMENTS
  } from '../../store/modules/enforcements'

  import {
    successCondition, failCondition, postCondition, mainCondition, actionCategories, actionsMeta
  } from '../../constants/enforcement'

  export default {
    name: 'XEnforcement',
    components: {
      xPage, xSplitBox, xCard, xButton,
      xTrigger, xTriggerConfig,
      xAction, xActionGroup, xActionConfig, xActionLibrary,
      xToast
    },
    data () {
      return {
        enforcement: {},
        actionInProcess: {
          position: null, definition: null
        },
        triggerInProcess: {
          position: null, definition: null
        },
        allowedActionNames: [],
        message: ''
      }
    },
    computed: {
      ...mapState({
        enforcementData (state) {
          return state.enforcements.current.data
        },
        enforcementFetching (state) {
          return state.enforcements.current.fetching
        },
        isReadOnly (state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions.Enforcements === 'ReadOnly'
        },
        enforcementNames(state) {
          return state.enforcements.savedEnforcements.data
        }
      }),
      id () {
        return this.$route.params.id
      },
      name () {
        if (!this.enforcementData || !this.enforcementData.name) return 'New Enforcement Set'

        return this.enforcementData.name
      },
      error() {
        if (!this.enforcement.name) {
          return 'Enforcement Name is a required field'
        }
        if (!this.enforcementData.name && this.enforcementNames.includes(this.enforcement.name)) {
          return 'Name already taken by another Enforcement'
        }
        if (!this.mainAction.name) {
          return 'A Main Action is required for Enforcement'
        }
        return ''
      },
      disableSave () {
        return Boolean(this.error)
      },
      disableRun () {
        return this.disableSave || !this.trigger || !this.trigger.view || !this.trigger.view.name
      },
      actions () {
        if (!this.enforcement || !this.enforcement.actions) return { ...initRecipe }

        return this.enforcement.actions
      },
      mainAction () {
        let main = this.actions[mainCondition]
        let mainAction = {
          condition: mainCondition, key: mainCondition,
          selected: this.mainActionSelected, readOnly: this.isReadOnly,
          titlePrefix: 'action'
        }
        if (!main || !main.name) return mainAction
        return {
          ...mainAction,
          name: main.action['action_name'], title: main.name
        }
      },
      mainActionSelected () {
        return this.actionInProcess.position && this.actionInProcess.position.condition === mainCondition
      },
      successiveActions () {
        return [successCondition, failCondition, postCondition].map(condition => {
          return {
            condition,
            id: `${condition}_action`,
            selected: this.selectedAction(condition),
            items: this.actions[condition],
            readOnly: this.isReadOnly
          }
        })
      },
      actionConfTitle () {
        if (!this.currentActionName) return ''
        return `Action Library / ${actionsMeta[this.currentActionName].title}`
      },
      actionConfLogo () {
        if (!this.currentActionName) return ''
        return `actions/${this.currentActionName}`
      },
      currentActionName () {
        if (!this.actionInProcess.definition || !this.actionInProcess.definition.action
                || !this.actionInProcess.position) return ''

        return this.actionInProcess.definition.action['action_name']
      },
      trigger () {
        let selected = this.triggerInProcess.position === 0
        if (!this.enforcement.triggers || !this.enforcement.triggers.length) return { selected }
        return { ...this.enforcement.triggers[0], selected }
      },
      triggerCount () {
        if (!this.enforcement.triggers) return 0
        return this.enforcement.triggers.length
      },
      actionCategories () {
        return actionCategories
      },
      excludedNames () {
        let allNames = [successCondition, failCondition, postCondition]
                .map(condition => this.actions[condition]
                        .filter((action, i) => action.name &&
                                (this.actionInProcess.position.condition !== condition || this.actionInProcess.position.i !== i))
                        .map(action => action.name))
                .reduce((allNames, actionNames) => {
                  allNames = allNames.concat(actionNames)
                  return allNames
                }, [])

        if (!this.actions[mainCondition] || !this.actions[mainCondition].name
                || this.actionInProcess.position.condition === mainCondition) return allNames
        return [...allNames, this.actions[mainCondition].name]
      },
      currentActionReversible () {
        let position = this.actionInProcess.position
        if (!position) return false
        return (this.mainActionSelected && !Boolean(this.mainAction.name)) ||
                (!this.mainActionSelected && this.actions[position.condition].length === position.i)
      },
      saved() {
        return this.enforcement.uuid !== undefined
      }
    },
    created () {
      if (!this.enforcementFetching && (!this.enforcementData.uuid || this.enforcementData.uuid !== this.id)) {
        this.fetchEnforcement(this.id).then(() => {
          this.initData()
        })
      } else {
        this.initData()
      }
    },
    mounted () {
      if (this.$refs.name) {
        this.$refs.name.focus()
      }
      this.tour({ name: 'enforcementName' })
      if (!this.enforcementNames || !this.enforcementNames.length) {
        this.fetchSavedEnforcements()
      }
    },
    methods: {
      ...mapMutations({
        tour: CHANGE_TOUR_STATE, updateView: UPDATE_DATA_VIEW
      }),
      ...mapActions({
        fetchEnforcement: FETCH_ENFORCEMENT, saveEnforcement: SAVE_ENFORCEMENT,
        runEnforcement: RUN_ENFORCEMENT, fetchSavedEnforcements: FETCH_SAVED_ENFORCEMENTS
      }),
      initData () {
        this.enforcement = { ...this.enforcementData }
        this.selectActionMain()
      },
      saveRun () {
        this.saveEnforcement(this.enforcement).then((response) => {
          if (!this.enforcement.uuid) {
            this.enforcement.uuid = response
          }
          this.runEnforcement(this.enforcement.uuid)
          this.message = 'Enforcement Task is in progress'
        })
      },
      saveExit () {
        this.saveEnforcement(this.enforcement).then(() => this.exit())
      },
      viewTasks() {
        this.updateView({
          module: 'tasks',
          view: {
            query: {
              filter: `post_json.report_name == "${this.enforcement.name}"`
            }
          }
        })
        this.$router.push({ name: 'Tasks' })
      },
      exit () {
        this.$router.push({ name: 'Enforcements' })
      },
      selectedAction (condition) {
        if (!this.actionInProcess.position || this.actionInProcess.position.condition !== condition) return -1

        return this.actionInProcess.position.i
      },
      selectAction (condition, i) {
        this.actionInProcess.position = { condition, i }
        this.actionInProcess.definition = (this.actions[condition] && this.actions[condition].length > i) ?
                { ...this.actions[condition][i] } :
                { ...initAction, action: { ...initAction.action } }
        this.triggerInProcess.position = null
      },
      selectActionMain () {
        this.actionInProcess.position = { condition: mainCondition }
        this.actionInProcess.definition = (this.mainAction && this.mainAction.name) ?
                { ...this.actions.main, action: { ...this.actions.main.action } } :
                { ...initAction, action: { ...initAction.action } }
        this.triggerInProcess.position = null
      },
      restartAction () {
        this.selectAction(this.actionInProcess.position.condition, this.actionInProcess.position.i)
      },
      removeAction (condition, i) {
        if (this.actions[condition][i].name) {
          this.allowedActionNames.push(this.actions[condition][i].name)
        }
        this.actions[condition].splice(i, 1)
        if (condition === this.actionInProcess.position.condition) {
          this.selectAction(this.actionInProcess.position.condition, this.actionInProcess.position.i)
        }
      },
      removeActionMain () {
        if (this.actions[mainCondition].name) {
          this.allowedActionNames.push(this.actions[mainCondition].name)
        }
        this.actions[mainCondition] = null
        if (this.mainActionSelected) {
          this.selectActionMain()
        }
      },
      selectActionType (name) {
        this.actionInProcess.definition.action['action_name'] = name
        this.actionInProcess.definition.action.config = null
      },
      saveAction () {
        if (!this.actionInProcess.position) {
          return
        }
        let condition = this.actionInProcess.position.condition
        this.updateTour(condition)
        let i = this.actionInProcess.position.i
        if (condition === mainCondition) {
          this.actions[condition] = this.actionInProcess.definition
          this.selectTrigger(0)
          return
        }
        if (this.actions[condition].length <= i) {
          this.actions[condition].push(this.actionInProcess.definition)
        } else {
          this.actions[condition][i] = this.actionInProcess.definition
        }
        if (!this.mainAction.name) {
          this.selectActionMain()
          return
        }
        this.selectAction(condition, i + 1)
      },
      updateTour (condition) {
        switch (condition) {
          case mainCondition:
            this.tour({ name: 'enforcementTrigger' })
            break
          case successCondition:
            this.tour({ name: 'actionFailure' })
            break
          case failCondition:
            this.tour({ name: 'actionConstant' })
            break
          default:
            this.tour({ name: 'enforcementSave' })
        }
      },
      selectTrigger (i) {
        this.actionInProcess.position = null
        if (i === undefined || i >= this.triggerCount) {
          this.triggerInProcess.position = this.triggerCount
          this.triggerInProcess.definition = {
            ...initTrigger,
            name: 'Trigger',
            view: { ...initTrigger.view },
            conditions: { ...initTrigger.conditions }
          }
          return
        }
        this.triggerInProcess.position = i
        this.triggerInProcess.definition = { ...this.enforcement.triggers[i] }
        this.actionInProcess.position = null
      },
      saveTrigger () {
        if (this.triggerInProcess.position === null) return

        let position = this.triggerInProcess.position
        if (this.triggerCount <= position) {
          this.enforcement.triggers.push(this.triggerInProcess.definition)
        } else {
          this.enforcement.triggers[position] = this.triggerInProcess.definition
        }
        this.triggerInProcess.position = null
        this.selectAction(successCondition, 0)
        this.tour({ name: 'actionSuccess' })
      },
      onNameInput () {
        this.tour({ name: 'actionMain' })
      }
    }
  }
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