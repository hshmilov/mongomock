<template>
  <div class="x-expression">
    <!-- Choice of logical operator, available from second expression --->
    <x-select
      :readOnly="disabled"
      v-if="!first"
      v-model="logicOp"
      :options="logicOps"
      placeholder="op..."
      class="x-select-logic"
    />
    <div v-else />
    <!-- Option to add '(', to negate expression and choice of field to filter -->
    <x-button
      :disabled="disabled"
      light
      class="checkbox-label expression-bracket-left"
      :active="expression.leftBracket"
      @click="toggleLeftBracket"
    >(</x-button>
    <x-button
      :disabled="disabled"
      light
      class="checkbox-label expression-not"
      :active="expression.not"
      @click="toggleNot"
    >NOT</x-button>
    <x-button
      :disabled="disabled"
      light
      class="checkbox-label expression-obj"
      :active="expression.obj"
      @click="toggleObj"
    >OBJ</x-button>
    <x-condition
      :readOnly="disabled"
      v-model="expressionCond"
      :module="module"
      :first="first"
      :is-parent="expression.obj"
      @change="onChangeCondition"
    />

    <!-- Option to add ')' and to remove the expression -->
    <x-button
      :disabled="disabled"
      light
      class="checkbox-label expression-bracket-right"
      :active="expression.rightBracket"
      @click="toggleRightBracket"
    >)</x-button>
    <x-button
      v-if="!disabled"
      link
      class="expression-remove"
      @click="$emit('remove')"
    >x</x-button>

    <template v-if="expression.obj && expression.field">
      <template v-for="(nestedExpr, i) in expression.nested">
        <div class="grid-span4" />
        <x-condition
          :readOnly="disabled"
          :key="'cond' + nestedExpr.i"
          v-model="nestedExpr.expression"
          :module="module"
          :parent-field="expression.field"
          @input="onChangeCondition($event, i)"
        />
        <x-button
          v-if="!disabled"
          :key="`remove_${nestedExpr.i}`"
          link
          class="condition-remove"
          @click="removeNestedExpression(i)"
        >x</x-button>
        <div />
      </template>
      <div class="grid-span4" />
      <x-button
         v-if="!disabled"
        link
        class="expression-nest"
        @click="addNestedExpression"
      >+</x-button>
    </template>
  </div>
</template>

<script>
  import xSelect from '../../axons/inputs/select/Select.vue'
  import xCondition from './Condition.vue'
  import xButton from '../../axons/inputs/Button.vue'
  import { nestedExpression } from '../../../constants/filter'

  import {mapGetters} from 'vuex'
  import { AUTO_QUERY } from "../../../store/getters"
  import { calcMaxIndex } from '../../../constants/utils'

  export default {
    name: 'XExpression',
    components: {
      xSelect, xCondition, xButton
    },
    model: {
      prop: 'expression',
      event: 'input'
    },
    props: {
      expression: {
        type: Object,
        default: () => {}
      },
      module: {
        type: String,
        required: true
      },
      first: {
        type: Boolean,
        default: false
      },
      disabled: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
      }
    },
    computed: {
      ...mapGetters({
        autoQuery: AUTO_QUERY
      }),
      logicOps () {
        return [{
          name: 'and', title: 'and'
        }, {
          name: 'or', title: 'or'
        }]
      },
      expressionCond: {
        get () {
          return {
            field: this.expression.field,
            compOp: this.expression.compOp,
            value: this.expression.value,
            filteredAdapters: this.expression.filteredAdapters,
            fieldType: this.expression.fieldType
          }
        },
        set (condition) {
          if (condition.field !== this.expression.field && this.expression.obj) {
            this.expression.nested = []
            this.addNestedExpression()
          }
          this.updateExpression({
            value: condition.value,
            field: condition.field,
            compOp: condition.compOp,
            filteredAdapters: condition.filteredAdapters,
            fieldType: condition.fieldType,
          })
        }
      },
      logicOp: {
        get () {
          return this.expression.logicOp
        },
        set (logicOp) {
          this.updateExpression({ logicOp })
        }
      }
    },
    methods: {
      updateExpression (update) {
        this.$emit('input', {
          ...this.expression,
          ...update
        })
        this.$emit('change')
      },
      toggleLeftBracket () {
        this.updateExpression({
          leftBracket: !this.expression.leftBracket
        })
      },
      toggleRightBracket () {
        this.updateExpression({
          rightBracket: !this.expression.rightBracket
        })
      },
      toggleNot () {
        this.updateExpression({
          not: !this.expression.not
        })
      },
      toggleObj () {
        this.updateExpression({
          obj: !this.expression.obj,
          field: ''
        })
      },
      addNestedExpression () {
        this.expression.nested.push({
          ...nestedExpression,
          i: calcMaxIndex(this.expression.nested),
          filteredAdapters: this.expression.filteredAdapters
        })
        this.$emit('change')
      },
      onChangeCondition (condition, nestedIndex) {
        if (nestedIndex !== undefined) {
          this.expression.nested[nestedIndex].condition = condition
        }
        this.$emit('change')
      },
      removeNestedExpression (index) {
        this.expression.nested.splice(index, 1)
        if (!this.expression.nested.length) {
          this.addNestedExpression()
        }
        this.$emit('change')
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

        .x-button.light {
            input {
                display: none;
            }
        }

        .expression-nest {
            text-align: left;
        }
    }
</style>
