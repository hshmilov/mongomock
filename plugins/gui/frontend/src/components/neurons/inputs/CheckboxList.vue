<template>
  <div class="x-checkbox-list">
    <Component
      :is="listWrapperType"
      v-model="orderedItems"
      ghost-class="ghost"
      class="list"
      :class="{ draggable }"
      @start="onStartDrag"
      @end="onEndDrag"
    >
      <div
        v-for="item in items"
        :key="item.name"
        :title="item.title"
        class="list__item"
        :class="{ dragging }"
      >
        <XIcon
          family="action"
          type="drag"
        />
        <XCheckbox
          :value="item.name"
          :label="item.title"
          :data="value"
          @change="onChangeCheckbox"
        >
          <slot :item="item" />
        </XCheckbox>

      </div>
    </Component>
  </div>
</template>

<script>
import draggable from 'vuedraggable';
import XIcon from '@axons/icons/Icon';
import XCheckbox from '../../axons/inputs/Checkbox.vue';

export default {
  name: 'XCheckboxList',
  components: {
    draggable, XCheckbox, XIcon,
  },
  props: {
    items: {
      type: Array,
      required: true,
    },
    value: {
      type: Array,
      default: () => [],
    },
    draggable: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      dragging: false,
    };
  },
  computed: {
    listWrapperType() {
      return this.draggable ? 'draggable' : 'div';
    },
    orderedItems: {
      get() {
        return this.items;
      },
      set(newItems) {
        this.$emit('change', newItems);
      },
    },
    itemNames() {
      return this.orderedItems.map((item) => item.name);
    },
  },
  methods: {
    onChangeCheckbox(checked) {
      const hiddenChecked = checked.filter((itemName) => !this.itemNames.includes(itemName));
      const visibleOrderedChecked = this.itemNames.filter((itemName) => checked.includes(itemName));
      this.$emit('input', [...hiddenChecked, ...visibleOrderedChecked]);
    },
    onStartDrag() {
      this.dragging = true;
    },
    onEndDrag() {
      this.dragging = false;
    },
  },
};
</script>

<style lang="scss">
  .x-checkbox-list {
    margin-top: 8px;
    overflow: auto;
    height: 360px;
    line-height: 22px;

    .list {
      display: grid;
      grid-template-columns: 1fr 1fr;
      font-size: 12px;
      color: $theme-black;

      &__item {
        background: $theme-white;
        display: flex;
        padding-right: 16px;
        border-color: transparent;
        border-width: 1px 0px;
        border-style: solid;

        .x-icon {
          visibility: hidden;
          color: $grey-3;
          font-size: 16px;
          min-width: 16px;
          width: 16px;
          margin: 4px -6px 0 -4px;
          transform: rotate(90deg);
          position: relative;
          top: -2px;
          cursor: move;
        }

        .x-checkbox {
          margin-left: -4px;
        }
      }

      &.draggable {
        .list__item:not(.dragging):hover {
          border-color: $grey-2;

          .x-icon {
            visibility: visible;
          }
        }

        .ghost {
          border: 1px solid rgba($theme-blue, 0.4);
        }
      }

    }
  }
</style>
