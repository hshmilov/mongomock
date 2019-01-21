<template>
    <x-feedback-modal v-model="isActive" :handle-save="handleSave" :message="message" :approve-text="actionText"
                      :disabled="disabled">
        <slot></slot>
    </x-feedback-modal>
</template>

<script>
    import xFeedbackModal from '../popover/FeedbackModal.vue'

    export default {
        name: 'x-action-menu-item',
        components: {xFeedbackModal},
        props: {
            title: {
                required: true
            },
            handleSave: {
                required: true
            },
            message: {
                default: ''
            },
            actionText: {},
            disabled: false
        },
        data() {
            return {
                isActive: false
            }
        },
        methods: {
            activate() {
                this.isActive = true
            }
        }
    }
</script>

<style scoped>

</style>