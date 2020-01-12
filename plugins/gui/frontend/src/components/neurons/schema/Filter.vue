<template>
  <div class="x-filter">
    <div v-if="!disabled" class="filter-title">Show only data:</div>
    <x-expression
      v-for="(expression, i) in expressions"
      :disabled="disabled"
      :key="expression.i"
      ref="expression"
      v-model="expressions[i]"
      :first="!i"
      :module="module"
      @change="onExpressionsChange"
      @remove="() => removeExpression(i)"
    />
    <div v-if="!disabled" class="footer">
      <x-button
        light
        @click="addEmptyExpression"
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
  import { calcMaxIndex } from '../../../constants/utils'
  import {mapGetters} from "vuex";
  import {GET_MODULE_SCHEMA} from "../../../store/getters";
  import {expression, nestedExpression} from "../../../constants/filter";

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
      },
      error: {
          type: String,
          default: ''
      },
      disabled: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        filters: []
      }
    },
    computed: {
        ...mapGetters({
            getModuleSchema: GET_MODULE_SCHEMA
        }),
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
        this.addEmptyExpression()
      }
    },
    methods: {
      onExpressionsChange() {
          this.$emit('change', this.expressions)
      },
      addEmptyExpression () {
          this.expressions.push({...expression, i: this.maxIndex, nested: [{ ...nestedExpression, i: 0 }]})
          this.onExpressionsChange()
      },
      removeExpression (index) {
          if (index >= this.expressions.length) return
          if (this.expressions.length === 1) {
              this.$emit('clear')
              return
          }
          this.expressions.splice(index, 1)
          if (this.expressions[0].logicOp) {
              // Remove the logicOp from filter as well as expression
              this.expressions[0].logicOp = ''
          }
          this.onExpressionsChange()
      },
      reset () {
        this.filters.length = 0
        this.addEmptyExpression()
        this.$emit('error', null)
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
