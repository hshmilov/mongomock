<template>
  <div class="x-expression-ops">
    <div>
      <XSelect
        v-if="!first"
        v-model="logicOp"
        :options="logicOpsToUse"
        :read-only="disabled"
        placeholder="op..."
        class="x-select-logic"
      />
    </div>
    <XButton
      :disabled="disabled"
      type="light"
      class="checkbox-label expression-bracket-left"
      :on="expression.leftBracket"
      @click="toggleLeftBracket"
    >(</XButton>
    <XButton
      :disabled="disabled"
      type="light"
      class="checkbox-label expression-not"
      :on="expression.not"
      @click="toggleNot"
    >NOT</XButton>

    <slot />

    <XButton
      :disabled="disabled"
      type="light"
      class="checkbox-label expression-bracket-right"
      :on="expression.rightBracket"
      @click="toggleRightBracket"
    >)</XButton>
    <ExpressionActions
      v-if="!disabled"
      :is-column-in-table="isColumnInTable"
      :disabled-toggle-field="disabledToggleField"
      @duplicate="$emit('duplicate')"
      @toggle-column="$emit('toggle-column')"
      @remove="$emit('remove')"
    />
  </div>
</template>

<script>
import { logicOps } from '@constants/filter';
import XSelect from '@axons/inputs/select/Select.vue';
import XButton from '@axons/inputs/Button.vue';
import ExpressionActions from '@neurons/schema/query/ExpressionActions.vue';

export default {
  name: 'XExpressionOperators',
  components: {
    XSelect,
    XButton,
    ExpressionActions,
  },
  props: {
    expression: {
      type: Object,
      default: () => {},
    },
    first: {
      type: Boolean,
      default: false,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    isColumnInTable: {
      type: Boolean,
      default: false,
    },
    disabledToggleField: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    logicOp: {
      get() {
        return this.expression.logicOp || 'and';
      },
      set(logicOp) {
        this.updateExpression({ logicOp });
      },
    },
  },
  created() {
    this.logicOpsToUse = logicOps;
  },
  methods: {
    updateExpression(update) {
      this.$emit('change', { ...update });
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
.x-expression-ops {
  display: grid;
  grid-gap: 8px;
  grid-template-columns: 60px 30px 30px auto 30px 66px;
  align-items: start;
  .checkbox-label {
    margin-bottom: 0;
    font-size: 12px;
    padding: 0;
    height: 32px;
    &::before {
      margin: 0;
    }
  }
  .x-button.ant-btn-light {
    input {
      display: none;
    }
  }
  .expression-remove {
    padding: 0;
  }
}
</style>
