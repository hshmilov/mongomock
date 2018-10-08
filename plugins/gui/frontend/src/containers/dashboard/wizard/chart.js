export default {
	props: {
		value: {}, views: { required: true }, entities: { required: true }
	},
	computed: {
		addBtnTitle() {
			return this.hasMaxViews? `Limited to ${this.max} queries` : ''
		},
        hasMaxViews() {
            if (!this.max || !this.config.views) return false
            return this.config.views.length === this.max
        }
	},
	watch: {
		config: {
			handler(newConfig) {
				this.$emit('input', newConfig)
				this.validate()
			},
			deep: true
		}
	}
}