<template>
  <Component
    :is="conditionType"
    class="x-condition"
    :module="module"
    :condition="condition"
    :read-only="readOnly"
    :view-fields="viewFields"
    @update="updateCondition"
    @change-child="onChangeChild"
    @remove-child="onRemoveChild"
    @duplicate-child="onDuplicateChild"
    @toggle-column="toggleColumn"
  >
    <XButton
      v-if="children.length && !readOnly"
      type="link"
      class="expression-nest"
      @click="onAddChild"
    >+</XButton>
  </Component>
</template>

<script>
import ALL from './ConditionAggregatedData.vue';
import OBJ from './ConditionComplexField.vue';
import ENT from './ConditionAssetEntity.vue';
import CMP from './ConditionFieldComparison.vue';

import { calcMaxIndex } from '../../../../constants/utils';
import { childExpression } from '../../../../constants/filter';

export default {
  name: 'XCondition',
  components: {
    ALL,
    OBJ,
    ENT,
    CMP,
  },
  model: {
    prop: 'condition',
    event: 'input',
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    condition: {
      type: Object,
      default: undefined,
    },
    context: {
      type: String,
      default: '',
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
  data() {
    return {
    };
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
      this.children = [...this.children, {
        ...childExpression,
        i: calcMaxIndex(this.children),
      }];
    },
    onChangeChild(childChanged) {
      const { index, expression } = childChanged;
      const replaceExpression = (child) => ((child.i === index) ? { ...child, expression } : child);
      this.children = this.children.map(replaceExpression);
    },
    onRemoveChild(index) {
      this.children = this.children.filter((child) => child.i !== index);
    },
    onDuplicateChild(index) {
      const duplicateIndex = index + 1;
      this.children = [
        ...this.children.slice(0, duplicateIndex),
        { ...this.children.find((child) => child.i === index), i: duplicateIndex },
        ...this.children.slice(duplicateIndex).map((item, itemIndex) => {
          return { ...item, i: duplicateIndex + itemIndex + 1 };
        }),
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
    &__parent {
      display: grid;
      grid-gap: 8px;
    }

    &__child {
      display: grid;
      grid-template-columns: 240px auto 48px;
      grid-gap: 4px;
      position: relative;
    }
  }
</style>
