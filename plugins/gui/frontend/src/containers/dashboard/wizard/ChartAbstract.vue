<template>
    <div class="x-chart-metric">
        <x-select-symbol :options="entities" v-model="config.entity" type="icon" placeholder="module..."/>
        <x-select :options="views[config.entity] || []" :searchable="true" v-model="config.view"
                  placeholder="query (or empty for all)" />
        <div></div><div></div>
        <x-select-typed-field :fields="fieldOptions" :value="config.field.name" @input="updateField" />
        <div></div><div></div>
        <x-select :options="funcOptions" v-model="config.func" placeholder="function..." />
    </div>
</template>

<script>
	import xSelect from '../../../components/inputs/Select.vue'
	import xSelectSymbol from '../../../components/inputs/SelectSymbol.vue'
	import xSelectTypedField from '../../../components/inputs/SelectTypedField.vue'
	import ChartMixin from './chart'

	export default {
		name: 'x-chart-abstract',
		components: { xSelect, xSelectSymbol, xSelectTypedField },
        mixins: [ ChartMixin ],
		props: { fields: { required: true }},
        computed: {
			funcOptions() {
				return [
                    { name: 'average', title: 'Average'},
					{ name: 'count', title: 'Count'}
                ]
            },
			fieldOptions() {
				if (!this.config.entity || !this.fields[this.config.entity]) return []
				return this.fields[this.config.entity].map(category => {
					return { ...category, fields: category.fields.filter(field => {
						return !field.branched && field.type !== 'array' &&
                            (this.config.func !== 'average' || field.type === 'number' || field.type === 'integer')
					})}
				})
			},
            fieldMap() {
				return this.fieldOptions.reduce((map, item) => {
					if (item.fields) {
						item.fields.forEach((field) => {
							map[field.name] = field
						})
					} else {
						map[item.name] = item
					}
					return map
				}, {})
            }
        },
		data() {
			return {
				config: { entity: '', view: '', field: { name: '' }, func: '' }
			}
		},
        methods: {
			updateField(fieldName) {
				this.config.field = this.fieldMap[fieldName]
            },
			validate() {
				this.$emit('validate', this.config.field.name && this.config.func)
            }
        }
	}
</script>

<style scoped>

</style>