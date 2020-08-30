<template>
  <div class="x-action-group">
    <template v-if="isSuccessive">
      <XIcon
        :type="condition"
        family="symbol"
        class="condition"
        :class="{disabled: iconsDisabled}"
      />
      <div class="connection" />
    </template>
    <div class="group-items">
      <XTextBox
        v-if="readOnly"
        key="new"
        v-bind="{id, text, selected: anySelected, clickable: false, capitalized: true}"
      />
      <XAction
        v-else
        key="new"
        v-bind="{id, condition, selected: isSelected(items.length), capitalized: true}"
        class="items-new"
        @click="selectAction(items.length)"
      />
      <XAction
        v-for="(data, i) in items"
        :key="data.name"
        v-bind="processAction(data, i)"
        @click="selectAction(i)"
      />
    </div>
  </div>
</template>

<script>
import XIcon from '@axons/icons/Icon';
import XTextBox from '../../axons/layout/TextBox.vue';
import XAction from './Action.vue';

export default {
  name: 'XActionGroup',
  components: {
    XTextBox, XAction, XIcon,
  },
  props: {
    id: String,
    items: Array,
    condition: String,
    selected: Number,
    readOnly: Boolean,
    iconsDisabled: {
      type: Boolean,
      default: true,
    },
  },
  computed: {
    isSuccessive() {
      return this.condition !== 'main';
    },
    text() {
      return `${this.condition} actions`;
    },
    anySelected() {
      return this.selected > -1 && this.selected <= this.items.length;
    },
    empty() {
      return !this.items.length;
    },
  },
  methods: {
    processAction(data, i) {
      return {
        condition: this.condition,
        name: data.action.action_name,
        title: data.name,
        selected: this.isSelected(i),
        status: data.status,
        readOnly: this.readOnly,
      };
    },
    selectAction(i) {
      this.$emit('select', this.condition, i);
    },
    isSelected(i) {
      return i === this.selected;
    },
  },
};
</script>

<style lang="scss">
    .x-action-group {
        display: flex;
        align-items: flex-start;
        .condition {
            font-size: 20px;
            margin-left: 12px;
            margin-top: 14px;
        }
        .connection {
            height: 2px;
            background-color: $grey-4;
            width: 12px;
            margin-top: 24px;
        }
        .group-items {
            display: grid;
            grid-auto-rows: 48px;
            grid-gap: 8px 0;
            z-index: 0;
            .items-new {
                z-index: 1;
            }
        }
        .disabled {
          use {
            fill: $grey-3;
          }
          g {
            fill: $grey-3;
          }
        }
    }
</style>
