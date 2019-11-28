<template>
  <div class="x-filter">
    <div class="filter-title">Show only data:</div>
    <x-expression
      v-for="(expression, i) in expressions"
      :key="expression.i"
      ref="expression"
      v-model="expressions[i]"
      :first="!i"
      :module="module"
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
        error: ''
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
      maxIndex () {
        return calcMaxIndex(this.expressions)
      }
    },
    mounted () {
      if (!this.expressions.length) {
        this.addExpression()
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
        this.bracketWeights[index] = payload.bracketWeight || 0
        if (!this.validateBrackets()) return
        // No compilation error - can remove existing error
        this.error = ''

        if (this.filters.length !== this.expressions.length) {
          // Rebuild state - expressions are given on initialization of the component
          // and filters should be updated but not passed on, to prevent calls with partial filter
          return
        }
        this.$emit('change', this.filters.join(' '))
      },
      addExpression () {
        this.expressions.push({...expression, i: this.maxIndex, nested: [{ ...nestedExpression, i: 0 }]})
      },
      removeExpression (index) {
        if (index >= this.expressions.length) return
        if (this.expressions.length === 1) {
          this.$emit('clear')
          return
        }
        this.expressions.splice(index, 1)
        this.filters.splice(index, 1)
        this.bracketWeights.splice(index, 1)
        if (!this.validateBrackets()) return
        if (this.expressions[0].logicOp) {
          // Remove the logicOp from filter as well as expression
          this.filters[0] = this.filters[0].replace(this.expressions[0].logicOp + ' ', '')
          this.expressions[0].logicOp = ''
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
      },
      reset () {
        this.filters = []
        this.addExpression()
        this.error = ''
      }
    }
  }
</script>

<style lang="scss">
    .x-filter {
        .filter-title {
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