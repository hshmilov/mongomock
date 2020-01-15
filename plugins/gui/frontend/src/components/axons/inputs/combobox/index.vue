<template>
  <!-- render this if not in keepOpen state -->
  <v-combobox
    v-if="!keepOpen"
    ref="combobox"
    v-model="selectedItems"
    class="x-combobox"
    :items="mergedItemsList"
    :search-input.sync="searchField"
    :hide-no-data="!allowCreateNew"
    :placeholder="label"
    item-color="transparent"
    color="black"
    :height="height"
    background-color="#fff"
    hide-details
    multiple
    dense
    chips
    :allow-overflow="false"
    :prepend-inner-icon="prependIcon"
    :menu-props="menuProps"
    v-on="$listeners"
  >
    <!-- slot for rendering the selected items -->
    <template v-slot:selection="{ item, index }">
      <v-chip
        v-if="index < selectionDisplayLimit"
        class="tag"
      >
        <span :title="item">{{ item }}</span>
      </v-chip>
      <span
        v-else-if="index === (selectionDisplayLimit)"
        class="grey--text caption"
      >(+{{ value.length - selectionDisplayLimit }} others)</span>
    </template>

    <!-- slot for rendering item in menu -->
    <template v-slot:item="{ index, item }">
      <div
        :title="item"
        class="x-combobox__list-item-container"
      >
        <v-checkbox
          :input-value="isSelectedItem(item)"
          :indeterminate="isIndeterminateItem(item)"
          :label="item"
          color="black"
        />
        <v-chip
          v-if="isNewItem(item)"
          x-small
          class="ma-2"
          color="secondary"
          outlined
        >New</v-chip>
      </div>
    </template>

    <!-- slot for create-new and quick-selection actions -->
    <template
      v-if="allowCreateNew || !hideQuickSelections"
      v-slot:append-item
    >
      <!-- create-new -->
      <v-list-item v-if="showCreateNew">
        <v-list-item-content>
          <v-list-item-title
            class="x-combobox_create-new-item"
            @click.stop="addNewItem"
          >
            {{ searchField }}<span class="x-combobox_create-new-item--spaces">(create new)</span>
          </v-list-item-title>
        </v-list-item-content>
      </v-list-item>

      <!-- quick selections -->
      <v-list-item
        v-if="!hideQuickSelections"
        class="comnobox__quick-selections"
      >
        <v-list-item-content>
          <v-list-item-title>
            <v-btn
              text
              small
              color="secondary"
              @click="selectAll"
            >Select All</v-btn>
            <v-btn
              text
              small
              color="secondary"
              @click="clearSelections"
            >Clear All</v-btn>
          </v-list-item-title>
        </v-list-item-content>
      </v-list-item>
    </template>

    <!-- slot for rendering create-new action when the query has no matching results -->
    <template
      v-if="searchField"
      v-slot:no-data
    >
      <v-list-item>
        <v-list-item-content>
          <v-list-item-title
            class="x-combobox_create-new-item"
            @click.stop="addNewItem"
          >
            {{ searchField }}<span class="x-combobox_create-new-item--spaces">(create new)</span>
          </v-list-item-title>
        </v-list-item-content>
      </v-list-item>
    </template>
  </v-combobox>

  <!-- render this is in keepOpen -->
  <div v-else>
    <v-text-field
      ref="inputFiled"
      v-model="searchField"
      class="x-combobox_text-field--keep-open"
      prepend-inner-icon="mdi-magnify"
      :placeholder="label"
      solo
      color="rgba(0, 0, 0, 0.54)"
      dense
      @keyup.enter="addNewItem"
    />

    <v-card
      height="420"
      allow-overflow
      class="x-combobox_results-card--keep-open"
    >
      <section class="x-combobox_results-card--keep-open--scrollable">
        <!-- render items -->
        <v-list
          flat
        >
          <v-list-item-group
            v-model="selectedItems"
            multiple
            dense
          >
            <v-list-item
              v-for="item in mergedItemsList"
              v-show="keepOpen__mergedItemsList.includes(item)"
              :key="item"
              :value="item"
            >
              <template v-slot:default="{ active, toggle }">
                <v-list-item-action>
                  <v-checkbox
                    :class="getCheckBoxClass(active, item)"
                    :input-value="active"
                    :indeterminate="isIndeterminateItem(item)"
                    @click.stop="toggle"
                  />
                </v-list-item-action>
                <v-list-item-content>
                  <v-list-item-title v-text="item" />
                </v-list-item-content>
                <v-chip
                  v-if="isNewItem(item)"
                  x-small
                  class="ma-2"
                  color="secondary"
                  outlined
                >New</v-chip>
              </template>
            </v-list-item>
          </v-list-item-group>
        </v-list>

        <!-- render create-new actions -->
        <v-list-item
          v-if="keepOpen__showCreateNew"
          class="create-new"
        >
          <v-list-item-content>
            <v-list-item-title
              class="x-combobox_create-new-item"
              @click.stop="addNewItem"
            >
              {{ searchField }}<span class="x-combobox_create-new-item--spaces">(create new)</span>
            </v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </section>

      <!-- render quick-selecions -->
      <v-card-actions v-if="!hideQuickSelections">
        <v-btn
          text
          small
          color="secondary"
          @click="selectAll"
        >Select All</v-btn>
        <v-btn
          text
          small
          color="secondary"
          @click="clearSelections"
        >Clear All</v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>

