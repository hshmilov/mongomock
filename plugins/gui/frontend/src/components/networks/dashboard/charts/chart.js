export default {
	props: {
		value: {},
		entities: { required: true },
		views: { required: true },
		chartView: { required: true },
	},
	computed: {
		config: {
			get () {
				if (this.value) return this.value
				return { ...this.initConfig }
			},
			set (newConfig) {
				this.$emit('input', newConfig)
				this.$nextTick(this.validate)
			}
		}
	},
    methods: {
        updateView(view) {
        },
    },
}
