<template>
    <div class="expression">
        <!-- Choice of logical operator, available from second expression --->
        <x-select v-if="!first" :options="logicOps" placeholder="op..." v-model="expression.logicOp" class="x-select-logic"/>
        <div v-else></div>
        <!-- Option to add '(', to negate expression and choice of field to filter -->
        <label class="x-btn light checkbox-label expression-bracket-left" :class="{'active': expression.leftBracket}">
            <input type="checkbox" v-model="expression.leftBracket">(</label>
        <label class="x-btn light checkbox-label" :class="{active: expression.not, disabled: disableNot}">
            <input type="checkbox" v-model="expression.not">NOT</label>
        <x-select-typed-field :fields="fields" v-model="expression.field" :id="first? 'query_field': undefined" />
        <!-- Choice of function to compare by and value to compare, according to chosen field -->
        <template v-if="fieldSchema.type">
            <x-select :options="fieldOpsList" v-model="expression.compOp" v-if="fieldOpsList.length"
                      placeholder="func..." :id="first? 'query_op': undefined" class="x-select-comp" />
            <template v-if="showValue">
                <component :is="valueSchema.type" :schema="valueSchema" v-model="expression.value" class="expression-value"
                           :class="{'grid-span2': !fieldOpsList.length}" :id="first? 'query_value': undefined" />
            </template>
            <template v-else>
                <!-- No need for value, since function is boolean, not comparison -->
                <div></div>
            </template>
        </template>
        <template v-else><div/><div/></template>
        <!-- Option to add ')' and to remove the expression -->
        <label class="x-btn light checkbox-label expression-bracket-right" :class="{'active': expression.rightBracket}">
            <input type="checkbox" v-model="expression.rightBracket">)</label>
        <div class="x-btn link expression-remove" @click="$emit('remove')">x</div>
    </div>
</template>

