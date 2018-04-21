/*
	Common functionality for array typed controls.

	Received props include:
	 - schema - parameters configuring the functionality of the array. Specifically, expected to contain 'items'
	   describing types of children, either unified for a regular array or a tuple representing an ordered object.
	 - value - data in the form of object, where keys are numbers (for a unified array) or names of items
	   (for a tuple representing an ordered object)
 */

export default {
	props: {
		'schema': {required: true}, 'value': {required: true}
	},
	computed: {
		schemaItems () {
			let schemaItems = []
			// Process schema to create list of items which Array components can present
			if (Array.isArray(this.schema.items)) {
				// schema.items contains explicit definition for each type of contained children
				schemaItems = this.schema.items.filter(item => item.title)
			} else if (this.schema.items instanceof Object && this.schema.name) {
				// schema.items contains one unified definition for type of all children
				schemaItems = this.toList(this.data).map((item, index) => {
					// Use same unified schema and add name
					return {...this.schema.items, name: index}
				})
			}
			schemaItems.forEach((schema) => {
				// An array of bytes is handled by 'file' type
				if (this.isFile(schema)) {
					schema.type = 'file'
				}
				// Primitive children are required if appear in schema.required list
				schema.required = (schema.type !== 'array' && this.schema.required
					&& this.schema.required.includes(schema.name))
			})
			return schemaItems
		}
	},
	data () {
		return {
			data: {...this.value}
		}
	},
	watch: {
		value(newValue) {
			this.data = {...newValue}
		}
	},
	methods: {
		empty (data) {
			if (data === undefined || data == null || data === '') { return true }
			if (typeof data !== 'object') { return false }
			let hasValue = false
			Object.values(data).forEach((value) => {
				if (value) { hasValue = true }
			})
			return !hasValue
		},
		toList(data) {
			if (!Array.isArray(data)) {
				return Object.keys(this.data)
			}
			return data
		},
		isFile (schema) {
			return (schema.items instanceof Object) && (schema.format === 'bytes')
		}
	}
}