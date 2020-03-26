<template>
  <AModal
    :visible="active"
    :title="title"
    :closable="false"
    :width="null"
    :class="`w-${size}`"
    :centered="true"
    @cancel="handleDismiss"
  >
    <slot />
    <template slot="footer">
      <XButton
        link
        @click="handleDismiss"
      >
        {{ dismissText }}
      </XButton>
      <XButton
        type="primary"
        @click="handleApprove"
      >
        {{ approveText }}
      </XButton>
    </template>
  </AModal>
</template>

<script>
import XButton from '../inputs/Button.vue';

export default {
  name: 'XModal',
  components: {
    XButton,
  },
  props: {
    approveText: { default: 'OK', type: String },
    dismissText: { default: 'Cancel', type: String },
    size: { default: 'xl', type: String },
    title: { default: '', type: String },
    active: { default: false, type: Boolean },
  },
  data() {
    return {
    };
  },
  methods: {
    handleApprove() {
      this.$emit('approve');
    },
    handleDismiss() {
      this.$emit('dismiss');
    },
  },
};
</script>

<style lang="scss">
    .ant-modal {
        &.w-xl {
          width: 770px;
        }
        .ant-modal-header {
            border-bottom: unset;
        }
        .ant-modal-body {
            padding: 0 24px;
        }
        .ant-modal-footer {
            border-top: unset;
        }
    }
</style>
