<template>
  <x-modal
    v-if="action"
    size="lg"
    class="x-action-library-tip"
    @close="$emit('close')"
  >
    <div
      slot="body"
      class="body"
    >
      <div class="content">
        <template v-if="!action.implemented">
          <div><span class="title">{{ action.title }}</span> Action</div>
          <div>coming soon</div>
        </template>
        <template v-if="action.locked">
          <div>Please reach out to your Account Manager</div>
          <div>in order to add the</div>
          <div><span class="title">{{ action.title }}</span> Action</div>
        </template>
      </div>
    </div>
    <div slot="footer">
      <x-button @click="$emit('close')">OK</x-button>
    </div>
  </x-modal>
</template>

<script>
  import xModal from '../../axons/popover/Modal.vue'
  import xButton from '../../axons/inputs/Button.vue'

  export default {
    name: 'XActionLibraryTip',
    components: {
      xModal, xButton
    },
    props: {
      action: {
        type: Object,
        default: () => {}
      }
    }
  }
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

        .title {
          font-weight: 300;
          font-style: italic;
        }
      }
    }
  }
</style>