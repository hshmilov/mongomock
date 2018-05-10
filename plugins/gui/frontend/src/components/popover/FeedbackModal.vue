<template>
    <modal v-show="launch" @confirm="handleConfirm" @close="handleClose" :disabled="disabled" >
        <div slot="body" class="feedback-modal-body" @keyup.esc="handleClose">
            <template v-if="status.processing">
                <pulse-loader :loading="true" color="#26dad2"></pulse-loader>
            </template>
            <template v-else-if="status.success">
                <div class="text-center">
                    <i class="icon-checkmark2 success-icon"></i>
                    <div>{{ message }}</div>
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
                <button class="x-btn link" @click="$emit('close')">Cancel</button>
                <button class="x-btn" :class="{disabled}" @click="handleConfirm">Save</button>
            </template>
        </div>
    </modal>
</template>

<script>
	import Modal from './Modal.vue'
	import PulseLoader from 'vue-spinner/src/PulseLoader.vue'

	export default {
		name: 'feedback-modal',
		components: {Modal, PulseLoader},
		model: {
			prop: 'launch',
			event: 'change'
		},
		props: {handleSave: {required: true}, message: {default: 'Save complete'},
            launch: {default: false}, disabled: {default: false}},
		data () {
			return {
				isActive: false,
				status: {
					processing: false,
					success: false,
					error: ''
				}
			}
		},
		methods: {
			handleConfirm () {
				if (this.status.error || this.status.success || this.status.processing) { this.handleClose() }
				this.status.processing = true
				this.handleSave().then(() => {
					this.status.processing = false
					this.status.success = true
					setTimeout(() => {
                        this.$emit('change', false)
						setTimeout(() => {
							this.status.success = false
                        }, 1000)
					}, 1000)
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
        .success-icon {
            font-size: 48px;
            color: $color-success;
        }
    }
</style>