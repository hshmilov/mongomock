<template>
    <div class="expression">
        <select v-if="!first" v-model="expression.logicOp" @change="compileExpression">
            <option value="" disabled hidden>OP</option>
            <option v-for="op, i in logicOps" :key="i" :value="op">{{ op }}</option>
        </select>
        <div v-else></div>
        <label class="btn-light checkbox-label" :class="{'active': expression.not}">
            <input type="checkbox" v-model="expression.not" @change="compileExpression">NOT</label>
        <label class="btn-light checkbox-label" :class="{'active': expression.leftBracket}">
            <input type="checkbox" v-model="expression.leftBracket" @change="compileExpression">(</label>
        <select v-model="expression.field" @change="compileExpression">
            <option value="" disabled hidden>FIELD</option>
            <option v-for="field in fields" :key="field.name" :value="field.name">{{ field.title }}</option>
        </select>
        <template v-if="fieldSchema.type">
            <select v-model="expression.compOp" @change="compileExpression">
                <option value="" disabled hidden>OP</option>
                <option v-for="op, i in compOpsList" :key="i" :value="op.pattern">{{ op.name }}</option>
            </select>
            <component :is="`x-${fieldSchema.type}-edit`" class="fill" :schema="fieldSchema"
                       v-model="expression.value" @input="compileExpression"></component>
        </template>
        <template v-else-if="fieldSchema.name && fieldSchema.name === 'predefined'">
            <select v-model="expression.value" @change="compileExpression" class="grid-span-2">
                <option v-for="item in fieldSchema.enum" :value="item.name">{{ item.title }}</option>
            </select>
        </template>
        <template v-else><select></select><input disabled></template>
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
			fieldMap() {
				return this.fields.reduce((map, item) => {
					map[item.name] = item
                    return map
                }, {})
            },
			fieldSchema () {
				if (!this.expression.field || !this.fieldMap[this.expression.field]) return {}

                return this.fieldMap[this.expression.field]
			},
            compOpsList() {
				if (!this.fieldSchema || !this.fieldSchema.type) return []
				if (this.fieldSchema.format && this.compOps[this.fieldSchema.format]) {
					return this.compOps[this.fieldSchema.format]
                }
				if (this.compOps[this.fieldSchema.type]) {
                    return this.compOps[this.fieldSchema.type]
                }
                return this.compOps['numerical']
            }
		},
		data () {
			return {
				expression: {...this.value}
			}
		},
		methods: {
			compileExpression () {
				this.$emit('input', this.expression)
                let error = ''
                if (!this.first && !this.expression.logicOp) {
					error = 'Logical operator is needed to add expression to the filter'
				} else if (!this.expression.field) {
					error = 'A field to check is needed to add expression to the filter'
                } else if (!this.expression.compOp && this.expression.field !== 'predefined') {
					error = 'Comparison operator is needed to add expression to the filter'
                } else if (!this.expression.value) {
					error = 'A value to compare is needed to add expression to the filter'
                }
                if (error) {
					this.$emit('change', {error})
                    return
                }

                let filter = (this.expression.field === 'predefined')? this.expression.value:
                    `${this.expression.field} ${this.expression.compOp.replace('{val}', this.expression.value)}`
                let bracketWeight = 0
                if (this.expression.leftBracket) {
					filter = `(${filter}`
					bracketWeight -= 1
                }
                if (this.expression.rightBracket) {
					filter = `${filter})`
					bracketWeight += 1
                }
                if (this.expression.not) {

                }
                if (this.expression.logicOp) {
					filter = `${this.expression.logicOp} ${filter}`
                }
				this.$emit('change', {filter, bracketWeight})
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
        .fill {
            width: 100%;
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