<script>
import _isEmpty from 'lodash/isEmpty';
import _trim from 'lodash/trim';

function compare(item1, item2) {
  // 2 levels of comparison
  // first: by type ([0] selected items, [1] indeterminate items, [2] unselected items)
  // second: alphabetical order
  const typeClassifier = (item) => {
    if (this.value.includes(item)) {
      // type of selected
      return 0;
    }
    if (this.indeterminate.includes(item)) {
      // type of indeterminate
      return 1;
    }
    // type of new
    return 2;
  };

  const type1 = typeClassifier(item1);
  const type2 = typeClassifier(item2);

  return type1 - type2 || item1.toLowerCase().localeCompare(item2.toLowerCase());
}

export default {
  name: 'Xcombobox',
  props: {
    label: {
      type: String,
      default: 'Add or Search items',
    },
    value: {
      type: Array,
      default: () => [],
    },
    items: {
      type: Array,
      default: () => [],
    },
    indeterminate: {
      type: Array,
      default: () => [],
    },
    selectionDisplayLimit: {
      type: Number,
      default: 3,
    },
    multiple: {
      type: Boolean,
      default: false,
    },
    keepOpen: {
      type: Boolean,
      default: false,
    },
    hideQuickSelections: {
      type: Boolean,
      default: true,
    },
    allowCreateNew: {
      type: Boolean,
      default: true,
    },
    height: {
      type: String,
      default: '',
    },
    prependIcon: {
      type: String,
      default: '',
    },
    menuProps: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      showCreateNewForSubMatches: true,
      searchField: null,
      sortedItems: [...this.items].sort(compare.bind(this)),
      newItems: [],
      sourceData: {
        indeterminate: new Set(this.indeterminate),
      },
    };
  },
  computed: {
    selectedItems: {
      get() {
        return this.value;
      },
      set(newSelections) {
        /**
        when in regular (not keep open) mode, adding new is not going
        through the pipeline of addNewItem method.
        selectedItem is in 2-way-binding with the Combobox component,
        and that is the reason why the decision whether to add items into the "new" array made here
        */
        this.insertIntoNewItemsIfNew(newSelections);
        const selections = this.handleIndeterminateItems(newSelections);

        this.$emit('input', selections);
      },
    },
    sortedNewItems() {
      return [...this.newItems].sort();
    },
    mergedItemsList() {
      // return a merged list of predefined items, and new items generated on runtime.

      const mergedItems = [...this.sortedNewItems, ...this.sortedItems];
      return mergedItems;
    },
    keepOpen__mergedItemsList() {
      return this.searchField
        ? this.mergedItemsList.filter(this.keepOpen__filterItems)
        : this.mergedItemsList;
    },
    showCreateNew() {
      return this.allowCreateNew
      && this.showCreateNewForSubMatches
      && !_isEmpty(_trim(this.searchField));
    },
    keepOpen__showCreateNew() {
      // if the query sting is empty - dont show create new section
      if (_isEmpty(_trim(this.searchField))) {
        return false;
      }

      // if there are no results matching the query string,
      // show create-new section (if allowed [prop])
      const noMatchFound = this.keepOpen__mergedItemsList.length === 0;
      if (this.allowCreateNew && noMatchFound) {
        return true;
      }


      // eslint-disable-next-line max-len
      const exactMatchFound = this.keepOpen__mergedItemsList.findIndex((item) => item.toLocaleLowerCase() === this.searchField.toLocaleLowerCase()) > -1;

      // if not exact match found, show create-new (if allowed [prop])
      return this.allowCreateNew && !exactMatchFound;
    },
  },
  mounted() {
    if (!this.keepOpen && this.allowCreateNew) {
      this.$watch(
        () => this.$refs.combobox.filteredItems,
        (results) => {
          this.determineWhetherDisplayCreateNew(results);
        },
      );
    }
  },
  methods: {
    focusInput() {
      if (this.keepOpen) {
        this.$refs.inputFiled.focus();
      } else {
        this.$refs.combobox.focus();
      }
    },
    addNewItem() {
      const newitemValue = _trim(this.searchField);
      if (!newitemValue || this.mergedItemsList.includes(newitemValue)) {
        return;
      }
      const newSelections = [...this.selectedItems, this.searchField];
      this.selectedItems = newSelections;
      this.searchField = '';
      this.focusInput();
    },
    selectAll() {
      this.$emit('input', [...this.mergedItemsList]);
      this.$emit('update:indeterminate', []);
      this.$emit('change');
    },
    clearSelections() {
      this.$emit('input', []);
      this.$emit('update:indeterminate', []);
      this.$emit('change');
    },
    isSelectedItem(item) {
      return this.selectedItems.includes(item);
    },
    isNewItem(item) {
      return this.newItems.includes(item);
    },
    isIndeterminateItem(item) {
      return this.indeterminate.includes(item);
    },
    handleIndeterminateItems(newValue) {
      let selections = [...newValue];
      const recentlySelectedItem = newValue.find((item) => !this.selectedItems.includes(item));

      /**
             * items that originally marked as indetermiated, walk through a 3 states cycle
             * indeterminate -> selected -> unselected -> indeterminate [again]
             */
      if (this.sourceData.indeterminate.has(recentlySelectedItem)) {
        if (this.indeterminate.includes(recentlySelectedItem)) {
          // from: inderterminate ---> into: selected
          this.removeItemFromIndeterminate(recentlySelectedItem);
        } else {
          // from: unselected ---> into: indetermnate
          this.insertItemIntoIndeterminate(recentlySelectedItem);

          // element should be filtered out from selections
          selections = newValue.filter((item) => item !== recentlySelectedItem);
        }
      }

      return selections;
    },
    removeItemFromIndeterminate(recentlySelectedItem) {
      this.$emit('update:indeterminate', this.indeterminate.filter((item) => item !== recentlySelectedItem));
    },
    insertItemIntoIndeterminate(recentlySelectedItem) {
      this.$emit('update:indeterminate', [...this.indeterminate, recentlySelectedItem]);
    },
    insertIntoNewItemsIfNew(newValue) {
      const recentAddedItem = newValue.slice().pop();
      // eslint-disable-next-line max-len
      const isNewItem = !this.items.includes(recentAddedItem) && !this.newItems.includes(recentAddedItem);
      if (recentAddedItem && isNewItem) {
        this.newItems = [...this.newItems, recentAddedItem];
      }
    },
    determineWhetherDisplayCreateNew(results) {
      const searchTermEmpty = !this.searchField;
      const resultsExist = !_isEmpty(results);

      if (searchTermEmpty) {
        this.showCreateNewForSubMatches = true;
        return;
      }

      if (!resultsExist) {
        this.showCreateNewForSubMatches = false;
        return;
      }

      // eslint-disable-next-line max-len
      const exactMatchNotFoud = this.mergedItemsList.findIndex((item) => item.toLocaleLowerCase() === this.searchField.toLocaleLowerCase()) < 0;

      this.showCreateNewForSubMatches = Boolean(exactMatchNotFoud);
    },
    keepOpen__filterItems(item) {
      return item.toLocaleLowerCase().indexOf(this.searchField.toLocaleLowerCase()) > -1;
    },
    keepOpen__onCheckboxChange(value, item) {
      if (value || this.indeterminate.includes(item)) {
        this.selectedItems = [...this.selectedItems, item];
      } else {
        this.selectedItems = this.selectedItems.filter((i) => i !== item);
      }
    },
    getCheckBoxClass(active, item) {
      const indeterminateOrUnchecked = this.isIndeterminateItem(item) ? 'checkbox--partial' : 'checkbox--unchecked';
      return active ? 'checkbox--checked' : indeterminateOrUnchecked;
    },
  },
};
</script>

