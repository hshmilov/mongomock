<template>
  <component
    :is="conditionType"
    class="x-condition"
    :module="module"
    :condition="condition"
    :read-only="readOnly"
    @update="updateCondition"
    @change-child="onChangeChild"
    @remove-child="onRemoveChild"
  >
    <x-button
      v-if="children.length && !readOnly"
      link
      class="expression-nest"
      @click="onAddChild"
    >+</x-button>
  </component>
</template>

<script>
import ALL from './ConditionAggregatedData.vue';
import OBJ from './ConditionComplexField.vue';
import ENT from './ConditionAssetEntity.vue';
import xButton from '../../../axons/inputs/Button.vue';

import { calcMaxIndex } from '../../../../constants/utils';
import { childExpression } from '../../../../constants/filter';

export default {
  name: 'XCondition',
  components: {
    ALL,
    OBJ,
    ENT,
    xButton,
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
      grid-template-columns: 240px auto;
      grid-gap: 4px;
      position: relative;

      .child-remove {
        position: absolute;
        left: 100%;
      }

    }
  }
</style>
