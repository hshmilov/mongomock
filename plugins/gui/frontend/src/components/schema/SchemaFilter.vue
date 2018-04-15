<template>
    <div class="filter">
        <div class="mb-4">Show only Devices:</div>
        <x-schema-expression v-for="expression, i in expressions" :key="expression.i" :first="!i"
                             v-model="expressions[i]" :fields="schema"
                             @change="compileFilter(i, $event)" @remove="removeExpression(i)"/>
        <div class="footer">
            <div @click="addExpression" class="x-btn light">+</div>
            <div v-if="error" class="error-text">{{ error }}</div>
        </div>
    </div>
</template>

<script>
	import xSchemaExpression from './SchemaExpression.vue'
    import { expression } from '../../mixins/filter'

	export default {
		name: 'x-schema-filter',
		components: {xSchemaExpression},
		props: {schema: {required: true}, value: {}, rebuild: {default: false}},
		data () {
			return {
				expressions: [...this.value],
				filters: [],
				bracketWeights: [],
				error: ''
			}
		},
		watch: {
			value (newValue) {
				if (!newValue) return
				this.expressions = [...newValue]
                if (!this.expressions.length || (this.expressions.length === 1 && !this.expressions[0].field)) {
					this.error = ''
                    this.filters = []
                }
			},
            rebuild (newRebuild) {
				if (newRebuild) {
					this.$emit('change', this.filters.join(' '))
                }
            }
		},
		methods: {
			compileFilter (index, payload) {
				if (payload.error) {
					this.error = payload.error
					this.$emit('error')
					return
				}
				this.filters[index] = payload.filter
                if (!this.filters[0]) {
					this.$emit('error')
                    return
                }
				this.bracketWeights[index] = payload.bracketWeight
				let totalBrackets = this.bracketWeights.reduce((accumulator, currentVal) => accumulator + currentVal)
				if (totalBrackets !== 0) {
					this.error = (totalBrackets < 0) ? 'Missing right bracket' : 'Missing left bracket'
					this.$emit('error')
					return
				}
				// No compilation error - propagating
				this.error = ''
				this.$emit('input', this.expressions)
				this.$emit('change', this.filters.join(' '))
			},
			addExpression () {
				this.expressions.push({...expression, i: this.expressions.length})
				this.$emit('input', this.expressions)
			},
			removeExpression (index) {
				if (index >= this.expressions.length) return
				this.expressions.splice(index, 1)
				this.filters.splice(index, 1)
				if (!index && this.expressions.length) {
					this.expressions[index].logicOp = ''
					if (this.filters.length) {
						this.filters[index] = this.filters[index].split(' ').splice(1).join(' ')
					}
				}
				this.$emit('change', this.filters.join(' '))
			}
		},
		created () {
			if (!this.expressions.length) {
				this.addExpression()
			}
		}
	}
</script>

<style lang="scss">
    .filter {
        .expression-container {
            display: grid;
            grid-template-columns: auto 20px;
            grid-column-gap: 4px;
            .link {
                text-align: center;
            }
        }
        .footer {
            display: flex;
            justify-content: space-between;
        }
    }
</style>