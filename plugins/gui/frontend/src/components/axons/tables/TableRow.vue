<template>
  <tr
    class="x-table-row"
    :class="[{clickable: clickable && !readOnly, selected}, getRowClass]"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
  >
    <td
      v-if="selected !== undefined && multipleRowSelection"
      class="w-14 top"
    >
      <x-checkbox
        :data="selected"
        :read-only="readOnly"
        @change="onSelect"
      />
    </td>
    <td
      v-if="expandable"
      class="top"
    >
      <XIcon
        :class="expandRow ? 'active' : ''"
        :type="expandRow ? 'up' : 'down'"
        @click.native.stop="onToggleExpand"
      />
    </td>
    <td
      v-for="schema in fields"
      :key="schema.name"
      nowrap
      :class="`table-td-${schema.name}`"
    >
      <slot
        v-bind="{schema, data, sort, filter: filters[schema.name],
                 hoverRow, expandRow, formatTitle}"
      />
    </td>
  </tr>
</template>

<script>
import _isFunction from 'lodash/isFunction';
import xCheckbox from '../inputs/Checkbox.vue';
import { validateClassName } from '../../../constants/utils';

export default {
  name: 'XTableRow',
  components: {
    xCheckbox,
  },
  props: {
    data: {
      type: [String, Number, Boolean, Array, Object],
      required: true,
    },
    fields: {
      type: Array,
      required: true,
    },
    sort: {
      type: Object,
      default: () => ({ field: '', desc: true }),
    },
    filters: {
      type: Object,
      default: () => ({}),
    },
    selected: {
      type: Boolean,
    },
    expandable: {
      type: Boolean,
      default: false,
    },
    clickable: {
      type: Boolean,
      default: false,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
    rowClass: {
      type: [Function, String],
      default: '',
    },
    formatTitle: {
      type: Function,
      default: null,
    },
    multipleRowSelection: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      hoverRow: false,
      expandRow: false,
    };
  },
  computed: {
    getRowClass() {
      let value = this.rowClass;
      if (_isFunction(value)) {
        value = value(this.data);
      }
      if (!validateClassName(value)) {
        return '';
      }
      return value;
    },
  },
  methods: {
    onEnter() {
      this.hoverRow = true;
    },
    onLeave() {
      this.hoverRow = false;
    },
    onToggleExpand() {
      this.expandRow = !this.expandRow;
    },
    onSelect(selected) {
      this.$emit('input', selected);
    },
  },
};
</script>

<style lang="scss">
  .x-table-row {
    height: 30px;

    &:nth-child(odd) {
      background: rgba($grey-1, 0.6);

      .svg-bg {
        fill: rgba($grey-1, 0.6);
      }
    }

    &.clickable:hover {
      cursor: pointer;
      background-color: rgba($theme-blue, 0.2);

      .v-chip {
        cursor: pointer;
      }
    }

    &.selected {
      background-color: rgba($theme-blue, 0.2);
    }

    td {
      line-height: 24px;

      &.top {
        vertical-align: top;

        .x-checkbox {
          height: 24px;
        }
      }
    }

    .x-data {
      display: flex;
    }

    .array {
      min-height: 24px;
    }

    .x-icon {
      &:hover, &.active {
        color: $theme-orange;
      }
    }

    .svg-bg {
      fill: $theme-white;
    }

  }
</style>
