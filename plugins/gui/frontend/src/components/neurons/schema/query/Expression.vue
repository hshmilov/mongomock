<template>
  <div class="x-expression">
    <XExpressionOperators
      :first="first"
      :expression="expression"
      :disabled="disabled"
      :is-column-in-table="isColumnInTable"
      :disabled-toggle-field="disableColumnToggle"
      @change="updateExpression"
      @duplicate="$emit('duplicate')"
      @toggle-column="$emit('toggle-column', expression.field)"
      @remove="$emit('remove')"
    >
      <template #default>
        <XCondition
          v-model="expressionCond"
          :expression="expression"
          :module="module"
          :read-only="disabled"
          :view-fields="viewFields"
          @update-context="updateExpression"
          @toggle-column="$emit('toggle-column', $event)"
        />
      </template>
    </XExpressionOperators>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import { AUTO_QUERY, GET_MODULE_FIELDS } from '@store/getters';
import XExpressionOperators from './ExpressionOperators.vue';
import XCondition from './Condition.vue';


export default {
  name: 'XExpression',
  components: {
    XCondition, XExpressionOperators,
  },
  model: {
    prop: 'expression',
    event: 'input',
  },
  props: {
    expression: {
      type: Object,
      default: () => ({}),
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
      default: false,
    },
    viewFields: {
      type: Array,
      default: () => ([]),
    },
  },
  computed: {
    ...mapGetters({
      autoQuery: AUTO_QUERY,
      getModuleFields: GET_MODULE_FIELDS,
    }),
    expressionCond: {
      get() {
        return {
          field: this.expression.field,
          compOp: this.expression.compOp,
          value: this.expression.value,
          subvalue: this.expression.subvalue,
          filteredAdapters: this.expression.filteredAdapters,
          fieldType: this.expression.fieldType,
          children: this.expression.children,
        };
      },
      set(condition) {
        this.updateExpression(condition);
      },
    },
    isColumnInTable() {
      return this.viewFields.includes(this.expression.field);
    },
    disableColumnToggle() {
      return !this.getModuleFields(this.module).includes(this.expression.field);
    },
  },
  methods: {
    updateExpression(update) {
      this.$emit('change', { ...update });
    },
    toggleColumn(columnName) {
      this.$emit('toggle-column', columnName);
    },
  },
};
</script>

<style lang="scss">
  .x-expression {

    select, input:not([type=checkbox]) {
      height: 32px;
      width: 100%;
    }
    .expression-nest {
      text-align: left;
      position: relative;
      left: -114px;
      display: flex;
      justify-content: center;
      align-items: center;
    }
    .expression-context {
      height: 32px;
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
