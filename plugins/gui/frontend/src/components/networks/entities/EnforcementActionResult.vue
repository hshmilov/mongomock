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
              id="task_link"
              @click="onNavigateToEnforcementTasks"
            >
              {{ newTaskMessage }}
            </a>
            <span v-else>{{ newTaskMessage }}</span>
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
import { Modal, Spin, Icon } from 'ant-design-vue';
import XIcon from '@axons/icons/Icon';
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
    this.$refs.wrapper_div.focus();
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
