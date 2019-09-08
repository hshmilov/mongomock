<template>
  <x-dropdown
    class="x-query-search-input"
    @activated="$emit('activated')"
  >
    <!-- Trigger is an input field containing a 'freestyle' query, a logical condition on fields -->
    <x-search-input
      id="query_list"
      slot="trigger"
      ref="greatInput"
      v-model="searchValue"
      placeholder="Insert your query or start typing to filter recent Queries"
      :tabindex="-1"
      @keyup.enter.native.stop="submitFilter"
      @keyup.down.native="incQueryMenuIndex"
      @keyup.up.native="decQueryMenuIndex"
    />
    <!--
      Content is a list composed of 3 sections:
      1. Saved queries, filtered to whose names contain the value 'searchValue'
      2. Historical queries, filtered to whose filter contain the value 'searchValue'
      3. Option to search for 'searchValue' everywhere in data (compares to every text field)
    -->
    <div
      slot="content"
      class="query-quick"
      @keyup.down="incQueryMenuIndex"
      @keyup.up="decQueryMenuIndex"
    >
      <x-menu
        v-if="savedViews && savedViews.length"
        id="query_select"
      >
        <div class="title">Saved Queries</div>
        <div class="menu-content">
          <x-menu-item
            v-for="(item, index) in savedViews"
            :key="index"
            :title="item.name"
            :selected="isSelectedSaved(index)"
            @click="selectQuery(item)"
          />
        </div>
      </x-menu>
      <x-menu v-if="historyViews && historyViews.length">
        <div class="title">History</div>
        <div class="menu-content">
          <x-menu-item
            v-for="(item, index) in historyViews"
            :key="index"
            :title="item.view.query.filter"
            :selected="isSelectedHistory(index)"
            @click="selectQuery(item)"
          />
        </div>
      </x-menu>
      <x-menu v-if="this.searchValue && isSearchSimple">
        <x-menu-item
          :title="`Search in table: ${searchValue}`"
          :selected="isSelectedSearch"
          @click="searchText"
        />
      </x-menu>
      <div v-if="noResults">No results</div>
    </div>
  </x-dropdown>
</template>

