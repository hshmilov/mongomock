<template>
    <feedback-modal v-model="isActive" :handle-save="handleSave" :message="message">
        <slot></slot>
    </feedback-modal>
</template>

<script>
    import FeedbackModal from '../../components/popover/FeedbackModal.vue'
	export default {
		name: 'x-data-action-modal',
        components: { FeedbackModal },
        props: {title: {required: true}, handleSave: {required: true}, message: {default: ''}},
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