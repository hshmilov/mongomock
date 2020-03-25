<template>
  <XDropdown
    class="x-query-search-input"
    :overflow="false"
    @activated="$emit('activated')"
  >
    <!-- Trigger is an input field containing a 'freestyle' query, a logical condition on fields -->
    <XSearchInput
      id="query_list"
      slot="trigger"
      ref="greatInput"
      v-model="inputValue"
      :placeholder="queryPlaceholder"
      :tabindex="-1"
      @keyup.enter.native.stop="submitFilter"
      @keyup.down.native="incQueryMenuIndex"
      @keyup.up.native="decQueryMenuIndex"
    >
      <template
        v-if="querySearchTemplate"
        v-slot:badge
      >
        <div class="search-input-badge">
          <VIcon
            size="16"
            color="#fff"
            class="search-input-badge__remove"
            @click.stop="removeSearchTemplate"
          >{{ closeSvgIconPath }}
          </VIcon>{{ querySearchTemplate.name }}
        </div>
      </template>
    </XSearchInput>
    <!--
      Content is a list composed of 4 sections:
      1. Specific type search, filtered to whose dynamic field contain the value 'searchValue'
      2. Saved queries, filtered to whose names contain the value 'searchValue'
      3. Historical queries, filtered to whose filter contain the value 'searchValue'
      4. Option to search for 'searchValue' everywhere in data (compares to every text field)
    -->
    <div
      slot="content"
      class="query-quick"
      @keyup.down="incQueryMenuIndex"
      @keyup.up="decQueryMenuIndex"
    >
      <XMenu
        v-if="templateViews && templateViews.length"
        id="specific_search_select"
      >
        <div class="menu-title">
          Search By
        </div>
        <div class="menu-content">
          <XMenuItem
            v-for="(item, index) in templateViews"
            :key="index"
            :title="item.name"
            @click="selectQuery(item)"
          />
        </div>
      </XMenu>
      <XMenu
        v-if="savedViews && savedViews.length"
        id="query_select"
      >
        <div class="menu-title">
          Saved Queries
        </div>
        <div class="menu-content">
          <XMenuItem
            v-for="(item, index) in savedViews"
            :key="index"
            :title="item.name"
            :selected="isSelectedSaved(index)"
            @click="selectQuery(item)"
          />
        </div>
      </XMenu>
      <XMenu v-if="historyViews && historyViews.length">
        <div class="menu-title">
          History
        </div>
        <div class="menu-content">
          <XMenuItem
            v-for="(item, index) in historyViews"
            :key="index"
            :title="item.view.query.filter"
            :selected="isSelectedHistory(index)"
            @click="selectQuery(item)"
          />
        </div>
      </XMenu>
      <XMenu v-if="searchValue && isSearchSimple">
        <XMenuItem
          :title="`Search in table: ${searchValue}`"
          :selected="isSelectedSearch"
          @click="searchText"
        />
      </XMenu>
      <div v-if="noResults">
        No results
      </div>
    </div>
  </XDropdown>
</template>

<script>
import { mapState, mapMutations, mapGetters } from 'vuex';
import _debounce from 'lodash/debounce';
import _get from 'lodash/get';
import _snakeCase from 'lodash/snakeCase';
import XDropdown from '@axons/popover/Dropdown.vue';
import XSearchInput from '@neurons/inputs/SearchInput.vue';
import XMenu from '@axons/menus/Menu.vue';
import XMenuItem from '@axons/menus/MenuItem.vue';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import { EXACT_SEARCH } from '@store/getters';
import { mdiClose } from '@mdi/js';
import { defaultViewForReset } from '@constants/entities';
import viewsMixin from '../../../../mixins/views';

