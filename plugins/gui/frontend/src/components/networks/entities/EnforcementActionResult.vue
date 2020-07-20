<template>
  <AModal
    id="enforcement_action_result"
    :visible="true"
    :cancel-button-props="{ props: { type: 'link' } }"
    :closable="false"
    :centered="true"
    @cancel="onClose"
  >
    <div
      ref="wrapper_div"
      class="enforcement-action-body"
      :tabindex="-1"
      @keyup.enter.stop.prevent="onClose"
    >
      <template v-if="isDataLoading">
        <ASpin
          size="large"
          class="loading-spinner"
        >
          <AIcon
            slot="indicator"
            type="loading"
          />
        </ASpin>
      </template>
      <template v-else-if="status.success">
        <div class="t-center">
          <div class="mt-12 navigate-task-link">
            <a
              v-if="!userCannotViewEnforcementsTasks"
              @click="onNavigateToNewTask"
            >
              {{ newTaskName }}
            </a>
            <span v-else>Task has been created successfully</span>
          </div>
          <XIcon
            class="enforcement-action-body__success-icon"
            family="symbol"
            type="success"
          />
        </div>
      </template>
      <template v-else-if="status.error">
        <div class="t-center">
          <XIcon
            class="enforcement-action-body__error-icon"
            family="symbol"
            type="error"
          />
          <div class="mt-12">
            {{ status.error }}
          </div>
        </div>
      </template>
    </div>
    <template #footer>
      <XButton
        type="primary"
        @click="onClose"
      >
        Close
      </XButton>
    </template>
  </AModal>
</template>

<script>
import { mapMutations, mapState, mapActions } from 'vuex';
import _get from 'lodash/get';
import { Modal, Spin, Icon } from 'ant-design-vue';
import XIcon from '@axons/icons/Icon';
import { SET_ENFORCEMENT } from '@store/modules/enforcements';
import { FETCH_ALL_TASKS } from '@store/modules/tasks';
import XButton from '@axons/inputs/Button.vue';

export default {
  name: 'XEnforcementActionResult',
  components: {
    AModal: Modal,
    ASpin: Spin,
    AIcon: Icon,
    XButton,
    XIcon,
  },
  props: {
    enforcementActionToRun: {
      type: Function,
      default: () => () => {},
      required: true,
    },
    enforcementName: {
      type: String,
      default: '',
      required: true,
    },
  },
  data() {
    return {
      status: {
        processing: false,
        success: false,
        error: '',
      },
    };
  },
  computed: {
    ...mapState({
      allTasks(state) {
        return _get(state, 'tasks.content.data', []);
      },
      userCannotViewEnforcementsTasks() {
        return this.$cannot(this.$permissionConsts.categories.Enforcements,
          this.$permissionConsts.actions.View, this.$permissionConsts.categories.Tasks);
      },
      newTaskId() {
        const newTask = this.allTasks.filter((task) => task && task['post_json.report_name']
           && task['post_json.report_name'].startsWith(this.enforcementName))
          .sort((a, b) => (new Date(b.date_fetched) - new Date(a.date_fetched)))[0];
        return newTask ? newTask.uuid : '';
      },
      newTaskName() {
        return `${this.enforcementName} - Task ${this.allTasks.length} has been created successfully`;
      },
      isDataLoading() {
        return (this.status.processing
          || (!this.newTaskId && !this.userCannotViewEnforcementsTasks)) && !this.status.error;
      },
    }),
  },
  mounted() {
    this.$refs.wrapper_div.focus();
    this.status.processing = true;
    this.enforcementActionToRun().then(() => {
      // Fetching tasks to calculate new task value only if user can view tasks
      if (!this.userCannotViewEnforcementsTasks) {
        this.fetchAllTasks();
      }
      // Reset the current enforcement data (it might be used later so must clean it)
      this.setEnforcement();
      this.status.processing = false;
      this.status.success = true;
    }).catch((error) => {
      this.status.processing = false;
      this.status.error = error.message;
    });
  },
  methods: {
    ...mapActions({
      fetchAllTasks: FETCH_ALL_TASKS,
    }),
    ...mapMutations({
      setEnforcement: SET_ENFORCEMENT,
    }),
    onClose() {
      this.$emit('close-result');
    },
    onNavigateToNewTask() {
      this.$router.push({ path: `/tasks/${this.newTaskId}` });
    },
  },
};
</script>

<style lang="scss">
  .enforcement-action-body {
    min-height: 120px;
    padding: 24px 24px 0;
    margin-bottom: 24px;
    &__success-icon, &__error-icon {
      font-size: 48px;
    }
    .loading-spinner {
        position: absolute;
        left: 50%;
        top: 50%;
        -webkit-transform: translate(-50%, -50%);
        transform: translate(-50%, -50%);
        margin: auto;
        color: $theme-orange;
    }
    .navigate-task-link {
      padding-bottom: 8px;
    }
  }
</style>
