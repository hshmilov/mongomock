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
		'schema': {required: true}, 'value': {required: true}, 'apiUpload': {}
	},
	computed: {
		data: {
			get() {
				return this.value || []
			},
			set(value) {
				this.$emit('input', value)
			}
		},
		isOrderedObject() {
			return Array.isArray(this.schema.items)
		},
		processedData() {
			return this.data
		},
		schemaItems() {
			let schemaItems = []
			// Process schema to create list of items which Array components can present
			if (this.isOrderedObject) {
				// schema.items contains explicit definition for each type of contained children
				// Filter those without a 'title' property since they are not for presentation
				schemaItems = this.schema.items.filter(item => item.title)
			} else if (this.schema.items instanceof Object && this.schema.name) {
				// schema.items contains one unified definition for type of all children
				schemaItems = this.toList(this.processedData).map((item, index) => {
					// Use same unified schema and add name
					return {...this.schema.items, name: index}
				})
			} else if (!this.schema.items) {
				// schema contains one unified definition for type of all data elements (primitive containing array)
				schemaItems = this.toList(this.processedData).map((item, index) => {
					// Use same unified schema and add name
					return {...this.schema, name: index, title: undefined}
				})
			}
			schemaItems.forEach(schema => {
				if (this.isFile(schema)) {
					schema.type = 'file'
				}
				// Primitive children are required if appear in schema.required list
				if (schema.type !== 'array' || (schema.items && schema.items.type === 'string')) {
					schema.required = (this.schema.required === true ||
						(Array.isArray(this.schema.required) && this.schema.required.includes(schema.name)))
				}
				schema.filter = this.schema.filter
				if (this.schema.hyperlinks) {
					schema.hyperlinks = this.schema.hyperlinks
					if (schema.name && typeof schema.name === 'string') {
						const cleanName = schema.name.replace('specific_data.', '').replace('data.', '')
						schema.hyperlinks = cleanName? schema.hyperlinks[cleanName] : schema.hyperlinks
					}
				}
			})
			return schemaItems
		},
		dataSchemaItems() {
			const data = this.data
			return this.schemaItems.filter(item => !this.empty(data[item.name]))
		},
		isHidden() {
			return this.data['enabled'] === false
		},
		shownSchemaItems() {
			if (this.isHidden){
				return this.schemaItems.filter(x => x.name === 'enabled')
			}
			return this.schemaItems
		}
	},
	data () {
		return {
			collapsed: false
		}
	},
	methods: {
		empty (data) {
			if (data === undefined || data == null || data === '') return true
			if (typeof data !== 'object') return false
			let dataToCheck = Array.isArray(data)? data : Object.values(data)
			let hasValue = false
			dataToCheck.forEach((value) => {
				if (value !== undefined && value !== null && value !== '') {
					hasValue = true
				}
			})
			return !hasValue
		},
		toList(data) {
			if (!data) return []
			if (!Array.isArray(data)) {
				return Object.keys(data)
			}
			return data
		},
		isFile (schema) {
			return (schema.type === 'file')
		}
	}
}