<template>
    <div class="expression">
        <!-- Choice of logical operator, available from second expression --->
        <select v-if="!first" v-model="expression.logicOp" @change="compileExpression">
            <option value="" disabled hidden>OP...</option>
            <option v-for="op, i in logicOps" :key="i" :value="op">{{ op }}</option>
        </select>
        <div v-else></div>
        <!-- Option to add '(', to negate expression and choice of field to filter -->
        <label class="btn-light checkbox-label" :class="{'active': expression.leftBracket}">
            <input type="checkbox" v-model="expression.leftBracket" @change="compileExpression">(</label>
        <label class="btn-light checkbox-label" :class="{'active': expression.not}">
            <input type="checkbox" v-model="expression.not" @change="compileExpression">NOT</label>
        <select v-model="expression.field" @change="compileExpression">
            <option value="" disabled hidden>FIELD...</option>
            <option v-for="field in fields" :key="field.name" :value="field.name">{{ field.title }}</option>
        </select>
        <!-- Choice of function to compare by and value to compare, according to chosen field -->
        <template v-if="fieldSchema.type">
            <select v-model="expression.compOp" @change="compileExpression" v-if="fieldOpsList.length">
                <option value="" disabled hidden>FUNC...</option>
                <option v-for="op, i in fieldOpsList" :key="i" :value="op">{{ op }}</option>
            </select>
            <template v-if="showValue">
                <component :is="`x-${fieldSchema.type}-edit`" class="fill"
                           :class="{'grid-span-2': !fieldOpsList.length}"
                           :schema="fieldSchema" v-model="expression.value" @input="compileExpression"></component>
            </template>
            <template v-else>
                <!-- No need for value, since function is boolean, not comparison -->
                <div></div>
            </template>
        </template>
        <template v-else><select></select><input disabled></template>
        <!-- Option to add ')' and to remove the expression -->
        <label class="btn-light checkbox-label" :class="{'active': expression.rightBracket}">
            <input type="checkbox" v-model="expression.rightBracket" @change="compileExpression">)</label>
        <div class="link" @click="$emit('remove')">x</div>
    </div>
</template>

<script>
	import Checkbox from '../Checkbox.vue'
	import xStringEdit from '../controls/string/StringEdit.vue'
	import xNumberEdit from '../controls/numerical/NumberEdit.vue'
	import xIntegerEdit from '../controls/numerical/IntegerEdit.vue'
	import xBoolEdit from '../controls/boolean/BooleanEdit.vue'
	import xArrayEdit from '../controls/array/ArrayFilter.vue'
	import IP from 'ip'

	export default {
		components: {
			Checkbox, xStringEdit,
			xNumberEdit,
			xIntegerEdit,
			xBoolEdit,
			xArrayEdit
		},
		name: 'x-schema-expression',
		props: {value: {}, fields: {required: true}, compOps: {required: true}, first: {default: false}},
		computed: {
			logicOps () {
				return ['and', 'or']
			},
			fieldMap () {
				return this.fields.reduce((map, item) => {
					map[item.name] = item
					return map
				}, {})
			},
			fieldSchema () {
				if (!this.expression.field || !this.fieldMap[this.expression.field]) return {}

				return this.fieldMap[this.expression.field]
			},
			fieldOps () {
				if (!this.fieldSchema) return {}

				if (this.fieldSchema.enum) {
					return this.compOps['enum'] || {}
				}
				if (this.fieldSchema.format) {
					return this.compOps[this.fieldSchema.format] || {}
				}
				if (this.fieldSchema.type) {
					return this.compOps[this.fieldSchema.type] || {}
				}
				return {}
			},
			fieldOpsList () {
				return Object.keys(this.fieldOps)

            },
            showValue() {
				return this.fieldSchema.format === 'predefined'
                    || (this.expression.compOp && this.fieldOpsList.length && this.fieldOps[this.expression.compOp]
                        && this.fieldOps[this.expression.compOp].pattern.includes('{val}'))
            }
		},
		data () {
			return {
				expression: {...this.value},
                processedValue: ''
			}
		},
		methods: {
			checkErrors () {
				if (!this.first && !this.expression.logicOp) {
					return 'Logical operator is needed to add expression to the filter'
				} else if (!this.expression.field) {
					return 'A field to check is needed to add expression to the filter'
				} else if (!this.expression.compOp && this.fieldOpsList.length) {
					return 'Comparison operator is needed to add expression to the filter'
				} else if (this.showValue && !this.expression.value) {
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
					if (!exists || !exists.length) this.expression.value = ''
				}
				return ''
			},
			composeCondition () {
				let cond = '{val}'
				let selectedOp = this.fieldOps[this.expression.compOp]
				if (selectedOp && selectedOp.pattern && selectedOp.notPattern) {
					cond = (this.expression.not) ? selectedOp.notPattern : selectedOp.pattern
					cond = cond.replace(/{field}/g, this.expression.field)
				} else if (this.fieldOpsList.length) {
					this.expression.compOp = ''
                    this.expression.value = ''
					return ''
				}

				let val = this.processedValue? this.processedValue : this.expression.value
				let iVal = Array.isArray(val) ? -1 : undefined
				return cond.replace(/{val}/g, () => {
					if (iVal === undefined) return val
					iVal = (iVal + 1) % val.length
					return val[iVal]
				})
			},
			compileExpression () {
				this.$emit('input', this.expression)
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
				if (this.expression.not) {}
				this.$emit('change', {filter: filterStack.join(''), bracketWeight})
			}
		}
	}
</script>

<style lang="scss">
    @import '../../scss/config';

    .expression {
        display: grid;
        grid-template-columns: 60px 30px 30px 180px 90px 200px 30px 30px;
        grid-template-rows: 40px;
        justify-items: start;
        align-items: center;
        grid-gap: 8px;
        margin-bottom: 20px;
        .grid-span-2 {
            grid-column-end: span 2;
        }
        .grid-span-2 {
            grid-column-end: span 2;
        }
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
        .btn-light {
            input {
                display: none;
            }
            &.active {
                background-color: #555;
                color: $border-color;
            }
        }
        .link {
            margin: auto;
        }
    }
</style>