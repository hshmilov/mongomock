<template>
  <div class="x-expression">
    <!-- Choice of logical operator, available from second expression --->
    <x-select
      v-if="!first"
      v-model="logicOp"
      :options="logicOps"
      :readOnly="disabled"
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
    <x-select
      v-model="context"
      :options="contextOptions"
      present-selection-value
      :read-only="disabled"
      placeholder="ALL"
      :class="{selected: contextSelected}"
      class="expression-context"
    />
    <x-condition
      v-model="expressionCond"
      :module="module"
      :context="context"
      :read-only="disabled"
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
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import xSelect from '../../../axons/inputs/select/Select.vue';
import xCondition from './Condition.vue';
import xButton from '../../../axons/inputs/Button.vue';

import { AUTO_QUERY } from '../../../../store/getters';

export default {
  name: 'XExpression',
  components: {
    xSelect, xCondition, xButton,
  },
  model: {
    prop: 'expression',
    event: 'input',
  },
  props: {
    expression: {
      type: Object,
      default: () => {},
    },
    module: {
      type: String,
      required: true,
    },
    first: {
      type: Boolean,
      default: false,
    },
    disabled: {
      type: Boolean,
      default: false
    },
  },
  data() {
    return {
      contextOptions: [{
        title: 'Aggregated Data', name: '',
      }, {
        title: 'Complex Field', name: 'OBJ',
      }, {
        title: 'Asset Entity', name: 'ENT',
      }],
    };
  },
  computed: {
    ...mapGetters({
      autoQuery: AUTO_QUERY,
    }),
    logicOps() {
      return [{
        name: 'and', title: 'and',
      }, {
        name: 'or', title: 'or',
      }];
    },
    expressionCond: {
      get() {
        return {
          field: this.expression.field,
          compOp: this.expression.compOp,
          value: this.expression.value,
          filteredAdapters: this.expression.filteredAdapters,
          fieldType: this.expression.fieldType,
          children: this.expression.children,
        };
      },
      set(condition) {
        this.updateExpression(condition);
      },
    },
    logicOp: {
      get() {
        return this.expression.logicOp;
      },
      set(logicOp) {
        this.updateExpression({ logicOp });
      },
    },
    context: {
      get() {
        return this.expression.context || '';
      },
      set(context) {
        this.updateExpression({
          context, field: '', children: [],
        });
      },
    },
    contextSelected() {
      return this.context !== '';
    },
  },
  methods: {
    updateExpression(update) {
      this.$emit('input', {
        ...this.expression,
        ...update,
      });
      this.$emit('change');
    },
    toggleLeftBracket() {
      this.updateExpression({
        leftBracket: !this.expression.leftBracket,
      });
    },
    toggleRightBracket() {
      this.updateExpression({
        rightBracket: !this.expression.rightBracket,
      });
    },
    toggleNot() {
      this.updateExpression({
        not: !this.expression.not,
      });
    },
  },
};
</script>

<style lang="scss">
  .x-expression {
    display: grid;
    grid-template-columns: 60px 30px 30px 60px auto 30px 30px;
    align-items: start;
    grid-gap: 8px;
    margin-bottom: 16px;

    select, input:not([type=checkbox]) {
      height: 32px;
      width: 100%;
    }

    .checkbox-label {
      margin-bottom: 0;
      cursor: pointer;
      font-size: 12px;
      padding: 0;
      height: 32px;

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

    .expression-context {
      .content.expand {
        min-width: max-content;
      }

      &.selected .x-select-trigger {
        background: $theme-black;
        color: $grey-2;
        border-radius: 2px;
      }
    }
  }
</style>