export default {
  name: 'XQuerySearchInput',
  components: {
    XDropdown, XSearchInput, XMenu, XMenuItem,
  },
  mixins: [viewsMixin],
  props: {
    module: {
      type: String,
      required: true,
    },
    value: {
      type: String,
      default: '',
    },
    querySearch: {
      type: String,
      default: null,
    },
    userFieldsGroups: {
      type: Object,
      default: () => ({ default: [] }),
    },
  },
  data() {
    return {
      searchValue: '',
      queryMenuIndex: -1,
      closeSvgIconPath: mdiClose,
    };
  },
  computed: {
    ...mapState({
      savedViews(state) {
        if (!this.isSearchSimple) return state[this.module].views.saved.content.data || [];
        return state[this.module].views.saved.content.data
          .filter((item) => item && item.name.toLowerCase()
            .includes(this.searchValue.toLowerCase()));
      },
      historyViews(state) {
        if (!this.isSearchSimple) return state[this.module].views.saved.content.data;
        return state[this.module].views.history.content.data
          .filter((item) => item && item.view.query && item.view.query.filter
                                  && item.view.query.filter.toLowerCase()
                                    .includes(this.searchValue.toLowerCase()));
      },
      templateViews(state) {
        return _get(state[this.module].views, 'template.content.data', []);
      },
      currentView(state) {
        return state[this.module].view;
      },
    }),
    ...mapGetters({
      exactSearch: EXACT_SEARCH,
    }),
    inputValue: {
      get() {
        if (this.querySearch) {
          return this.querySearch;
        }
        if (!this.querySearchTemplate) {
          return this.value;
        }
        return this.searchValue;
      },
      set(value) {
        this.searchValue = value;
      },
    },
    queryPlaceholder() {
      if (this.querySearchTemplate) {
        return `Search by ${this.querySearchTemplate.name}`;
      }
      return 'Insert your query or start typing to filter recent queries';
    },
    isSearchSimple() {
      /* Determine whether current search input value is an AQL filter, or just text */
      if (!this.searchValue) return true;
      if (this.searchValue.indexOf('exists_in') !== -1) return false;
      const simpleMatch = this.searchValue.match('[a-zA-Z0-9 -._:]*');
      return simpleMatch && simpleMatch.length === 1 && simpleMatch[0] === this.searchValue;
    },
    noResults() {
      /* Determine whether there are no results to show in the search input dropdown */
      return (!this.searchValue || !this.isSearchSimple)
              && (!this.savedViews || !this.savedViews.length)
              && (!this.historyViews || !this.historyViews.length);
    },
    queryMenuCount() {
      /* Total items to appear in the search input dropdown */
      return this.savedViews.length
              + this.historyViews.length
              + (this.searchValue && this.isSearchSimple);
    },
    isSelectedSearch() {
      /* Determine whether the search in table option of the search input dropdown is selected  */
      return this.queryMenuIndex === this.queryMenuCount - 1;
    },
    textSearchPattern() {
      if (!this.searchValue) {
        return '';
      }
      /* Create a template for the search everywhere filter, from all currently selected fields */
      if (!this.currentView.fields || !this.currentView.fields.length) return '';
      const patternParts = [];
      this.currentView.fields.forEach((field) => {
        // Filter fields containing image data, since it is not relevant for searching
        if (field.includes('image')) return;
        if (this.exactSearch && !this.currentView.historical) {
          patternParts.push(`${field} == "{val}"`);
        } else {
          patternParts.push(`${field} == regex("{val}", "i")`);
        }
      });
      if (this.exactSearch && !this.currentView.historical) {
        patternParts.push('search("{val}")');
      }
      return patternParts.join(' or ');
    },
    querySearchTemplate() {
      return _get(this.currentView, 'query.meta.searchTemplate', false);
    },
  },
  created() {
    this.fetchViewsHistory();
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    removeSearchTemplate() {
      const resetView = defaultViewForReset(this.module, this.userFieldsGroups.default);
      this.updateView(resetView);
      this.$emit('done');
    },
    viewsCallback() {
      if (this.$route.query.view) {
        const requestedView = this.savedViews.find((view) => view.name === this.$route.query.view);
        if (requestedView) {
          this.selectQuery({
            view: requestedView.view,
            uuid: requestedView.uuid,
          });
        }
      }
    },
    selectQuery({ view, uuid }) {
      /* Load given view by settings current filter and expressions to it */
      let userDefinedFields = false;
      const viewToUpdateSearchTemplate = _get(view, 'query.meta.searchTemplate', false);
      const columnsGroupName = viewToUpdateSearchTemplate ? viewToUpdateSearchTemplate.name : false;
      if (columnsGroupName) {
        if (this.userFieldsGroups[_snakeCase(columnsGroupName)]) {
          userDefinedFields = this.userFieldsGroups[_snakeCase(columnsGroupName)];
        }
        this.searchValue = '';
      }
      this.updateView({
        module: this.module,
        view: {
          ...view,
          enforcement: null,
          ...(userDefinedFields) && { fields: userDefinedFields },
          page: 0,
        },
        uuid,
      });
      if (!this.querySearch) {
        this.searchValue = view.query.filter;
      }
      this.$emit('validate');
      this.focusInput();
      this.closeInput();
    },
    incQueryMenuIndex() {
      this.queryMenuIndex++;
      if (this.queryMenuIndex >= this.queryMenuCount) {
        this.queryMenuIndex = -1;
        this.focusInput();
      }
    },
    decQueryMenuIndex() {
      this.queryMenuIndex--;
      if (this.queryMenuIndex < -1) {
        this.queryMenuIndex = this.queryMenuCount - 1;
      } else if (this.queryMenuIndex === -1) {
        this.focusInput();
      }
    },
    submitFilter: _debounce(function submitFilter() {
      if (this.isSearchSimple) {
        // Search for value in all selected fields
        this.searchText();
      } else {
        // Use the search value as a filter
        this.$emit('input', this.searchValue);
      }
      this.$emit('validate');
      this.closeInput();
    }, 400, { leading: true, trailing: false }),
    searchText() {
      // Plug the search value in the template for filtering by any of currently selected fields
      // in case of search type mode this component will handle the search value
      if (this.querySearchTemplate) {
        this.$emit('update:query-search', null);
        this.$emit('input', this.parseSearchTemplateQuery(this.querySearchTemplate.searchField, this.inputValue));
      } else {
        this.$emit('update:query-search', this.searchValue);
        this.$emit('input', this.textSearchPattern.replace(/{val}/g, this.searchValue));
      }
      this.closeInput();
    },
    isSelectedSaved(index) {
      return this.queryMenuIndex === index;
    },
    isSelectedHistory(index) {
      return this.queryMenuIndex === index + this.savedViews.length;
    },
    focusInput() {
      this.$refs.greatInput.focus();
    },
    closeInput() {
      this.$refs.greatInput.$parent.close();
    },
    parseSearchTemplateQuery(searchField, searchValue) {
      if (!searchValue) {
        return '';
      }
      return `(${searchField} == regex('${searchValue}', 'i'))`;
    },
  },
};
</script>

<style lang="scss">
  .x-query-search-input {
    flex: 1 0 auto;

    .content {
      width: 100%;
    }

    .x-search-input {
      padding: 0 12px 0 0;
      display: flex;
      align-items: center;

      .input-icon {
        padding: 0 8px;
        position: static;
        line-height: initial;
      }

      .search-input-badge {
        flex-shrink: 0;
        color: white;
        background-color: $theme-orange;
        padding: 2px 10px;
        text-transform: capitalize;

        .search-input-badge__remove {
          margin-right: 5px;
        }
       }

      .input-value {
        padding: 4px 8px 4px 4px;
      }
    }

    .query-quick {
      .x-menu {
        border-bottom: 1px solid $grey-2;

        &:last-child {
          border: 0;
        }

        .menu-content {
          max-height: 150px;
          overflow: auto;
        }

        .x-menu-item .item-content {
          text-overflow: ellipsis;
          white-space: nowrap;
          overflow: hidden;
        }

        .menu-title {
          font-size: 12px;
          font-weight: 400;
          text-transform: uppercase;
          padding-left: 6px;
          margin-top: 6px;
          color: $grey-4;
        }

        &:first-child {
          .menu-title {
            margin-top: 0;
          }
        }
      }
    }
  }
</style>
