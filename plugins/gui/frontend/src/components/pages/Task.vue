<template>
  <XPage
    class="x-task"
    :breadcrumbs="breadcrumbs"
  >
    <XSplitBox>
      <template slot="main">
        <div class="header">
          <XArrayView
            :schema="taskDetailsSchema"
            :value="taskData"
          />
        </div>
        <div class="body">
          <XAction
            v-bind="mainAction"
            read-only
            @click="selectActionMain"
          />
          <XActionGroup
            v-for="item in successiveActions"
            :key="item.condition"
            v-bind="item"
            @select="selectAction"
          />
        </div>
      </template>
      <XCard
        v-if="currentActionName"
        slot="details"
        v-bind="actionResCard"
      >
        <XActionResult
          :data="actionInView.definition"
          :module="triggerView.entity"
          :view="triggerView.name"
          @click-one="runFilter"
        />
      </XCard>
    </XSplitBox>
  </XPage>
</template>

<script>
import { mapActions, mapMutations, mapState } from 'vuex';
import _get from 'lodash/get';
import XPage from '../axons/layout/Page.vue';
import XSplitBox from '../axons/layout/SplitBox.vue';
import XCard from '../axons/layout/Card.vue';
import XArrayView from '../neurons/schema/types/array/ArrayView.vue';
import XAction from '../networks/enforcement/Action.vue';
import XActionGroup from '../networks/enforcement/ActionGroup.vue';
import XActionResult from '../networks/enforcement/ActionResult.vue';

import { UPDATE_DATA_VIEW } from '../../store/mutations';
import { FETCH_TASK } from '../../store/modules/tasks';

import {
  actionsMeta,
  failCondition,
  mainCondition,
  postCondition,
  successCondition,
} from '../../constants/enforcement';

