<template>
  <th
    class="x-table-head"
    :class="{ sortable }"
    nowrap
    @click="emitClick"
    @keyup.enter.stop="emitClick"
    @mouseenter="enterCol"
    @mouseleave="leaveCol"
  >
    <div class="inner-th">
      <img
        v-if="logo"
        class="logo md-image"
        :src="require(`Logos/adapters/${logo}.png`)"
        height="20"
        :alt="logo"
        :title="logo"
      >{{ title }}<div
        v-if="sortable"
        :class="`sort ${sortClass}`"
      />
      <div
        class="filter"
        @click.stop="toggleColFilter"
      >
        <VIcon
          v-if="!hasFilter && (filterVisible || Boolean(filterColumnName === field.name))"
          :class="{filterable: true, disabled: filterDisabled, active: Boolean(filterColumnName === field.name)}"
        >
          $vuetify.icons.filterable
        </VIcon>
        <VIcon
          v-if="hasFilter"
          class="funnel"
        >
          $vuetify.icons.funnel
        </VIcon>
      </div>
    </div>
  </th>
</template>

<script>

export default {
  name: 'XTableHead',
  props: {
    field: {
      type: Object,
      required: true,
    },
    sortable: {
      type: Boolean,
      default: false,
    },
    sort: {
      type: Object,
      default: () => ({ field: '', desc: true }),
    },
    filterColumnName: {
      type: String,
      default: '',
    },
    filterable: {
      type: Boolean,
      default: true,
    },
    hasFilter: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      filterVisible: false,
    };
  },
  computed: {
    name() {
      return this.field.name;
    },
    title() {
      return this.field.title;
    },
    logo() {
      return this.field.logo;
    },
    sortClass() {
      if (this.sort.field !== this.name) return '';
      if (this.sort.desc) return 'down';
      return 'up';
    },
    isString() {
      return this.field.type === 'string' && this.field.format !== 'date-time';
    },
    isArrayOfStrings() {
      return this.field.items.type === 'string';
    },
    isObjectWithString() {
      return Array.isArray(this.field.items) && this.field.items.find((item) => item.type === 'string');
    },
    isArrayOfObjectsWithString() {
      return this.field.items.items && Array.isArray(this.field.items.items)
                && this.field.items.items.find((item) => item.type === 'string');
    },
    isArrayWithString() {
      return this.isArrayOfStrings || this.isObjectWithString || this.isArrayOfObjectsWithString;
    },
    filterableType() {
      return (this.isString || (this.field.type === 'array' && this.isArrayWithString))
        && this.field.filterable;
    },
    filterDisabled() {
      return !this.filterableType || !this.filterable || this.filter === undefined;
    },
  },
  methods: {
    emitClick() {
      this.$emit('click', this.name);
    },
    enterCol() {
      if (this.filterable && this.filterableType) {
        this.filterVisible = true;
      }
    },
    leaveCol() {
      this.filterVisible = false;
    },
    toggleColFilter() {
      if (!this.filterable) {
        return;
      }
      this.$emit('toggleColumnFilter', this.name);
    },
  },
};
</script>

<style lang="scss">
  .x-table-head {
    min-width: 120px;

    .inner-th {
      display: flex;
    }

    .filter {
      cursor: pointer;
      width: 14px;
      margin-left: auto;

      svg {
        height: 15px;
        width: 15px;
      }

      &:not(.disabled) {

        .active {
          rect {
            fill: $theme-orange;
          }
          path {
            stroke: #fff;
          }
        }
      }

      &.disabled {
        pointer-events: none;
      }

    }

    > .logo {
      margin-right: 4px;
    }

    &.sortable {
      cursor: pointer;

      .sort {
        position: relative;
        display: inline-block;
        height: 4px;
        width: 16px;
        margin: 16px 0 0 8px;

        &.up:before {
          @include triangle('up', $color: $grey-4);
          top: -2px;
        }

        &.down:after {
          @include triangle('down', $color: $grey-4);
          top: 4px;
        }
      }

      &:hover .sort {

        &.down:before {
          @include triangle('up', $color: rgba($grey-4, 0.6));
          top: -2px;
        }

        &:not(.down):not(.up):after {
          @include triangle('down', $color: rgba($grey-4, 0.6));
          top: 4px;
        }
      }
    }
  }
</style>
