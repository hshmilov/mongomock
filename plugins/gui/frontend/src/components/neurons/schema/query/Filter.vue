<template>
  <div class="x-filter">
    <div
      v-if="!disabled"
      class="filter-title"
    >Show only data:</div>
    <template v-if="disabled">
      <XExpression
        v-for="(expression, i) in expressions"
        :key="expression.i"
        ref="expression"
        v-model="expressions[i]"
        :disabled="disabled"
        :first="!i"
        :module="module"
      />
    </template>
    <Draggable
      v-else
      v-model="expressions"
      tag="ul"
      handle=".draggable-expression-handle"
      ghost-class="ghost"
    >
      <li
        v-for="(expression, i) in expressions"
        :key="expression.i"
        :class="expressionContainerCSSClass"
      >
        <XIcon
          v-if="expressions.length > 1"
          family="action"
          type="drag"
          :rotate="90"
          class="draggable-expression-handle"
        />
        <XExpression
          ref="expression"
          v-model="expressions[i]"
          :disabled="disabled"
          :first="!i"
          :module="module"
          :view-fields="viewFields"
          v-on="{ change: onExpressionsChangeByIndex(i)}"
          @remove="removeExpression(i)"
          @duplicate="duplicateExpression(i)"
          @toggle-column="toggleColumn"
        />
      </li>
    </Draggable>
    <div
      v-if="!disabled"
      class="footer"
    >
      <XButton
        type="light"
        class="add-expression"
        @click="addEmptyExpression"
      >+</XButton>
      <div
        v-if="error"
        class="error-text"
      >{{ error }}</div>
    </div>
  </div>
</template>

<script>
import { UPDATE_DATA_VIEW } from '@store/mutations';
import { mapState, mapMutations } from 'vuex';
import { calcMaxIndex } from '@constants/utils';
import { expression } from '@constants/filter';
import Draggable from 'vuedraggable';
import XExpression from './Expression.vue';

export default {
  name: 'XFilter',
  components: { XExpression, Draggable },
  props: {
    module: {
      type: String,
      required: true,
    },
    value: {
      type: Array,
      default: () => [],
    },
    error: {
      type: String,
      default: '',
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      filters: [],
    };
  },
  computed: {
    ...mapState({
      viewFields(state) {
        return state[this.module].view.fields;
      },
    }),
    expressions: {
      get() {
        return this.value;
      },
      set(expressions) {
        this.$emit('input', expressions);
      },
    },
    maxIndex() {
      return calcMaxIndex(this.expressions);
    },
    expressionContainerCSSClass() {
      return `expression__container${this.expressions.length > 1 ? '--draggable' : ''}`;
    },
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    onExpressionsChangeByIndex(index) {
      return (update) => {
        this.$emit('change', this.expressions.map((currentExpression, i) => {
          if (index === i) {
            return { ...currentExpression, ...update };
          }
          return currentExpression;
        }));
      };
    },
    onExpressionsChange() {
      this.$emit('change', this.expressions);
    },
    addEmptyExpression() {
      const logicOp = !this.expressions.length ? '' : 'and';
      this.$emit('change', [...this.expressions, { ...expression, i: this.maxIndex, logicOp }]);
    },
    removeExpression(index) {
      if (index >= this.expressions.length) return;
      if (this.expressions.length === 1) {
        this.$emit('clear');
        return;
      }
      this.expressions.splice(index, 1);
      if (this.expressions[0].logicOp) {
        // Remove the logicOp from filter as well as expression
        this.expressions[0].logicOp = '';
      }
      this.onExpressionsChange();
    },
    duplicateExpression(index) {
      const logicOp = this.expressions[index].logicOp || 'and';
      this.$emit('change', [
        ...this.expressions.slice(0, index + 1),
        { ...this.expressions[index], logicOp, i: this.maxIndex },
        ...this.expressions.slice(index + 1),
      ]);
    },
    toggleColumn(columnName) {
      let viewFields = [];
      if (this.viewFields.includes(columnName)) {
        viewFields = this.viewFields.filter((column) => column !== columnName);
      } else {
        // insert column to second place, so it will be easier to see with query wizard open
        viewFields = [...this.viewFields];
        viewFields.splice(1, 0, columnName);
      }
      this.updateView({
        module: this.module,
        view: {
          fields: viewFields,
        },
      });
      this.$emit('done');
    },
    reset() {
      this.filters.length = 0;
      this.$emit('error', null);
    },
  },
};

</script>

<style lang="scss">
    .x-filter {
        .filter-title {
            line-height: 24px;
        }

        .footer {
            display: flex;
            justify-content: space-between;
            .add-expression {
                display: flex;
                justify-content: center;
                align-items: center;
            }
        }
        .expression__container > .x-expression {
            width: 100%;
        }
        .expression__container--draggable {
          display: flex;

          .draggable-expression-handle {
            float: left;
            cursor: move;
            margin-right: 4px;
            opacity: 0;
            width: 5%;
            margin-top: 15px;
          }
          .x-expression {
            width: 95%;
          }

          &:hover {
            .draggable-expression-handle {
              opacity: 1;
              font-size: 15px;
              color: $theme-orange;
            }
          }
        }
        .ghost {
          border: 1px dashed rgba($theme-blue, 0.4);
        }
    }
</style>
