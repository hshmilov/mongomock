/*
	Common functionality for primitive controls in 'edit' mode.

	Received props include:
	 - schema - parameters configuring the functionality of the control
	 - value - current value of the control (primitive object)
	 - validator - a Vue instance serving as an event bus, to dispatch events directly to ancestor

	Defined data includes:
	 - data - created from given value and emitted as an input event (implementing v-model)
	 - valid - validity state of current data. Common validity test is whether empty, if data is required by schema.

	Declared methods include:
	 - handleData - to be called on any change of data.
	   After formatting, via helper method, data is sent on a 'input' event, for v-model purposes.
	   After validating, via helper method, validity is sent, using the validator, on a 'validate' event.
	 - formatData - May be overridden by mixed components to convert formatting inferred by schema.
	 - validateData - By default, initiates the validity to true (common validity test runs after it).
	   May be overridden by mixed components to enforce formatting inferred by schema.

 */
export default {
	props: ['schema', 'value', 'validator'],
	data() {
		return {
			data: this.value,
			valid: true
		}
	},
	watch: {
		value(newValue, oldValue) {
			if (newValue !== oldValue) {
				this.data = this.value
			}
		}
	},
	methods: {
		validate() {
			if (!this.validator) { return }
			this.valid = this.checkData() && (!this.schema.required || !this.isEmpty())
			this.validator.$emit('validate', { title: this.schema.title, valid: this.valid })
		},
		input() {
			this.data = this.formatData()
			this.$emit('input', this.data)
		},
		formatData() {
			return this.data
		},
		checkData() {
			return true
		},
		isEmpty() {
			return !this.data
		}
	},
	created() {
		if (this.validator) {
			this.validator.$on('focusout', this.validate)
		}
	}
}