<script>
  import xDropdown from '../../../axons/popover/Dropdown.vue'
  import xSearchInput from '../../../neurons/inputs/SearchInput.vue'
  import xMenu from '../../../axons/menus/Menu.vue'
  import xMenuItem from '../../../axons/menus/MenuItem.vue'

  import viewsMixin from '../../../../mixins/views'

  import { mapState, mapMutations } from 'vuex'
  import { UPDATE_DATA_VIEW } from '../../../../store/mutations'

  export default {
    name: 'XQuerySearchInput',
    components: {
      xDropdown, xSearchInput, xMenu, xMenuItem
    },
    mixins: [viewsMixin],
    props: {
      module: {
        type: String,
        required: true
      },
      value: {
        type: String,
        default: ''
      },
      querySearch: {
        type: String,
        default: ''
      },
      valid: {
        type: Boolean,
        default: true
      }
    },
    data () {
      return {
        searchValue: '',
        inTextSearch: false,
        queryMenuIndex: -1
      }
    },
    computed: {
      ...mapState({
        savedViews (state) {
          if (!this.isSearchSimple) return state[this.module].views.saved.content.data
          return state[this.module].views.saved.content.data
                  .filter(item => item.name.toLowerCase().includes(this.searchValue.toLowerCase()))
        },
        historyViews (state) {
          if (!this.isSearchSimple) return state[this.module].views.saved.content.data
          return state[this.module].views.history.content.data
                  .filter(item => item.view.query && item.view.query.filter &&
                                  item.view.query.filter.toLowerCase().includes(this.searchValue.toLowerCase()))
        },
        fields (state) {
          return state[this.module].view.fields
        }
      }),
      isSearchSimple () {
        /* Determine whether current search input value is an AQL filter, or just text */
        if (!this.searchValue) return true
        if (this.searchValue.indexOf('exists_in') !== -1) return false
        let simpleMatch = this.searchValue.match('[a-zA-Z0-9 -\._:]*')
        return simpleMatch && simpleMatch.length === 1 && simpleMatch[0] === this.searchValue
      }
      ,
      noResults () {
        /* Determine whether there are no results to show in the search input dropdown */
        return (!this.searchValue || !this.isSearchSimple) && (!this.savedViews || !this.savedViews.length)
          && (!this.historyViews || !this.historyViews.length)
      },
      queryMenuCount () {
        /* Total items to appear in the search input dropdown */
        return this.savedViews.length + this.historyViews.length + (this.searchValue && this.isSearchSimple)
      },
      isSelectedSearch () {
        /* Determine whether the search in table option of the search input dropdown is selected  */
        return this.queryMenuIndex === this.queryMenuCount - 1
      },
      textSearchPattern () {
        if (!this.searchValue) {
          return ''
        }
        /* Create a template for the search everywhere filter, from all currently selected fields */
        if (!this.fields || !this.fields.length) return ''
        let patternParts = []
        this.fields.forEach((field) => {
          // Filter fields containing image data, since it is not relevant for searching
          if (field.includes('image')) return
          patternParts.push(field + ' == regex("{val}", "i")')
        })
        return patternParts.join(' or ')
      }
    },
    watch: {
      value () {
        if (!this.inTextSearch) {
          this.searchValue = this.value
        }
      }
    },
    created () {
      if (this.querySearch) {
        this.searchValue = this.querySearch
      } else if (this.value) {
        this.searchValue = this.value
      }
      this.fetchViewsHistory()
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW
      }),
      viewsCallback () {
        if (this.$route.query.view) {
          let requestedView = this.savedViews.find(view => view.name === this.$route.query.view)
          if (requestedView) {
            this.selectQuery({
              view: requestedView.view,
              uuid: requestedView.uuid
            })
          }
        }
      },
      selectQuery ({ view, uuid }) {
        /* Load given view by settings current filter and expressions to it */
        this.inTextSearch = false
        view.enforcement = null
        this.updateView({
          module: this.module, view, uuid
        })
        if (!this.inTextSearch) {
          this.searchValue = view.query.filter
        }
        this.$emit('validate')
        this.focusInput()
        this.closeInput()
      },
      incQueryMenuIndex () {
        this.queryMenuIndex++
        if (this.queryMenuIndex >= this.queryMenuCount) {
          this.queryMenuIndex = -1
          this.focusInput()
        }
      },
      decQueryMenuIndex () {
        this.queryMenuIndex--
        if (this.queryMenuIndex < -1) {
          this.queryMenuIndex = this.queryMenuCount - 1
        } else if (this.queryMenuIndex === -1) {
          this.focusInput()
        }
      },
      submitFilter () {
        if (!this.valid) return
        if (this.isSearchSimple) {
          // Search for value in all selected fields
          this.searchText()
        } else {
          // Use the search value as a filter
          this.$emit('input', this.searchValue)
          this.inTextSearch = false

        }
        this.$emit('validate')
        this.closeInput()
      },
      searchText () {
        /* Plug the search value in the template for filtering by any of currently selected fields */
        this.$emit('input', this.textSearchPattern.replace(/{val}/g, this.searchValue))
        this.inTextSearch = true
        this.closeInput()
      },
      isSelectedSaved (index) {
        return this.queryMenuIndex === index
      },
      isSelectedHistory (index) {
        return this.queryMenuIndex === index + this.savedViews.length
      },
      focusInput () {
        this.$refs.greatInput.focus()
      },
      closeInput () {
        this.$refs.greatInput.$parent.close()
      }
    }
  }
</script>

<style lang="scss">
  .x-query-search-input {
    flex: 1 0 auto;

    .content {
      width: 100%;
    }

    .x-search-input {
      padding: 0 12px 0 0;

      .input-icon {
        padding: 0 8px;
      }

      .input-value {
        padding-left: 36px;
        width: calc(100% - 12px);
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

        .title {
          font-size: 12px;
          font-weight: 400;
          text-transform: uppercase;
          padding-left: 6px;
          margin-top: 6px;
          color: $grey-4;
        }

        &:first-child {
          .title {
            margin-top: 0;
          }
        }
      }
    }
  }
</style>