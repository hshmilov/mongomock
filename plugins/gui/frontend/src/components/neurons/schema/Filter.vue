<template>
    <div class="x-filter">
        <div class="title">Show only data:</div>
        <x-expression v-for="(expression, i) in expressions" :key="expression.i" :first="!i" :module="module"
                      v-model="expressions[i]" ref="expression"
                      @change="compileFilter(i, $event)" @remove="removeExpression(i)"/>
        <div class="footer">
            <div @click="addExpression" class="x-btn light">+</div>
            <div v-if="error" class="error-text">{{ error }}</div>
        </div>
    </div>
</template>

<script>
    import xExpression from './Expression.vue'
    import {expression, nestedExpression} from '../../../constants/filter'

    export default {
        name: 'x-filter',
        components: {xExpression},
        props: {module: {required: true}, value: {}},
        computed: {
            isFilterEmpty() {
                return !this.expressions.length || (this.expressions.length === 1 && !this.expressions[0].field)
            }
        },
        data() {
            return {
                expressions: [],
                filters: [],
                bracketWeights: [],
                error: '',
                rebuild: false
            }
        },
        watch: {
            value(newValue) {
                if (!newValue) return
                this.expressions = [...newValue]
                if (this.isFilterEmpty) {
                    this.error = ''
                    this.filters = []
                    this.bracketWeights = []
                }
            }
        },
        methods: {
            compileFilter(index, payload) {
                if (payload.error) {
                    this.error = payload.error
                    this.$emit('error')
                    return
                }
                if (!payload.filter) {
                    this.filters.splice(index, 1)
                } else {
                    this.filters[index] = payload.filter
                    if (!this.filters[0]) {
                        this.$emit('error')
                        return
                    }
                }
                this.bracketWeights[index] = payload.bracketWeight
                if (!this.validateBrackets()) return
                // No compilation error - can remove existing error
                this.error = ''

                if (this.rebuild) {
                    // Rebuild state is when expressions are given on initialization
                    // and filters should be updated but not passed on, in case the user edited the filter
                    if (this.filters.length === this.expressions.length) {
                        this.rebuild = false
                    }
                    return
                }
                // In ongoing update state - propagating the filter and expression values
                this.$emit('input', this.expressions)
                this.$emit('change', this.filters.join(' '))
            },
            addExpression() {
                this.expressions.push({
                    ...expression,
                    i: this.expressions.length,
                    nested: [{...nestedExpression, i: 0}]
                })
                this.$emit('input', this.expressions)
            },
            removeExpression(index) {
                if (index >= this.expressions.length) return
                this.expressions.splice(index, 1)
                this.filters.splice(index, 1)
                this.bracketWeights.splice(index, 1)
                while (index < this.expressions.length) {
                    this.expressions[index].i = index
                    index++
                }
                if (!this.validateBrackets()) return
                if (!this.expressions.length) {
                    // Expressions list should never stay empty, but have at least one empty expression
                    this.addExpression()
                } else if (this.expressions[0].logicOp) {
                    // Not ready for publishing yet, since first expression should not have a logical operation
                    return
                }
                this.$emit('change', this.filters.join(' '))
            },
            validateBrackets() {
                let totalBrackets = this.bracketWeights.reduce((accumulator, currentVal) => accumulator + currentVal, 0)
                if (totalBrackets !== 0) {
                    this.error = (totalBrackets < 0) ? 'Missing right bracket' : 'Missing left bracket'
                    this.$emit('error')
                    return false
                }
                return true
            },
            compile() {
                this.$refs.expression.forEach((expression) => expression.compileExpression())
            }
        },
        created() {
            if (this.value && this.value.length) {
                this.expressions = [...this.value]
            }
            if (!this.expressions.length) {
                this.addExpression()
            }
            if (!this.isFilterEmpty) {
                // Filter was created with existing expressions and the filters list should be updated accordingly,
                // but final result should not be emitted since it was created externally to begin with.
                this.rebuild = true
            }
        }
    }
</script>

<style lang="scss">
    .x-filter {
        .title {
            line-height: 24px;
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