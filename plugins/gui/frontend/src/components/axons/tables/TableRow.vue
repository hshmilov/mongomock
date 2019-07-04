<template>
  <tr
    class="x-table-row"
    :class="{clickable: clickable && !readOnly, selected}"
    @mouseenter="enterRow"
    @mouseleave="leaveRow"
  >
    <td
      v-if="selected !== undefined"
      class="w-14"
    >
      <x-checkbox
        :data="selected"
        :read-only="readOnly"
        @change="onSelect"
      />
    </td>
    <td v-if="expandable">
      <md-icon
        v-if="expanded"
        class="active"
        @click.native.stop="collapseRow"
      >expand_less</md-icon>
      <md-icon
        v-else
        @click.native.stop="expandRow"
      >expand_more</md-icon>
    </td>
    <td
      v-for="schema in fields"
      :key="schema.name"
      nowrap
    >
      <slot
        :schema="schema"
        :data="data"
        :sort="sort"
        :hover-row="hovered"
        :expand-row="expanded"
      >
        <x-table-data
          :schema="schema"
          :data="data"
          :sort="sort"
        />
      </slot>
    </td>
  </tr>
</template>

<script>
  import xTableData from './TableData.vue'
  import xCheckbox from '../inputs/Checkbox.vue'

  export default {
    name: 'XTableRow',
    components: {
      xTableData, xCheckbox
    },
    props: {
      data: {
        type: Object,
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
        hovered: false,
        expanded: false
      }
    },
    methods: {
      enterRow () {
        this.hovered = true
      },
      leaveRow () {
        this.hovered = false
      },
      expandRow () {
        this.expanded = true
      },
      collapseRow () {
        this.expanded = false
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
            vertical-align: top;
            line-height: 24px;
        }

        .x-data {
            display: flex;
        }

        .array {
            min-height: 24px;
        }

        .md-icon {
            width: 14px;
            min-width: 14px;
            &:hover, &.active {
                color: $theme-orange;
            }
        }

        .svg-bg {
            fill: $theme-white;
        }

    }
</style>