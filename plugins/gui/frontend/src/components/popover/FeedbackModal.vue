<template>
    <modal v-if="launch" @confirm="handleConfirm" @close="handleClose" :disabled="disabled"
           @enter="$emit('enter')" @leave="$emit('leave')">
        <div slot="body" class="feedback-modal-body" @keyup.esc="handleClose">
            <template v-if="status.processing">
                <pulse-loader :loading="true" color="#FF7D46"></pulse-loader>
            </template>
            <template v-else-if="status.success">
                <div class="t-center">
                    <svg-icon name="symbol/success" :original="true" height="48px"></svg-icon>
                    <div class="mt-12">{{ message }}</div>
                </div>
            </template>
            <template v-else-if="status.error">
                <div class="error-text">{{ status.error }}</div>
            </template>
            <template v-else>
                <slot></slot>
            </template>
        </div>
        <div slot="footer">
            <template v-if="!status.success && !status.processing">
                <button class="x-btn link" @click="handleClose">Cancel</button>
                <button class="x-btn" :class="{disabled}" @click="handleConfirm" :id="approveId">{{ approveText }}</button>
            </template>
        </div>
    </modal>
</template>

<script>
	import Modal from './Modal.vue'
	import PulseLoader from 'vue-spinner/src/PulseLoader.vue'

	export default {
		name: 'feedback-modal',
		components: { Modal, PulseLoader },
		model: {
			prop: 'launch',
			event: 'change'
		},
		props: { handleSave: { required: true }, message: { default: 'Save complete' }, launch: { default: false },
            disabled: { default: false }, approveId: {}, approveText: { default: 'Save' } },
		data () {
			return {
				status: {
					processing: false,
					success: false,
					error: ''
				}
			}
		},
		methods: {
			handleConfirm () {
				if (this.disabled) return
				if (this.status.error || this.status.success || this.status.processing) { this.handleClose() }
				this.status.processing = true
				this.handleSave().then(() => {
					this.status.processing = false
					this.status.success = true
					setTimeout(() => {
                        this.$emit('change', false)
						setTimeout(() => {
							this.status.success = false
                        }, 2000)
					}, 100)
				}).catch((error) => {
					this.status.processing = false
					this.status.error = error.message
				})
			},
            handleClose() {
				this.$emit('change', false)
                this.status.success = false
                this.status.processing = false
                this.status.error = ''
            }
		}
	}
</script>

<style lang="scss">
    .feedback-modal-body {
        min-height: 120px;
        position: relative;
    }
</style>