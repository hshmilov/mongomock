<template>
  <AModal
    visible
    centered
    :closable="false"
    dialog-class="x-action-library-tip"
    @cancel="$emit('close')"
  >
    <div
      class="body"
    >
      <div class="content">
        <template v-if="!action.implemented">
          <div><span class="action-title">{{ action.title }}</span> Action</div>
          <div>coming soon</div>
        </template>
        <template v-if="action.locked">
          <div>Please reach out to your Account Manager</div>
          <div>in order to add the</div>
          <div><span class="action-title">{{ action.title }}</span> Action</div>
        </template>
      </div>
    </div>
    <div slot="footer">
      <XButton
        type="primary"
        @click="$emit('close')"
      >OK</XButton>
    </div>
  </AModal>
</template>

<script>
import { Modal } from 'ant-design-vue';

export default {
  name: 'XActionLibraryTip',
  components: {
    AModal: Modal,
  },
  props: {
    action: {
      type: Object,
      default: () => ({}),
    },
  },
};
</script>

<style lang="scss">
  .x-action-library-tip {
    .body {
      display: flex;
      flex-direction: column;
      justify-content: center;

      .content {
        text-align: center;
        margin-top: 12px;
        font-size: 20px;
        line-height: 30px;

        .action-title {
          font-weight: 300;
          font-style: italic;
        }
      }
    }
  }
</style>
