<template>
    <div class="x-chart-metric">
        <x-select-symbol :options="entities" v-model="config.entity" type="icon" placeholder="module..."/>
        <x-select :options="views[config.entity] || []" v-model="config.view" placeholder="query..." />
        <div></div><div></div>
        <x-select-typed-field :fields="fieldOptions" v-model="config.field" />
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
			}
        },
		data() {
			return {
				config: { entity: '', view: '', field: '', func: '' }
			}
		},
        methods: {
			validate() {
				this.$emit('validate', this.config.field && this.config.func)
            }
        }
	}
</script>

<style scoped>

</style>