<script>
    import xSelect from '../inputs/Select.vue'
    import xSelectTypedField from '../inputs/SelectTypedField.vue'
	import string from '../controls/string/StringEdit.vue'
	import number from '../controls/numerical/NumberEdit.vue'
	import integer from '../controls/numerical/IntegerEdit.vue'
	import bool from '../controls/boolean/BooleanEdit.vue'
	import array from '../controls/array/ArrayFilter.vue'
	import IP from 'ip'
	import { compOps } from '../../constants/filter'

    import { mapMutations } from 'vuex'
	import { CHANGE_TOUR_STATE } from '../../store/modules/onboarding'

	export default {
		components: {
			xSelect, xSelectTypedField, string, number, integer, bool, array,
		},
		name: 'x-schema-expression',
		props: {
			value: {}, fields: {required: true}, first: {default: false}
		},
		computed: {
			logicOps () {
				return [{name: 'and', title: 'and'}, {name: 'or', title: 'or'}]
			},
			fieldMap () {
				return this.fields.reduce((map, item) => {
					if (item.fields) {
						item.fields.forEach((field) => {
							map[field.name] = field
                        })
					} else {
					    map[item.name] = item
                    }
					return map
				}, {})
			},
			fieldSchema () {
				if (!this.expression.field || !this.fieldMap[this.expression.field]) return {}

				return this.fieldMap[this.expression.field]
			},
			valueSchema () {
				if (this.fieldSchema && this.fieldSchema.type === 'array'
					&& ['contains', 'equals', 'subnet'].includes(this.expression.compOp)) {
					return this.fieldSchema.items
				}
                if (this.fieldSchema && this.fieldSchema.format && this.fieldSchema.format === 'date-time'
                    && ['days'].includes(this.expression.compOp)) {
					return { type: 'integer' }
                }
				return this.fieldSchema
			},
			fieldOps () {
				if (!this.fieldSchema || !this.fieldSchema.type) return {}
				let isArray = this.fieldSchema.type === 'array'
                let ops = isArray? compOps['array'] : {}
				let schema = isArray? this.fieldSchema.items : this.fieldSchema
                if (schema.enum && schema.format !== 'predefined') {
                    ops = { ...ops, equals: compOps[schema.type].equals }
                } else if (schema.format) {
                    ops = { ...ops, ...compOps[schema.format] }
                } else {
					ops = { ...ops, ...compOps[schema.type] }
                }
                if (isArray && ops.exists) {
                    ops.exists = {
                        pattern: `(${ops.exists.pattern} and {field} != [])`,
                        notPattern: `(${ops.exists.notPattern} or {field} == [])`
                    }
                }
				return ops
			},
			fieldOpsList () {
				return Object.keys(this.fieldOps).map((op ) => {
					return { name: op, title: op }
				})

			},
			showValue () {
				return this.fieldSchema.format === 'predefined'
					|| (this.expression.compOp && this.fieldOpsList.length && this.fieldOps[this.expression.compOp]
						&& this.fieldOps[this.expression.compOp].pattern.includes('{val}'))
			},
            disableNot() {
				return this.expression.field && this.expression.format === 'predefined'
            }
		},
		data () {
			return {
				expression: { ...this.value },
				processedValue: '',
                newExpression: false
			}
		},
		watch: {
			value (newValue) {
                if (newValue.field !== this.expression.field) {
                	this.expression = { ...newValue }
					this.newExpression = true
                }
            },
			valueSchema (newSchema, oldSchema) {
				if (!oldSchema.type && !oldSchema.format) return
				if (!this.newExpression && (newSchema.type !== oldSchema.type || newSchema.format !== oldSchema.format)) {
					this.expression.value = null
				}
				this.newExpression = false
			}
		},
		methods: {
            ...mapMutations({ changeState: CHANGE_TOUR_STATE }),
			checkErrors () {
				if (!this.first && !this.expression.logicOp) {
					return 'Logical operator is needed to add expression to the filter'
				} else if (!this.expression.compOp && this.fieldOpsList.length) {
					return 'Comparison operator is needed to add expression to the filter'
				} else if (this.showValue && (typeof this.expression.value !== 'number' || isNaN(this.expression.value))
                    && (!this.expression.value || !this.expression.value.length)) {
					return 'A value to compare is needed to add expression to the filter'
				}
			},
			formatExpression () {
				this.processedValue = ''
				if (this.fieldSchema.format && this.fieldSchema.format === 'ip' && this.expression.compOp === 'subnet') {
					let val = this.expression.value
					if (!val.includes('/') || val.indexOf('/') === val.length - 1) {
						return 'Specify <address>/<CIDR> to filter IP by subnet'
					}
					try {
						let subnetInfo = IP.cidrSubnet(val)
						this.processedValue = [IP.toLong(subnetInfo.networkAddress), IP.toLong(subnetInfo.broadcastAddress)]
					} catch (err) {
						return 'Specify <address>/<CIDR> to filter IP by subnet'
					}
				}
				if (this.fieldSchema.enum && this.fieldSchema.enum.length && this.expression.value) {
					let exists = this.fieldSchema.enum.filter((item) => {
						return (item.name) ? (item.name === this.expression.value) : item === this.expression.value
					})
					if (!exists || !exists.length) return 'Specify a valid value for enum field'
				}
				return ''
			},
			composeCondition () {
				let cond = '({val})'
				let selectedOp = this.fieldOps[this.expression.compOp]
				if (selectedOp && selectedOp.pattern && selectedOp.notPattern) {
					cond = (this.expression.not) ? selectedOp.notPattern : selectedOp.pattern
					cond = cond.replace(/{field}/g, this.expression.field)
				} else if (this.fieldOpsList.length) {
					this.expression.compOp = ''
					this.expression.value = ''
					return ''
				} else if (this.fieldSchema.format === 'predefined' && this.expression.not) {
					// Expression with some existing query is negated by a preceding NOT
					cond = `not ({val})`
                }

				let val = this.processedValue ? this.processedValue : this.expression.value
				let iVal = Array.isArray(val) ? -1 : undefined
				return cond.replace(/{val}/g, () => {
					if (iVal === undefined) return val
					iVal = (iVal + 1) % val.length
					return val[iVal]
				})
			},
			compileExpression () {
            	if (!this.expression.i) {
            		this.expression.logicOp = ''
                }
				if (!this.expression.compOp && !this.expression.value && this.expression.field.includes('id')) {
                    this.expression.compOp = 'exists'
                    return
                }
				this.$emit('input', this.expression)
                if (!this.expression.field) return
				let error = this.checkErrors() || this.formatExpression()
				if (error) {
					this.$emit('change', {error})
					return
				}
				let filterStack = []
				if (this.expression.logicOp) {
					filterStack.push(this.expression.logicOp + ' ')
				}
                let bracketWeight = 0
                if (this.expression.leftBracket) {
                    filterStack.push('(')
                    bracketWeight -= 1
                }
                filterStack.push(this.composeCondition())
                if (this.expression.rightBracket) {
                    filterStack.push(')')
                    bracketWeight += 1
                }
				this.$emit('change', {filter: filterStack.join(''), bracketWeight})
			}
		},
		updated () {
			this.compileExpression()
            if (this.first) {
				if (this.expression.field && this.expression.compOp && !this.expression.value) {
					this.changeState({ name: 'queryValue' })
                } else if (this.expression.field && !this.expression.compOp) {
					this.changeState({ name: 'queryOp' })
                }
            }
		},
        created() {
			if (this.expression.field) {
				this.compileExpression()
            }
        }
	}
</script>

<style lang="scss">
    .expression {
        display: grid;
        grid-template-columns: 56px 30px 30px 240px 80px auto 30px 30px;
        grid-template-rows: 40px;
        justify-items: stretch;
        align-items: center;
        grid-gap: 8px;
        margin-bottom: 20px;
        select, input:not([type=checkbox]) {
            height: 30px;
            width: 100%;
        }
        .checkbox-label {
            margin-bottom: 0;
            cursor: pointer;
            font-size: 12px;
            &::before {
                margin: 0;
            }
        }
        .x-btn.light {
            input {
                display: none;
            }
            &.disabled {
                visibility: hidden;
            }
        }
        .link {
            margin: auto;
        }
    }
</style>
