<template>
  <AModal
    id="enforcement_action_result"
    :visible="true"
    :closable="false"
    :centered="true"
    @cancel="onClose"
  >
    <div
      ref="modalContent"
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
              @click="onNavigateToEnforcementTasks"
            >
              {{ newTaskMessage }}
            </a>
            <span v-else>{{ newTaskMessage }}</span>
          </div>
          <XIcon
            class="enforcement-action-body__success-icon icon-success"
            type="check-circle"
            theme="filled"
          />
        </div>
      </template>
      <template v-else-if="status.error">
        <div class="t-center">
          <XIcon
            class="enforcement-action-body__error-icon icon-success"
            type="close-circle"
            theme="filled"
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
import { Modal, Spin, Icon } from 'ant-design-vue';

export default {
  name: 'XEnforcementActionResult',
  components: {
    AModal: Modal,
    ASpin: Spin,
    AIcon: Icon,
  },
  props: {
    enforcementActionToRun: {
      type: Function,
      default: () => () => {},
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
      currentEnforcementId: '',
    };
  },
  computed: {
    userCannotViewEnforcementsTasks() {
      return this.$cannot(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.View, this.$permissionConsts.categories.Tasks);
    },
    newTaskMessage() {
      return 'Enforcement task has been created successfully';
    },
    isDataLoading() {
      return this.status.processing && !this.status.error;
    },
  },
  mounted() {
    this.$nextTick(() => {
      this.$refs.modalContent.focus();
    });
    this.status.processing = true;
    this.enforcementActionToRun().then((currentEnforcementId) => {
      this.currentEnforcementId = currentEnforcementId;
      this.status.processing = false;
      this.status.success = true;
    }).catch((error) => {
      this.status.processing = false;
      this.status.error = error.message;
    });
  },
  methods: {
    onClose() {
      this.$emit('close-result');
    },
    onNavigateToEnforcementTasks() {
      this.$router.push({ path: `/enforcements/${this.currentEnforcementId}/tasks` });
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
