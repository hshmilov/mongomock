<template>
  <tr
    class="x-table-row"
    :class="{clickable: clickable && !readOnly, selected}"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
  >
    <td
      v-if="selected !== undefined"
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
      <md-icon
        v-if="expandRow"
        class="active"
        @click.native.stop="collapseRow"
      >expand_less</md-icon>
      <md-icon
        v-else
        @click.native.stop="onToggleExpand"
      >expand_more</md-icon>
    </td>
    <td
      v-for="schema in fields"
      :key="schema.name"
      nowrap
    >
      <slot v-bind="{schema, data, sort, filter: filters[schema.name], hoverRow, expandRow}" />
    </td>
  </tr>
</template>

<script>
  import xCheckbox from '../inputs/Checkbox.vue'

  export default {
    name: 'XTableRow',
    components: {
      xCheckbox
    },
    props: {
      data: {
        type: [String, Number, Boolean, Array, Object],
        required: true
      },
      fields: {
        type: Array,
        required: true
      },
      sort: {
        type: Object,
        default: () => {
          return { field: '', desc: true }
        }
      },
      filters: {
        type: Object,
        default: () => {
          return {}
        }
      },
      selected: {
        type: Boolean
      },
      expandable: {
        type: Boolean,
        default: false
      },
      clickable: {
        type: Boolean,
        default: false
      },
      readOnly: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        hoverRow: false,
        expandRow: false
      }
    },
    methods: {
      onEnter () {
        this.hoverRow = true
      },
      onLeave () {
        this.hoverRow = false
      },
      onToggleExpand () {
        this.expandRow = !this.expandRow
      },
      onSelect(selected) {
        this.$emit('input', selected)
      }
    }
  }
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
            box-shadow: 0 2px 16px -4px $grey-4;
        }

        &.selected {
            background-color: rgba($theme-blue, 0.2);
        }

        td {
            line-height: 24px;

            &.top {
              vertical-align: top;
            }
        }

        .x-data {
            display: flex;
        }

        .array {
            min-height: 24px;
        }

        .md-icon {
            &:hover, &.active {
                color: $theme-orange;
            }
        }

        .svg-bg {
            fill: $theme-white;
        }

    }
</style>