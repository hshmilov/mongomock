<template>
  <x-feedback-modal
    v-model="isActive"
    :handle-save="handleSave"
    :message="message"
    :approve-text="actionText"
    :disabled="disabled"
    @change="handleChange"
  >
    <slot />
  </x-feedback-modal>
</template>

<script>
  import xFeedbackModal from '../popover/FeedbackModal.vue'

  export default {
    name: 'XActionMenuItem',
    components: { xFeedbackModal },
    props: {
      title: {
        type: String,
        required: true
      },
      handleSave: {
        type: Function,
        required: true
      },
      handleClose: {
        type: Function,
        default: undefined
      },
      message: {
        type: String,
        default: ''
      },
      actionText: {
        type: String,
        default: ''
      },
      disabled: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        isActive: false
      }
    },
    methods: {
      activate () {
        this.isActive = true
      },
      handleChange (active) {
        if (!active && this.handleClose !== undefined) {
          this.handleClose()
        }
      }
    }
  }
</script>

<style>

</style>