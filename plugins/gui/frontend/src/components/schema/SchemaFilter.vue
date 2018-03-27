<template>
    <div class="filter">
        <div class="mb-4">Show only Devices:</div>
        <x-schema-expression v-for="expression, i in expressions" :key="expression.i" :first="!i"
                             v-model="expressions[i]" :fields="schema" :comp-ops="compOps"
                             :recompile="recompile" @recompiled="handleRecompiled"
                             @change="compileFilter(i, $event)" @remove="removeExpression(i)"/>
        <div class="footer">
            <div @click="addExpression" class="btn-light">+</div>
            <div v-if="error" class="error-text">{{ error }}</div>
        </div>
    </div>
</template>

<script>
	import xSchemaExpression from './SchemaExpression.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'

	export default {
		name: 'x-schema-filter',
		components: {xSchemaExpression},
		props: {'schema': {required: true}, 'value': {}, recompile: {default: false}},
		computed: {
			expression () {
				return {
					logicOp: '',
					not: false,
					leftBracket: false,
					field: '',
					compOp: '',
					value: null,
					rightBracket: false
				}
			},
			compOps () {
				const exists = {
					pattern: '({field} == exists(true) and {field} != "")',
					notPattern: '({field} == exists(false) or {field} == "")'
				}
				const equals = {
					pattern: '{field} == "{val}"',
					notPattern: '{field} != "{val}"'
				}
				const contains = {
					pattern: '{field} == regex("{val}", "i")',
					notPattern: '{field} == regex("^(?!.*{val})", "i")'
				}
				const numerical = {
					'equals': {pattern: '{field} == {val}', notPattern: '{field} != {val}'},
					'<': {pattern: '{field} < {val}', notPattern: '{field} >= {val}'},
					'>': {pattern: '{field} > {val}', notPattern: '{field} <= {val}'}
				}
				return {
					'array': {
						'size': {
							pattern: '{field} == size({val})',
							notPattern: 'not {field} == size({val})'
						},
						'exists': {
							pattern: '({field} == exists(true) and {field} > [])',
							notPattern: '({field} == exists(false) or {field} == [])'
						}
					},
					'date-time': {
						'<': { pattern: '{field} < date("{val}")', notPattern: '{field} >= date("{val}")' },
						'>': { pattern: '{field} > date("{val}")', notPattern: '{field} <= date("{val}")' },
                        'past days': {
							pattern: '{field} >= date("NOW - {val}d")',
                            notPattern: '{field} < date("NOW - {val}d")'
						}
					},
					'ip': {
						'subnet': {
							pattern: '({field}_raw >= {val} and {field}_raw <= {val})',
							notPattern: '({field}_raw < {val} or {field}_raw > {val})'
						},
						equals,
						'isIPv4': {
							pattern: '{field} == regex("\.")',
							notPattern: '{field} == regex("^(?!.*\.)")'
						},
						'isIPv6': {
							pattern: '{field} == regex(":")',
							notPattern: '{field} == regex("^(?!.*:)")'
						},
						exists
					},
					'string': {
						contains,
						equals,
						'starts': {
							pattern: '{field} == regex("^{val}", "i")',
							notPattern: '{field} == regex("^^(?!{val})", "i")'
						},
						'ends': {
							pattern: '{field} == regex("{val}$", "i")',
							notPattern: '{field} == regex("^(?!{val})$", "i")'
						},
						exists
					},
					'bool': {
						'true': {pattern: '{field} == true', notPattern: '{field} == false'},
						'false': {pattern: '{field} == false', notPattern: '{field} == true'}
					},
					'number': numerical,
					'integer': numerical
				}
			}
		},
		data () {
			return {
				expressions: [...this.value],
				filters: [],
				bracketWeights: [],
				error: '',
                recompiledCounter: 0
			}
		},
		watch: {
			value (newValue) {
				this.expressions = [...newValue]
			},
		},
		methods: {
			compileFilter (index, payload) {
				if (payload.error) {
					this.error = payload.error
					this.$emit('error')
					return
				}

				this.filters[index] = payload.filter
				this.bracketWeights[index] = payload.bracketWeight
				let totalBrackets = this.bracketWeights.reduce((accumulator, currentVal) => accumulator + currentVal)
				if (totalBrackets !== 0) {
					this.error = (totalBrackets < 0) ? 'Missing right bracket' : 'Missing left bracket'
					return
				}
				// No compilation error - propagating
				this.error = ''
				this.$emit('input', this.expressions)
				this.$emit('change', this.filters.join(' '))
			},
			addExpression () {
				this.expressions.push({...this.expression, i: this.expressions.length})
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
			},
            handleRecompiled() {
				if (!this.recompile) return

                this.recompiledCounter += 1
				if (this.recompiledCounter === this.expressions.length) {
					this.$emit('recompiled')
                    this.recompiledCounter = 0
				}
            }
		},
		created () {
			if (!this.expressions.length) {
				// this.addExpression()
				// this.addExpression()
			}
		}
	}
</script>

<style lang="scss">
    .filter {
        .btn-light {
            cursor: pointer;
            background-color: $border-color;
            border-radius: 4px;
            -webkit-transition: 0.2s ease-in;
            -o-transition: 0.2s ease-in;
            transition: 0.2s ease-in;
            text-align: center;
            width: 30px;
            line-height: 30px;
            height: 30px;
            &:hover {
                -webkit-box-shadow: 0px 4px 8px 0px rgba(0, 0, 0, 0.2);
                box-shadow: 0px 4px 8px 0px rgba(0, 0, 0, 0.2);
            }
        }
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