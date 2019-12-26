<template>
  <v-select
    ref="select"
    v-model="selection"
    :items="filteredItems"
    :menu-props="{
      maxHeight: 480,
      minWidth: '100%'
    }"
    :multiple="multiple"
    item-text="title"
    item-value="name"
    no-data-text=""
    dense
    attach=""
    :class="{'v-select--open': keepOpen}"
    class="v-text-field--outlined"
  >
    <template #prepend-item>
      <x-search-input
        ref="search"
        v-model="searchInput"
        placeholder=""
        @keydown.tab.native.stop.prevent=""
        @keyup-enter="addNewItem"
      >
        <span
          v-if="!searchInput"
          class="x-search-input__placeholder"
        >{{ searchPlaceholder }}</span>
      </x-search-input>
    </template>

    <template #selection="{ item, index }">
      <v-chip
        v-if="index < selectionDisplayLimit"
        class="selection"
        :title="item.text"
      >
        <span>{{ item.title }}</span>
      </v-chip>
      <span
        v-if="index === selectionDisplayLimit"
        class="selection__remainder"
        :title="selection.join('  ')"
      >(+{{ selection.length - selectionDisplayLimit }} others)</span>
    </template>

    <template
      #item="{ attrs, item, parent, selected }"
      :ripple="false"
    >
      <v-checkbox
        v-if="multiple"
        :ripple="false"
        :input-value="attrs.inputValue"
        :indeterminate="indeterminate.includes(item.title)"
      />
      <span
        class="item-text"
        :class="{'item-text--new': item.isNew }"
        :title="item.title"
      >{{ item.title }}</span>
      <v-chip
        v-if="item.isNew"
        outlined
      >New</v-chip>
    </template>
    <template #append-item>
      <div
        v-if="searchInput.length > 0 && isNewItem"
        class="new-item"
        @click="addNewItem"
      >
        <span
          class="new-item__content"
          :title="searchInput"
        >{{ searchInput }}</span>
        <span class="new-item__marker">(create new)</span>
      </div>
    </template>
  </v-select>
</template>

<script>
import xSearchInput from '../../../neurons/inputs/SearchInput.vue';

export default {
  name: 'XSelectBox',
  components: { xSearchInput },
  props: {
    value: {
      type: Array,
      default: () => []
    },
    items: {
      type: Array,
      default: () => []
    },
    indeterminate: {
      type: Array,
      default: () => []
    },
    searchPlaceholder: {
      type: String,
      default: 'Add or Search items'
    },
    selectionDisplayLimit: {
      type: Number,
      default: 3
    },
    multiple: {
      type: Boolean,
      default: false
    },
    keepOpen: {
      type: Boolean,
      default: false
    }

  },
  data() {
    return {
      // For filtering items from the list
      searchInput: '',

      // Sort alphabetically ascending, with selected items first, indeterminate next and lastly non-selected
      sortedItems: [ ...this.items ].sort((item1, item2) => {
        const title1 = item1.title
        const title2 = item2.title
        return (this.value.includes(title2) - this.value.includes(title1) ||
                this.indeterminate.includes(title2) - this.indeterminate.includes(title1) ||
               title1.toLowerCase().localeCompare(title2.toLowerCase()))
      }),

      baseIndeterminate: new Set([ ...this.indeterminate ])
    }
  },
  computed: {
    filteredItems () {
      return this.sortedItems.filter(
              item => item.title.toLowerCase().includes(this.searchInput.toLowerCase()))
    },
    selection: {
      get() {
        return this.value;
      },
      set(newSelection) {
        // Indeterminate items go through a three-state cycle
        if (this.baseIndeterminate.size) {
          // Retrieve added item to check for special handling
          const addedItem = newSelection.find(item => !this.selection.includes(item))
          // selected --> non-selected - default behaviour (no addedItem and no need to change indeterminate)
          if (addedItem && this.baseIndeterminate.has(addedItem)) {
            if (this.indeterminate.includes(addedItem)) {
              // indeterminate --> selected - remove indeterminate
              this.$emit('update:indeterminate', this.indeterminate.filter(item => item !== addedItem))
            } else {
              // non-selected --> indeterminate - restore indeterminate mark and remove from selected
              newSelection = newSelection.filter(item => item !== addedItem)
              this.$emit('update:indeterminate', [ ...this.indeterminate, addedItem ])
            }
          }
        }
        this.$emit('input', newSelection)

      }
    },
    isNewItem() {
      return !this.sortedItems.find(item => item.title === this.searchInput)
    }
  },
  mounted() {
    // For the keepOpen option, menu should be constantly active
    if (this.keepOpen) {
      this.$refs.select.activateMenu()
    }
  },
  methods: {
    addNewItem() {
      if (!this.searchInput) {
        return
      }
      this.$emit('input', [...this.selection, this.searchInput])
      this.sortedItems.unshift({
        name: this.searchInput,
        title: this.searchInput,
        isNew: true
      })
      this.searchInput = ''
      this.$refs.search.focus()
    }
  }
}
</script>

