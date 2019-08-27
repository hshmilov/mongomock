<template>
  <div class="x-filter">
    <div class="title">Show only data:</div>
    <x-expression
      v-for="(expression, i) in expressions"
      :key="expression.i"
      ref="expression"
      v-model="expressions[i]"
      :first="!i"
      :module="module"
      :rebuild="rebuild"
      @change="(filter) => compileFilter(i, filter)"
      @remove="() => removeExpression(i)"
    />
    <div class="footer">
      <x-button
        light
        @click="addExpression"
      >+</x-button>
      <div
        v-if="error"
        class="error-text"
      >{{ error }}</div>
    </div>
  </div>
</template>

<script>
  import xExpression from './Expression.vue'
  import xButton from '../../axons/inputs/Button.vue'
  import { expression, nestedExpression } from '../../../constants/filter'
  import { calcMaxIndex } from '../../../constants/utils'

  export default {
    name: 'XFilter',
    components: { xExpression, xButton },
    props: {
      module: {
        type: String,
        required: true
      },
      value: {
        type: Array,
        default: () => []
      }
    },
    data () {
      return {
        filters: [],
        bracketWeights: [],
        error: '',
        rebuild: false
      }
    },
    computed: {
      expressions: {
        get () {
          return this.value
        },
        set (expressions) {
          this.$emit('input', expressions)
        }
      },
      isFilterEmpty () {
        return !this.expressions.length || (this.expressions.length === 1 && !this.expressions[0].field)
      },
      calculateI () {
        return calcMaxIndex(this.expressions)
      }
    },
    created () {
      if (!this.expressions.length) {
        this.addExpression()
      }
      if (!this.isFilterEmpty) {
        // Filter was created with existing expressions and the filters list should be updated accordingly,
        // but final result should not be emitted since it was created externally to begin with.
        this.rebuild = true
      }
    },
    methods: {
      compileFilter (index, payload) {

        if (payload.error) {
          this.error = payload.error
          this.filters[index] = ''
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

        if (this.rebuild && this.filters.length !== this.expressions.length) {
          // Rebuild state is when expressions are given on initialization
          // and filters should be updated but not passed on, in case the user edited the filter
          return
        }
        this.rebuild = false
        // In ongoing update state - propagating the filter and expression values
        this.$emit('change', this.filters.join(' '))
      },
      addExpression () {
        this.expressions = [ ...this.expressions, {
          ...expression,
          i: this.calculateI,
          nested: [{ ...nestedExpression, i: 0 }]
        }]
      },
      removeExpression (index) {
        if (index >= this.expressions.length) return
        this.expressions.splice(index, 1)
        this.filters.splice(index, 1)
        this.bracketWeights.splice(index, 1)
        if (!this.validateBrackets()) return
        if (!this.expressions.length) {
          // Expressions list should never stay empty, but have at least one empty expression
          this.addExpression()
        } else if (this.expressions[0].logicOp) {
          this.expressions[0].logicOp = ""
          // Not ready for publishing yet, since first expression should not have a logical operation
          return
        }
        this.$emit('change', this.filters.join(' '))
      },
      validateBrackets () {
        let totalBrackets = this.bracketWeights.reduce((accumulator, currentVal) => accumulator + currentVal, 0)
        if (totalBrackets !== 0) {
          this.error = (totalBrackets < 0) ? 'Missing right bracket' : 'Missing left bracket'
          this.$emit('error')
          return false
        }
        return true
      },
      compile () {
        this.$refs.expression.forEach((expression) => expression.compileExpression(true))
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