<template>
    <div class="filter">
        <div class="mb-4">Show only Devices:</div>
        <x-schema-expression v-for="expression, i in expressions" :key="expression.i" :first="!i"
                             v-model="expressions[i]" :fields="fields" :comp-ops="compOps"
                             @change="compileFilter(i, $event)" @remove="removeExpression(i)"></x-schema-expression>
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
		props: {'schema': {required: true}, 'value': {}},
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
			fields () {
				return this.spreadSchema(this.schema)
			},
			compOps () {
				return {
					'date-time': {
						'<': {pattern: '{field} < date("{val}")'},
						'>=': {pattern: '{field} >= date("{val}")'}
                    },
                    'ip': {
						'subnet': {pattern: '({field}_raw >= {val} and {field}_raw <= {val})'},
						'contains': {pattern: '{field} == regex("{val}")'},
                        'isIPv4': {pattern: '{field} == regex("\.")'},
						'isIPv6': {pattern: '{field} == regex(":")'}
                    },
                    'array': {
						'size': {pattern: '{field} == size({val})'},
                        'exists': {pattern: '{field} == exists(true) and {field} > []'}
					},
					'string': {
						'contains': {pattern: '{field} == regex("{val}", "i")'},
						'starts': {pattern: '{field} == regex("^{val}", "i")'},
						'ends': {pattern: '{field} == regex("{val}$", "i")'},
						'equals': {pattern: '{field} == "{val}"'},
                        'exists': {pattern: '{field} == exists(true) and {field} != ""'}
					},
                    'bool': {
						'true': {pattern: '{field} == true'},
                        'false': {pattern: '{field} == false'}
					},
					'numerical': {
						'==': {pattern: '{field} == {val}'},
						'<=': {pattern: '{field} <= {val}'},
						'>=': {pattern: '{field} >= {val}'},
						'>': {pattern: '{field} > {val}'},
						'<': {pattern: '{field} < {val}'}
					}
				}
			}
		},
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
				if (newValue.length === this.expressions.length) return
				this.expressions = [ ...newValue ]
            },
			expressions (newExpressions) {
				this.$emit('input', newExpressions)
			}
		},
		methods: {
			spreadSchema (schema, name='') {
				/*
				    Recursion over schema to extract a flat map from field path to its schema
				 */
				if (schema.name) {
					name = name? `${name}.${schema.name}` : schema.name
				}
				if (schema.type === 'array' && schema.items) {
					if (!Array.isArray(schema.items)) {
						let children = this.spreadSchema(this.fixTitle({ ...schema.items}, schema), name)
						if (schema.items.type !== 'array') {
							return children
                        }
						return [ {...schema, name}, ...children ]
					}
					let fields = []
					schema.items.forEach((item) => {
						fields = fields.concat(this.spreadSchema({ ...item }, name))
					})
					return fields
				}
				if (schema.type === 'object' && schema.properties) {
					let fields = []
					Object.keys(schema.properties).forEach((key) => {
						fields = fields.concat(this.spreadSchema({...schema.properties[key], name: key}, name))
					})
                    return fields
				}
				return [{ ...schema, name}]
			},
            fixTitle(child, parent) {
				if (!child.title) {
					child.title = ''
				}
				if (parent.title) {
					child.title = `${parent.title} ${child.title}`
				}
				return child
            },
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
				this.$emit('change', this.filters.join(' '))
			},
			addExpression () {
				this.expressions.push({ ...this.expression, i: this.expressions.length })
				this.$emit('input', this.expressions)
			},
            removeExpression(index) {
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
        created() {
			if (!this.expressions.length) {
				this.addExpression()
                this.addExpression()
            }
        }
	}
</script>

<style lang="scss">
    @import '../../scss/config';

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