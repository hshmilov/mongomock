<template>
  <div class="x-expression">
    <!-- Choice of logical operator, available from second expression --->
    <x-select
      v-if="!first"
      v-model="logicOp"
      :options="logicOps"
      placeholder="op..."
      class="x-select-logic"
    />
    <div v-else />
    <!-- Option to add '(', to negate expression and choice of field to filter -->
    <x-button
      light
      class="checkbox-label expression-bracket-left"
      :active="expression.leftBracket"
      @click="toggleLeftBracket"
    >(</x-button>
    <x-button
      light
      class="checkbox-label expression-not"
      :active="expression.not"
      @click="toggleNot"
    >NOT</x-button>
    <x-button
      light
      class="checkbox-label expression-obj"
      :active="expression.obj"
      @click="toggleObj"
    >OBJ</x-button>
    <x-condition
      v-model="expressionCond"
      :module="module"
      :first="first"
      :is-parent="expression.obj"
      @change="onChangeCondition"
      @error="onErrorCondition"
    />

    <!-- Option to add ')' and to remove the expression -->
    <x-button
      light
      class="checkbox-label expression-bracket-right"
      :active="expression.rightBracket"
      @click="toggleRightBracket"
    >)</x-button>
    <x-button
      link
      class="expression-remove"
      @click="$emit('remove')"
    >x</x-button>

    <template v-if="expression.obj && expression.field">
      <template v-for="(nestedExpr, i) in expression.nested">
        <div class="grid-span4" />
        <x-condition
          :key="'cond' + nestedExpr.i"
          v-model="nestedExpr.expression"
          :module="module"
          :parent-field="expression.field"
          @change="(cond) => onChangeCondition(cond, i)"
          @error="onErrorCondition"
        />
        <x-button
          :key="`remove_${nestedExpr.i}`"
          link
          class="condition-remove"
          @click="removeNestedExpression(i)"
        >x</x-button>
        <div />
      </template>
      <div class="grid-span4" />
      <x-button
        link
        class="expression-nest"
        @click="addNestedExpression"
      >+</x-button>
    </template>
  </div>
</template>

<script>
  import xSelect from '../../axons/inputs/Select.vue'
  import xCondition from './Condition.vue'
  import xButton from '../../axons/inputs/Button.vue'
  import { nestedExpression } from '../../../constants/filter'

  import {mapGetters, mapMutations} from 'vuex'
  import { CHANGE_TOUR_STATE } from '../../../store/modules/onboarding'
  import { AUTO_QUERY } from "../../../store/getters"
  import { calcMaxIndex, getExcludedAdaptersFilter } from '../../../constants/utils'

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
      }
    },
    data () {
      return {
        condition: '',
        error: '',
        errorCondition: ''
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
            fieldType: condition.fieldType
          }, false)
        }
      },
      logicOp: {
        get () {
          return this.expression.logicOp
        },
        set (logicOp) {
          this.updateExpression({ logicOp })
        }
      },
      nestedExpressionCond () {
        return this.expression.nested
          .filter(item => item.condition)
          .map(item => item.condition)
          .join(' and ')
      }
    },
    updated () {
      if (this.first) {
        if (this.expression.field && this.expression.compOp && !this.expression.value) {
          this.changeState({ name: 'queryValue' })
        } else if (this.expression.field && !this.expression.compOp) {
          this.changeState({ name: 'queryOp' })
        }
      }
    },
    methods: {
      ...mapMutations({
        changeState: CHANGE_TOUR_STATE
      }),
      updateExpression (update, compile = true) {
        this.$emit('input', {
          ...this.expression,
          ...update
        })
        if (compile) {
          this.$nextTick(this.compileExpression)
        }
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
      checkErrors () {
        if (!this.first && !this.logicOp) {
          return 'Logical operator is needed to add expression to the filter'
        } else if (this.expression.obj && !this.expression.field) {
          return 'Select an object to add nested conditions'
        }
        return ''
      },
      compileExpression (force = false) {
        if (!force && !this.autoQuery) {
          return
        }
        if (!this.expression.field || (this.expression.obj && !this.nestedExpressionCond)) {
          this.$emit('change', { filter: '', bracketWeight: 0 })
          return
        }
        let error = this.errorCondition || this.checkErrors()
        if (error) {
          this.$emit('change', { error })
          return
        }
        let filterStack = []
        if (this.logicOp && !this.first) {
          filterStack.push(this.logicOp + ' ')
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
            let expression = this.getMatchExpression(this.expression.field, this.nestedExpressionCond)
            filterStack.push('({val})'.replace(/{val}/g, getExcludedAdaptersFilter(this.expression.fieldType,
                this.expression.field, this.expression.filteredAdapters, expression)))
        } else {
          filterStack.push(this.condition)
        }
        if (this.expression.rightBracket) {
          filterStack.push(')')
          bracketWeight += 1
        }
        this.$emit('change', { filter: filterStack.join(''), bracketWeight })
      },
      getMatchExpression(field, condition){
          return `${field} == match([${condition}])`
      },
      addNestedExpression () {
        this.expression.nested.push({
          ...nestedExpression,
          i: calcMaxIndex(this.expression.nested),
          filteredAdapters: this.expression.filteredAdapters
        })
      },
      onChangeCondition (condition, nestedIndex) {
        if (nestedIndex !== undefined) {
          this.expression.nested[nestedIndex].condition = condition
        } else if (condition !== undefined) {
          this.condition = condition
        }
        this.errorCondition = ''
        this.compileExpression()
      },
      onErrorCondition (error) {
        this.errorCondition = error
        this.compileExpression(true)
      },
      removeNestedExpression (index) {
        this.expression.nested.splice(index, 1)
        if (!this.expression.nested.length) {
          this.addNestedExpression()
        }
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

        .x-button.light {
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