<style lang="scss">

  .v-select {
    &--open {
      .v-menu__content {
        height: 480px;
      }

      .v-input__control .v-input__slot .v-select__slot .v-select__selections input {
        display: none;
      }
    }

    .v-menu__content {
      overflow-y: auto !important;
      box-sizing: content-box;
      border: 1px solid $theme-black;
      font-size: 12px;
      color: $theme-black;
      box-shadow: none;

      .v-card {
        box-shadow: none;
      }

      .v-list-item .v-input__slot {
        margin-bottom: 8px;

        .v-icon {
          color: $theme-black !important;
        }
      }

      .item-text, .new-item__content {
        display: inline-block;
        word-break: break-all;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }

    .x-search-input {
      position: sticky;
      width: auto;
      top: 0;
      left: 0;
      z-index: 1;
      display: flex;
      align-items: center;
      border-bottom-left-radius: 0;
      border-bottom-right-radius: 0;

      &.focus {
        border-color: transparent;
        border-bottom-color: rgba($theme-blue, 0.4);
      }

      &__placeholder {
        position: absolute;
        top: 0;
        left: 42px;
        color: $grey-4;
        font-size: 14px;
        line-height: 28px;
      }

      .input-value {
        pointer-events: all;
      }
    }

    .v-list--dense .v-list-item {
      height: 28px;
      min-height: 28px;
      padding-left: 12px;
      color: $theme-black !important;
      caret-color: $theme-black !important;
    }

    .v-list-item:not(.v-list-item--link):nth-child(2) {
      height: 0;
      min-height: 0;
    }

    .v-list {
      padding: 0;
    }

    .theme--light.v-list-item--active:not(.v-list-item--highlighted):before {
      opacity: 0;
    }

    .v-list-item__content {
      height: 0;
      padding: 0;
    }

    .new-item {
      cursor: pointer;
      display: flex;
      align-items: center;
      height: 28px;
      position: sticky;
      z-index: 2000;
      border-top: 1px solid $grey-4;
      border-bottom: 1px solid $grey-4;
      padding-left: 16px;

      &:hover {
        text-shadow: $text-shadow;
      }

      .new-item__marker {
        margin-left: 8px;
        margin-right: 16px;
        color: $theme-blue;
        flex: 1 0 auto;
      }
    }

    .selection {
      .v-chip {
        width: 60px !important;
        text-align: center;
        display: inline-block;
      }

      .v-chip__content span {
        text-overflow: ellipsis;
        overflow: hidden;
      }

      &__remainder {
        font-size: 0.75rem !important;
        font-weight: 400;
        letter-spacing: 0.03333em !important;
        line-height: 1.25rem;
        color: $grey-3 !important;
        caret-color: $grey-3 !important;
      }
    }

    .v-list-item .v-chip {
      font-size: 12px;
      height: 16px;
      line-height: 16px;
      color: $theme-blue;
      border-color: $theme-blue;
      width: 24px;
      cursor: inherit;
    }
  }
</style>
