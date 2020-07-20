<template>
  <XModal
    v-if="launch"
    :disabled="disabled"
    @confirm="handleConfirm"
    @close="handleClose"
    @enter="$emit('enter')"
    @leave="$emit('leave')"
  >
    <div
      slot="body"
      class="feedback-modal-body"
      @keyup.esc="handleClose"
    >
      <template v-if="status.processing">
        <PulseLoader
          :loading="true"
          color="#FF7D46"
        />
      </template>
      <template v-else-if="status.success">
        <div class="t-center">
          <XIcon
            class="feedback-modal-body__success-icon"
            family="symbol"
            type="success"
          />
          <div class="mt-12">
            {{ message }}
          </div>
        </div>
      </template>
      <template v-else-if="status.error">
        <div class="t-center">
          <XIcon
            class="feedback-modal-body__error-icon"
            family="symbol"
            type="error"
          />
          <div class="mt-12">
            {{ status.error }}
          </div>
        </div>
      </template>
      <template v-else>
        <slot />
      </template>
    </div>
    <div slot="footer">
      <template v-if="!status.success && !status.processing && !status.error">
        <div class="text">
          <slot name="note" />
        </div>
        <XButton
          id="feedback_modal_cancel"
          type="link"
          @click="handleClose"
        >Cancel</XButton>
        <XButton
          :id="approveId"
          type="primary"
          :disabled="disabled"
          @click="handleConfirm"
        >{{ approveText }}</XButton>
      </template>
      <template v-else-if="!status.success && !status.processing && status.error">
        <div class="text">
          <slot name="note" />
        </div>
        <XButton
          type="primary"
          @click="handleClose"
        >Close</XButton>
      </template>
    </div>
  </XModal>
</template>

<script>
import XIcon from '@axons/icons/Icon';
import PulseLoader from 'vue-spinner/src/PulseLoader.vue';
import XButton from '../../axons/inputs/Button.vue';
import XModal from '../../axons/popover/Modal/index.vue';

export default {
  name: 'XFeedbackModal',
  components: {
    XButton,
    XModal,
    PulseLoader,
    XIcon,
  },
  model: {
    prop: 'launch',
    event: 'change',
  },
  props: {
    handleSave: { required: true },
    message: { default: 'Save complete' },
    launch: { default: false },
    disabled: { default: false },
    approveId: {},
    approveText: { default: 'Save' },
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
  methods: {
    handleConfirm() {
      if (this.status.error || this.status.success || this.status.processing) {
        this.handleClose();
      }
      this.status.processing = true;
      this.handleSave().then(() => {
        this.status.processing = false;
        this.status.success = true;
        setTimeout(() => {
          this.$emit('change', false);
          setTimeout(() => {
            this.status.success = false;
          }, 800);
        }, 600);
      }).catch((error) => {
        this.status.processing = false;
        this.status.error = error.message;
      });
    },
    handleClose() {
      this.$emit('change', false);
      this.status.success = false;
      this.status.processing = false;
      this.status.error = '';
    },
  },
};
</script>

<style lang="scss">
    .feedback-modal-body {
        min-height: 120px;
        &__success-icon, &__error-icon {
          font-size: 48px;
        }
        .v-spinner {
          position: static;
        }
    }
    .modal-footer {
        .text {
            font-style: italic;
            display: inline-block;
        }
    }
</style>
