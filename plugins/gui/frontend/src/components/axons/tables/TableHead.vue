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
      v-if="filterVisible || filterActive || filter"
      :title="filter || undefined"
      class="filter"
    >
      <x-search-input
        v-if="filterActive"
        :value="filter"
        :placeholder="filterPlaceholder"
        @input="(val) => $emit('filter', val)"
        @keyup.enter.native.stop="toggleColFilter"
      />
      <md-icon
        :class="{disabled: filterDisabled, active: filterActive}"
        @click.native.stop="toggleColFilter"
      >filter_list</md-icon>
    </div>
  </th>
</template>

<script>
  import xSearchInput from '../../neurons/inputs/SearchInput.vue'

  export default {
    name: 'XTableHead',
    components: {
      xSearchInput
    },
    props: {
      field: {
        type: Object,
        required: true
      },
      sortable: {
        type: Boolean,
        default: false
      },
      sort: {
        type: Object,
        default: () => {
          return { field: '', desc: true }
        }
      },
      filter: {
        type: String,
        default: undefined
      },
      filterable: {
        type: Boolean,
        default: true
      }
    },
    computed: {
      name () {
        return this.field.name
      },
      title () {
        return this.field.title
      },
      logo () {
        return this.field.logo
      },
      sortClass () {
        if (this.sort.field !== this.name) return ''
        if (this.sort.desc) return 'down'
        return 'up'
      },
      isString () {
        return this.field.type === 'string' && this.field.format !== 'date-time'
      },
      isArrayOfStrings () {
        return this.field.items.type === 'string'
      },
      isObjectWithString () {
        return Array.isArray(this.field.items) && this.field.items.find(item => item.type === 'string')
      },
      isArrayOfObjectsWithString () {
        return this.field.items.items && Array.isArray(this.field.items.items) &&
                this.field.items.items.find(item => item.type === 'string')
      },
      isArrayWithString () {
        return this.isArrayOfStrings || this.isObjectWithString || this.isArrayOfObjectsWithString
      },
      filterableType () {
        return this.isString || (this.field.type === 'array' && this.isArrayWithString)
      },
      filterDisabled () {
        return !this.filterableType || !this.filterable || this.filter === undefined
      },
      filterPlaceholder () {
        return `Show only ${this.title}...`
      }
    },
    data () {
      return {
        filterVisible: false,
        filterActive: false
      }
    },
    methods: {
      emitClick () {
        this.$emit('click', this.name)
      },
      enterCol () {
        if (this.filterable && this.filterableType) {
          this.filterVisible = true
        }
      },
      leaveCol () {
        this.filterVisible = false
      },
      toggleColFilter () {
        if (!this.filterable) {
          return
        }
        this.filterActive = !this.filterActive
      }
    }
  }
</script>

<style lang="scss">
  .x-table-head {
    min-width: 120px;

    .filter {
      position: absolute;
      bottom: 0;
      left: 0;
      display: flex;
      justify-content: flex-end;
      align-items: center;
      width: calc(100% - 4px);

      .md-icon {
        font-size: 16px !important;
        margin: 0;
        height: 28px;
        cursor: pointer;

        &:not(.disabled) {

          &:hover, &.active {
            color: $theme-orange;
          }
        }

        &.disabled {
          pointer-events: none;
        }
      }

      .x-search-input {
        width: calc(100% - 24px);
        height: 28px;
      }
    }

    &.sortable {
      cursor: pointer;

      .sort {
        position: relative;
        display: inline-block;
        height: 4px;
        width: 16px;
        margin: 0 8px;

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