<style lang="scss">

  $checkbox-color: rgba(0, 0, 0, 0.87) !important;
  $item-font-size: 14px;

  @mixin style-checkbox {
    color: $checkbox-color;
    .v-input--checkbox {
      margin: 0 5px 0 0;
      padding: 0;

      .accent--text {
        color: $checkbox-color;
      }
    }
    .v-messages{
      display: none;
    }

    .theme--light.v-icon {
      color: $checkbox-color;
    }
  }

  @mixin input-element-spacing {
    // fix vertical centering inside combobox menu items

    .v-input__slot {
        margin: 0 !important;
        padding: 0 4px;

        label {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          display: inline-block !important;
        }
    }

    .v-list-item {
      min-height: 20px;
      padding: 0;

      .v-list-item__content {
        padding: 2px 0;
        font-size: 12px;
      }
    }
  }

  @mixin label-element-styling {
     // fix label positioning
    .v-label {
      font-size: 14px !important;
      top: 11px;
      left: 8px !important;

      &--active {
        top: 0;
        left: 0 !important;
      }
    }
  }

  .x-combobox_text-field--keep-open {
    .v-input__slot {
      margin-bottom: 2px;
    }
    .v-text-field__details {
      display: none;
    }
    input {
      border-style: none !important;
    }

  }

  .x-combobox_create-new-item {
    border-top: 0.5px solid;
    border-bottom: 0.5px solid;
    border-color: $checkbox-color;
    padding: 8px 8px !important;
    cursor: pointer;
    margin-top: 10px;
    &--spaces {
      padding-left: 8px;
      color: $theme-blue;
    }
  }
  .x-combobox_results-card--keep-open {
    @include style-checkbox;
    @include input-element-spacing;

    position: relative;

    &--scrollable {
      overflow-y: auto;
      height: 100%;
    }

    .v-list-item__title {
      font-size: $item-font-size;
      color: black;
      display: flex;
      flex-direction: row;
      align-items: center;
      .v-label {
        font-size: $item-font-size;
        color: black;
      }

      .v-chip {
        margin: 0 !important;
      }
    }

    .v-list-item__action {
      margin-right: 4px !important;
      margin-top: 0px;
      margin-bottom: 0px;
    }

    .v-card__actions {
      position: absolute !important;
      width: 100%;
      bottom: 0;
      background-color: #fff;
    }
  }

  .x-combobox {
    @include input-element-spacing;
    @include label-element-styling;

    // eliminate the border-style inset
    input, textarea {
        border-style: none !important;
    }

    &__list-item-container {
      width: 95%;
      display: flex;
      justify-content: space-between;
      .v-label {
        display: block;
        text-overflow: ellipsis;
        overflow: hidden;
        white-space: nowrap;
      }
    }

    // fix bug that input cover the label when not in active mode
    .v-select__selections {
      .v-chip {
        max-width: 60%;
        span {
          justify-content: space-between;
          text-overflow: ellipsis;
          overflow: hidden;
          white-space: nowrap;
        }
      }
      input {
        padding: 0 8px !important;
        background-color: transparent;
      }
    }
  }

  .v-menu__content {
    @include style-checkbox;
    @include input-element-spacing;
    z-index: 1004 !important;

    .comnobox__quick-selections {
      padding: 0;
      border-top: 0.5px solid rgba(0, 0, 0, 0.12);
    }
  }
</style>
