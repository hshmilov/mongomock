<template>
  <div class="x-condition__wrapper">
    <XSelect
      v-model="context"
      :options="contextOptionsToUse"
      present-selection-value
      :read-only="readOnly"
      placeholder="ALL"
      :class="{selected: contextSelected}"
      class="expression-context"
    />
    <Component
      :is="conditionType"
      class="x-condition"
      :module="module"
      :condition="condition"
      :read-only="readOnly"
      :view-fields="viewFields"
      :field-type="expression.fieldType"
      @update="updateCondition"
      @change-child="onChangeChild"
      @remove-child="onRemoveChild"
      @duplicate-child="onDuplicateChild"
      @toggle-column="toggleColumn"
    >
      <template #default>
        <XButton
          v-if="children.length && !readOnly"
          type="light"
          class="expression-nest"
          @click="onAddChild"
        >+</XButton>
      </template>
    </Component>
  </div>
</template>

<script>
import XSelect from '@axons/inputs/select/Select.vue';
import { calcMaxIndex } from '@constants/utils';
import { childExpression, contextOptions } from '@constants/filter';
import ALL from './ConditionAggregatedData.vue';
import OBJ from './ConditionComplexField.vue';
import ENT from './ConditionAssetEntity.vue';
import CMP from './ConditionFieldComparison.vue';

export default {
  name: 'XCondition',
  components: {
    ALL,
    OBJ,
    ENT,
    CMP,
    XSelect,
  },
  model: {
    prop: 'condition',
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
    condition: {
      type: Object,
      default: undefined,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
    viewFields: {
      type: Array,
      default: () => ([]),
    },
  },
  computed: {
    conditionType() {
      return this.context || 'ALL';
    },
    field() {
      return this.condition.field;
    },
    children: {
      get() {
        return this.condition.children || [];
      },
      set(children) {
        if (!children.length) {
          children.push({
            ...childExpression, i: 0,
          });
        }
        this.$emit('input', { children });
      },
    },
    context: {
      get() {
        return this.expression.context || '';
      },
      set(context) {
        this.$emit('update-context', {
          context, compOp: '', value: null, field: '', children: [],
        });
      },
    },
    contextSelected() {
      return this.context !== '';
    },
  },
  created() {
    this.contextOptionsToUse = contextOptions;
  },
  methods: {
    updateCondition(update) {
      let { children } = this;
      if (update.field !== this.condition.field) {
        children = [{
          ...childExpression, i: 0,
        }];
      }
      this.$emit('input', {
        ...this.condition, ...update, children,
      });
    },
    onAddChild() {
      const childToAdd = { ...childExpression };
      childToAdd.expression.logicOp = !this.children.length ? '' : 'and';
      this.children = [...this.children, {
        ...childToAdd,
        i: calcMaxIndex(this.children),
      }];
    },
    onChangeChild(childChanged) {
      const { index, expression } = childChanged;
      const replaceExpression = (child) => ((child.i === index) ? { ...child, expression } : child);
      this.children = this.children.map(replaceExpression);
    },
    onRemoveChild(givenIndex) {
      const newChildren = this.children.filter((child) => child.i !== givenIndex);
      if (newChildren[0] && newChildren[0].expression.logicOp) {
        // Remove the logicOp from the expression
        newChildren[0].expression.logicOp = '';
      }
      this.children = newChildren;
    },
    onDuplicateChild(givenIndex) {
      const index = this.children.findIndex((child) => child.i === givenIndex);
      const newChild = { ...this.children[index], i: calcMaxIndex(this.children) };
      if (!newChild.expression.logicOp) {
        newChild.expression.logicOp = 'and';
      }
      this.children = [
        ...this.children.slice(0, index + 1),
        newChild,
        ...this.children.slice(index + 1),
      ];
    },
    toggleColumn(columnName) {
      this.$emit('toggle-column', columnName);
    },
  },
};
</script>

<style lang="scss">
  .x-condition {
    &__wrapper {
      display: grid;
      grid-gap: 8px;
      grid-template-columns: 60px auto;
    }
    &__parent {
      display: grid;
      grid-gap: 8px;
      &__header {
        display: grid;
        grid-template-columns: 60px auto;
        grid-gap: 8px;
      }
    }
    &__child {
      display: grid;
      grid-template-columns: 240px auto;
      grid-gap: 8px 4px;
      position: relative;
      .child-field {
        display: flex;
        &__type {
          border: 1px solid $grey-2;
          border-radius: 2px 0 0 2px;
          padding: 0 8px;
          display: flex;
          align-items: center;
          width: 60px;
          .logo {
            max-width: 30px;
            height: auto;
            max-height: 24px;
          }
        }
        .x-select {
          margin-left: -1px;
          border-radius: 0 2px 2px 0;
          width: 100%;
          max-width: 180px;
        }
      }
    }
    &__scaled {
      position: relative;
      left: -144px;
      width: calc(100% + 223px);
    }
    .x-select-typed-field {
      width: 240px;
      .field-select {
        flex: 0 0 auto;
      }
    }
  }
</style>