export default {
  name: 'XTask',
  components: {
    XPage,
    XSplitBox,
    XCard,
    XArrayView,
    XAction,
    XActionGroup,
    XActionResult,
  },
  computed: {
    ...mapState({
      triggerPeriods(state) {
        if (!state.constants.constants || !state.constants.constants.trigger_periods) {
          return [];
        }
        return state.constants.constants.trigger_periods;
      },
      fromEnforcementSetTaskListView() {
        return !!this.$route.params.id;
      },
      designatedEnforcementSetId() {
        return this.$route.params.id;
      },
      breadcrumbs() {
        return [
          { title: 'enforcements', path: { name: 'Enforcements' } },
          ...(this.fromEnforcementSetTaskListView ? [{ title: this.taskData['post_json.report_name'], path: { name: 'Enforcements' } }] : []),
          { title: 'tasks', path: { name: 'Tasks' } },
          { title: this.name },
        ];
      },
      taskFetching(state) {
        return state.tasks.current.fetching;
      },
      taskData(state) {
        let period = this.triggerPeriods.find((x) => x[state.tasks.current.data.period] !== undefined);
        if (period) {
          period = period[state.tasks.current.data.period];
        }
        return {
          ...state.tasks.current.data,
          period,
        };
      },
      view(state) {
        if (!this.triggerView) return {};
        return state[this.triggerView.entity].view;
      },
    }),
    id() {
      return this.$route.params.taskId;
    },
    name() {
      return (this.taskData && this.taskData.task_name) ? this.taskData.task_name : '';
    },
    enforcement() {
      return this.view.enforcement || null;
    },
    taskDetailsSchema() {
      return {
        type: 'array',
        items: [{
          name: 'started', title: 'Started', type: 'string', format: 'date-time',
        }, {
          name: 'finished', title: 'Completed', type: 'string', format: 'data-time',
        }, {
          name: 'enforcement', title: 'Enforcement Set Name', type: 'string',
        }, {
          name: 'view', title: 'Triggered Query Name', type: 'string',
        }, {
          name: 'period', title: 'Trigger Schedule', type: 'string',
        }, {
          name: 'condition', title: 'Triggered Conditions', type: 'string',
        }],
      };
    },
    taskResult() {
      if (!this.taskData) return {};
      return this.taskData.result;
    },
    mainAction() {
      if (!this.taskResult) {
        return {
          condition: 'main',
          id: 'main_action',
          titlePrefix: 'action',
        };
      }
      const mainAction = this.taskResult[mainCondition].action;
      return {
        condition: mainCondition,
        key: mainCondition,
        name: mainAction.action_name,
        title: this.taskResult[mainCondition].name,
        status: this.getStatus(mainAction),
        selected: this.actionInView.position && this.actionInView.position.condition === mainCondition,
      };
    },
    successiveActions() {
      return [successCondition, failCondition, postCondition].map((condition) => ({
        condition,
        items: !this.taskResult ? [] : this.taskResult[condition].map((item) => ({
          ...item,
          status: this.getStatus(item.action),
        })),
        selected: this.selectedAction(condition),
        readOnly: true,
      }));
    },
    currentActionName() {
      if (!this.actionInView.definition || !this.actionInView.definition.action
          || !this.actionInView.position) return '';

      return this.actionInView.definition.action.action_name;
    },
    actionResCard() {
      if (!this.currentActionName) return {};
      return {
        key: 'actionConf',
        title: `Action Library / ${actionsMeta[this.currentActionName].title}`,
        logo: `actions/${this.currentActionName}`,
      };
    },
    triggerView() {
      if (!this.taskResult || !this.taskResult.metadata || !this.taskResult.metadata.trigger) return null;

      return this.taskResult.metadata.trigger.view;
    },
  },
  data() {
    return {
      actionInView: {
        position: null, definition: null,
      },
    };
  },
  watch: {
    taskFetching() {
      if (!this.taskFetching) {
        this.initData();
      }
    },
  },
  methods: {
    ...mapActions({
      fetchTask: FETCH_TASK,
    }),
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    initData() {
      if (this.actionInView && this.actionInView.position) {
        this.selectAction(this.actionInView.position.condition, this.actionInView.position.i);
      } else {
        // always will run this
        this.selectActionMain();
      }
    },
    getStatus(action) {
      if (!action.results) return 'disabled';
      if (typeof (action.results) === 'string') return 'error';
      if (action.results.successful !== undefined) {
        return action.results.successful ? 'success' : 'error';
      }

      const successCount = action.results.successful_entities.length;
      const failureCount = action.results.unsuccessful_entities.length;
      if (!failureCount && !successCount) return 'disabled';
      const ratio = successCount / (failureCount + successCount);
      if (ratio === 1) return 'success';
      if (ratio < 0.5) return 'error';
      return 'warning';
    },
    selectAction(condition, i) {
      this.actionInView.position = { condition, i };
      this.actionInView.definition = this.taskResult[condition][i];
    },
    selectActionMain() {
      this.actionInView.position = { condition: mainCondition };
      this.actionInView.definition = this.taskResult.main;
    },
    selectedAction(condition) {
      if (!this.actionInView.position || this.actionInView.position.condition !== condition) return -1;

      return this.actionInView.position.i;
    },
    runFilter(index) {
      const success = index === 0 ? 'successful_entities' : 'unsuccessful_entities';
      let outcome = success.split('_')[0];
      outcome = `${outcome[0].toUpperCase()}${outcome.slice(1)}`;
      const action = this.actionInView.definition.name;
      const task = this.taskData.result.metadata.pretty_id;

      const i = this.actionInView.position.i || 0;
      const { condition } = this.actionInView.position;
      const filter = `exists_in(${task}, ${condition}, ${i}, ${success})`;

      this.updateView({
        module: this.triggerView.entity,
        view: {
          ...this.view,
          enforcement: {
            id: this.id,
            name: this.name,
            action,
            task,
            outcome,
            filter,
          },
          query: {
            expressions: [],
            filter,
          },
        },
        selectedView: null,
      });
      this.$router.push({ path: `/${this.triggerView.entity}` });
    },
  },
  mounted() {
    if (!this.taskFetching && (!this.taskData.name || this.taskData.uuid !== this.id)) {
      this.fetchTask(this.id);
    } else if (this.taskData.name) {
      this.initData();
    }
  },
};
</script>

<style lang="scss">
    .x-task {
        .main {
            height: 100%;
            display: grid;
            grid-template-rows: min-content auto;
            grid-gap: 36px 0;

            .header {
                padding-bottom: 24px;
                border-bottom: 1px solid rgba($theme-orange, 0.2);
            }

            .body {
                display: grid;
                grid-auto-rows: min-content;
                grid-gap: 24px 0;
                overflow: auto;
            }
        }

        .details {
            .x-card {
                height: 100%;

                .x-action-result {
                    height: calc(100% - 72px);
                }
            }
        }

        .array {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-gap: 12px;
        }
    }
</style>
