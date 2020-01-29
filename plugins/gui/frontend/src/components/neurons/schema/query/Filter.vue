<template>
  <div class="x-filter">
    <div
      v-if="!disabled"
      class="filter-title"
    >Show only data:</div>
    <template v-if="disabled">
      <x-expression
        v-for="(expression, i) in expressions"
        :key="expression.i"
        ref="expression"
        v-model="expressions[i]"
        :disabled="disabled"
        :first="!i"
        :module="module"
        @change="onExpressionsChange"
        @remove="() => removeExpression(i)"
      />
    </template>
    <draggable
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
        <v-icon
          v-if="expressions.length > 1"
          size="15"
          class="draggable-expression-handle"
        >$vuetify.icons.draggable</v-icon>
        <x-expression
          ref="expression"
          v-model="expressions[i]"
          :disabled="disabled"
          :first="!i"
          :module="module"
          @change="onExpressionsChange"
          @remove="() => removeExpression(i)"
        />
      </li>
    </draggable>
    <div
      v-if="!disabled"
      class="footer"
    >
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
import xButton from '@axons/inputs/Button.vue';
import { calcMaxIndex } from '@constants/utils';
import { expression } from '@constants/filter';
import draggable from 'vuedraggable';
import { mdiDrag } from '@mdi/js';
import xExpression from './Expression.vue';

export default {
  name: 'XFilter',
  components: { xExpression, xButton, draggable },
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
      dragIconPath: mdiDrag,
    };
  },
  computed: {
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
  mounted() {
    if (!this.expressions.length) {
      this.addEmptyExpression();
    }
  },
  methods: {
    onExpressionsChange() {
      this.$emit('change', this.expressions);
    },
    addEmptyExpression() {
      const logicOp = !this.expressions.length ? '' : 'and';
      this.expressions.push({ ...expression, i: this.maxIndexת, logicOp });
      this.onExpressionsChange();
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
    reset() {
      this.filters.length = 0;
      this.addEmptyExpression();
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
        .expression__container > .x-expression {
            width: 100%;
        }
        .expression__container--draggable {
          display: flex;

          .draggable-expression-handle {
            float: left;
            cursor: move;
            margin-right: 4px;
            margin-top: 8px;
            opacity: 0;
            width: 5%;
          }
          .x-expression {
            width: 95%;
          }

          &:hover {
            .draggable-expression-handle {
              opacity: 1;
            }
          }
        }
        .ghost {
          border: 1px dashed rgba($theme-blue, 0.4);
        }
    }
</style>
