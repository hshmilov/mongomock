export default {
	props: {
		value: {}, views: { required: true }, entities: { required: true }
	},
	computed: {
		addBtnTitle() {
			return this.hasMaxViews? `Limited to ${this.max} queries` : ''
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
	},
	created() {
		if (Object.keys(this.value).length) {
			this.config = { ...this.value }
		}
	}
}