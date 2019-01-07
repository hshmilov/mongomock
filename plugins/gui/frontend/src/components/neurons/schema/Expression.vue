<template>
    <div class="x-expression">
        <!-- Choice of logical operator, available from second expression --->
        <x-select v-if="!first" :options="logicOps" placeholder="op..." v-model="expression.logicOp"
                  class="x-select-logic"/>
        <div v-else></div>
        <!-- Option to add '(', to negate expression and choice of field to filter -->
        <label class="x-btn light checkbox-label expression-bracket-left" :class="{'active': expression.leftBracket}">
            <input type="checkbox" v-model="expression.leftBracket">(</label>
        <label class="x-btn light checkbox-label expression-not" :class="{ active: expression.not }">
            <input type="checkbox" v-model="expression.not">NOT</label>
        <label class="x-btn light checkbox-label expression-obj" :class="{ active: expression.obj }">
            <input type="checkbox" v-model="expression.obj">OBJ</label>
        <x-condition :module="module" v-model="expressionCond" :first="first" :is-parent="expression.obj"
                     @change="onChangeCondition" @error="onErrorCondition"/>

        <!-- Option to add ')' and to remove the expression -->
        <label class="x-btn light checkbox-label expression-bracket-right" :class="{'active': expression.rightBracket}">
            <input type="checkbox" v-model="expression.rightBracket">)</label>
        <div class="x-btn link expression-remove" @click="$emit('remove')">x</div>

        <template v-if="expression.obj && expression.field">
            <template v-for="(nestedExpr, i) in expression.nested">
                <div class="grid-span4"></div>
                <x-condition :module="module" v-model="nestedExpr.expression" :parent-field="expression.field"
                             @change="onChangeCondition($event, i)" @error="onErrorCondition" :key="nestedExpr.i"/>
                <button class="x-btn link condition-remove" @click="removeNestedExpression(i)">x</button>
                <div></div>
            </template>
            <div class="grid-span4"></div>
            <button class="x-btn link expression-nest" @click="addNestedExpression">+</button>
        </template>
    </div>
</template>

<script>
    import xSelect from '../../axons/inputs/Select.vue'
    import xSelectTypedField from '../inputs/SelectTypedField.vue'
    import xCondition from './Condition.vue'
    import {nestedExpression} from '../../../constants/filter'

    import {mapMutations} from 'vuex'
    import {CHANGE_TOUR_STATE} from '../../../store/modules/onboarding'


    export default {
        name: 'x-expression',
        components: {
            xSelect, xSelectTypedField, xCondition
        },
        props: {
            value: {}, module: {required: true}, first: {default: false}
        },
        computed: {
            logicOps() {
                return [{
                    name: 'and', title: 'and'
                }, {
                    name: 'or', title: 'or'
                }]
            },
            expression: {
                get() {
                    return this.value
                },
                set(expression) {
                    this.$emit('input', expression)
                }
            },
            expressionCond: {
                get() {
                    return {
                        field: this.expression.field, compOp: this.expression.compOp, value: this.expression.value
                    }
                },
                set(condition) {
                    this.expression = {
                        ...this.expression,
                        field: condition.field, compOp: condition.compOp, value: condition.value
                    }
                }
            },
            expressionField() {
                return this.expression.field
            },
            nestedExpressionCond() {
                return this.expression.nested
                    .filter(item => item.condition)
                    .map(item => item.condition)
                    .join(' and ')
            }
        },
        data() {
            return {
                condition: '',
                error: '',
                errorCondition: ''
            }
        },
        watch: {
            expressionField() {
                if (this.expression.obj) {
                    this.expression.nested = []
                    this.addNestedExpression()
                }

            }
        },
        methods: {
            ...mapMutations({changeState: CHANGE_TOUR_STATE}),
            checkErrors() {
                if (!this.first && !this.expression.logicOp) {
                    return 'Logical operator is needed to add expression to the filter'
                } else if (this.expression.obj && !this.expression.field) {
                    return 'Select an object to add nested conditions'
                }
                return ''
            },
            compileExpression() {
                if (!this.expression.i) {
                    this.expression.logicOp = ''
                }
                let error = this.errorCondition || this.checkErrors()
                if (error) {
                    this.$emit('change', {error})
                    return
                }
                if (!this.expression.field || (this.expression.obj && !this.nestedExpressionCond)) {
                    this.$emit('change', {filter: '', bracketWeight: 0})
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
                if (this.expression.not) {
                    filterStack.push('not ')
                }
                if (this.expression.obj) {
                    filterStack.push(`${this.expression.field} == match([${this.nestedExpressionCond}])`)
                } else {
                    filterStack.push(this.condition)
                }
                if (this.expression.rightBracket) {
                    filterStack.push(')')
                    bracketWeight += 1
                }
                this.$emit('change', {filter: filterStack.join(''), bracketWeight})
            },
            addNestedExpression() {
                this.expression.nested.push({...nestedExpression, i: this.expression.nested.length})
            },
            onChangeCondition(condition, nestedIndex) {
                if (nestedIndex !== undefined) {
                    this.expression.nested[nestedIndex].condition = condition
                } else {
                    this.condition = condition
                }
                this.compileExpression()
            },
            onErrorCondition(error) {
                this.errorCondition = error
            },
            removeNestedExpression(index) {
                this.expression.nested.splice(index, 1)
                if (!this.expression.nested.length) {
                    this.addNestedExpression()
                }
                this.compileExpression()
            }
        },
        updated() {
            this.compileExpression()
            if (this.first) {
                if (this.expression.field && this.expression.compOp && !this.expression.value) {
                    this.changeState({name: 'queryValue'})
                } else if (this.expression.field && !this.expression.compOp) {
                    this.changeState({name: 'queryOp'})
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
    .x-expression {
        display: grid;
        grid-template-columns: 56px 30px 30px 30px auto 30px 30px;
        grid-template-rows: 40px;
        justify-items: stretch;
        align-items: center;
        grid-gap: 8px;
        margin-bottom: 20px;

        select, input:not([type=checkbox]) {
            height: 32px;
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

        .expression-nest {
            text-align: left;
        }
    }
</style>
