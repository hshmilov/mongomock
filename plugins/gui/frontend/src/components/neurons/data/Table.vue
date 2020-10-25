<template>
  <div
    class="x-data-table"
  >
    <XTableWrapper
      :title="tableTitle"
      :count="count.data_to_show"
      :loading="loading || fetching || showTableSpinner"
      :error="content.error"
    >
      <template slot="search">
        <slot
          name="search"
          :on-search="onConfirmSearch"
          :table-title="tableTitle"
          :table-module="module"
          :table-view="view"
        />
      </template>
      <div
        v-if="selectionCount && multipleRowSelection"
        slot="state"
        class="selection"
      >
        <div>[ {{ selectionCount }} selected.</div>
        <XButton
          v-if="enableSelectAll && !allSelected"
          type="link"
          @click="selectAllData"
        >Select all</XButton>
        <XButton
          v-else-if="allSelected"
          type="link"
          @click="clearAllData"
        >Clear all</XButton>
        <div>]</div>
      </div>
      <slot
        slot="cache"
        name="cache"
      />
      <slot
        slot="actions"
        name="actions"
      />
      <XTable
        slot="table"
        ref="table"
        v-model="pageSelection"
        :data="pageData"
        :fields="fields"
        :page-size="pageSize"
        :sort="view.sort"
        :col-filters="view.colFilters"
        :col-excluded-adapters="view.colExcludedAdapters"
        :id-field="idField"
        :expandable="expandable"
        :filterable="filterable"
        :on-click-row="onClickRow"
        :on-click-col="sortable ? onClickSort : undefined"
        :on-click-all="onClickAll"
        :multiple-row-selection="multipleRowSelection"
        :row-class="rowClass"
        :read-only="readOnly"
        @updateColFilters="updateColFilters"
      >
        <template #default="slotProps">
          <slot v-bind="slotProps">
            <XTableData
              v-if="!$scopedSlots.default"
              v-bind="slotProps"
            />
          </slot>
        </template>
      </XTable>
    </XTableWrapper>
    <div class="x-pagination">
      <div class="x-sizes">
        <div class="number-of-results-title">
          results per page:
        </div>
        <div
          v-for="size in pageSizes"
          :key="size"
          class="x-link"
          :class="{active: size === pageSize}"
          @click="onClickSize(size)"
          @keyup.enter="onClickSize(size)"
        >{{ size }}</div>
      </div>
      <div class="x-pages">
        <div
          :class="{'x-link': page > 0}"
          @click="() => onClickPage(0)"
          @keyup.enter="() => onClickPage(0)"
        >&lt;&lt;</div>
        <div
          :class="{'x-link': page - 1 >= 0}"
          @click="onClickPage(page - 1)"
          @keyup.enter="onClickPage(page - 1)"
        >&lt;</div>
        <div
          v-for="number in pageLinkNumbers"
          :key="number"
          class="x-link"
          :class="{active: (number === page)}"
          @click="onClickPage(number)"
          @keyup.enter="onClickPage(number)"
        >{{ number + 1 }}</div>
        <div
          :class="{'x-link': page + 1 <= pageCount}"
          @click="onClickPage(page + 1)"
          @keyup.enter="onClickPage(page + 1)"
        >&gt;</div>
        <div
          :class="{'x-link': page < pageCount}"
          @click="onClickPage(pageCount)"
          @keyup.enter="onClickPage(pageCount)"
        >&gt;&gt;</div>
      </div>
    </div>
  </div>
</template>

<script>
import {
  mapState, mapMutations, mapActions,
} from 'vuex';
import _orderBy from 'lodash/orderBy';
import _isEmpty from 'lodash/isEmpty';
import _find from 'lodash/find';
import _matchesProperty from 'lodash/matchesProperty';
import { UPDATE_DATA_VIEW, UPDATE_DATA_VIEW_FILTER } from '@store/mutations';
import { FETCH_DATA_CONTENT, RESET_QUERY_CACHE } from '@store/actions';
import { ENTITIES_PAGES_LIMIT } from '@constants/entities';
import _capitalize from 'lodash/capitalize';
import { Divider as ADivider, Icon as AIcon } from 'ant-design-vue';
import _debounce from 'lodash/debounce';
import _get from 'lodash/get';
import XStringView from '@neurons/schema/types/string/StringView.vue';
import XTableWrapper from '../../axons/tables/TableWrapper.vue';
import XTable from '../../axons/tables/Table.vue';
import XTableData from './TableData';


export default {
  name: 'XDataTable',
  components: {
    XTableWrapper,
    XTable,
    XTableData,
    ADivider,
    XStringView,
    AIcon,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    idField: {
      type: String,
      default: 'uuid',
    },
    endpoint: {
      type: String,
      default: '',
    },
    value: {
      type: Object,
      default: undefined,
    },
    title: {
      type: String,
      default: '',
    },
    fields: {
      type: Array,
      default: null,
    },
    fetchFields: {
      type: Array,
      default: null,
    },
    staticData: {
      type: Array,
      default: null,
    },
    expandable: {
      type: Boolean,
      default: false,
    },
    filterable: {
      type: Boolean,
      default: false,
    },
    onClickRow: {
      type: Function,
      default: undefined,
    },
    staticSort: {
      type: Boolean,
      default: true,
    },
    multipleRowSelection: {
      type: Boolean,
      default: true,
    },
    pageSizes: {
      type: Array,
      default: () => [20, 50, 100],
    },
    rowClass: {
      type: [Function, String],
      default: '',
    },
    readOnly: {
      type: Array,
      default: () => [],
    },
    experimentalApi: {
      type: Boolean,
      required: false,
      default: false,
    },
    showTableSpinner: {
      type: Boolean,
      default: false,
    },
    sortColumnIndex: {
      type: Number,
      default: 0,
    },
    useCache: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      loading: true,
      enableSelectAll: false,
    };
  },
  computed: {
    ...mapState({
      moduleState(state) {
        return this.module.split('/').reduce((moduleState, key) => moduleState[key], state);
      },
      refresh(state) {
        if (this.useCache) {
          return 30;
        }
        if (!state.configuration
                  || !state.configuration.data
                  || !state.configuration.data.system) return 0;
        return state.configuration.data.system.refreshRate;
      },
      defaultNumOfEntitiesPerPage(state) {
        if (!state.configuration
                  || !state.configuration.data
                  || !state.configuration.data.system) return 20;
        return state.configuration.data.system.defaultNumOfEntitiesPerPage;
      },
    }),
    allSelected: {
      get() {
        return !this.value.include;
      },
      set(selectAll) {
        this.$emit('input', { ids: [], include: !selectAll });
      },
    },
    tableTitle() {
      if (this.title) return this.title;
      return _capitalize(this.module);
    },
    content() {
      if (this.staticData && !this.moduleState.content) return { fetching: false };
      return this.moduleState.content;
    },
    data() {
      if (this.staticData) return this.filteredData;
      return this.content.data;
    },
    count() {
      if (this.staticData) {
        return {
          data_to_show: this.filteredData.length,
        };
      }
      return this.moduleState.count;
    },
    view() {
      if (this.module === 'users' || this.module === 'devices') {
        return {
          ...this.moduleState.view,
          pageSize: (this.moduleState.view.pageSize || this.defaultNumOfEntitiesPerPage),
        };
      }
      return this.moduleState.view;
    },
    schemaFieldsByName() {
      return this.fields.reduce((allFields, field) => ({ ...allFields, [field.name]: field }), {});
    },
    ids() {
      return this.data.map((item) => item[this.idField]);
    },
    page() {
      return this.view.page;
    },
    pageSize() {
      return this.view.pageSize;
    },
    pageData() {
      return this.data.slice(this.page * this.pageSize, (this.page + 1) * this.pageSize)
        .filter((item) => item);
    },
    pageIds() {
      return this.pageData.map((item) => item[this.idField]);
    },
    fetching() {
      return this.content.fetching && !this.pageIds.length;
    },
    pageCount() {
      const count = this.count.data || this.count.data_to_show;
      if (!count) return 0;
      return Math.ceil(count / this.pageSize) - 1;
    },
    pageLinkNumbers() {
      // Page numbers that can be navigated to, should include 3 before current and 3 after
      let firstPage = this.page - 3;
      let lastPage = this.page + 3;
      if (firstPage <= 0) {
        // For the case that current page is up to 3, page numbers should be first 7 available
        firstPage = 0;
        lastPage = Math.min(firstPage + 6, this.pageCount);
      } else if (lastPage > this.pageCount) {
        // For the case that current page is up to 3 from last,
        // page numbers should be last 7 available
        lastPage = this.pageCount;
        firstPage = Math.max(lastPage - 6, 0);
      }
      return Array.from({ length: lastPage - firstPage + 1 }, (x, i) => i + firstPage);
    },
    pageSelection: {
      get() {
        if (this.value === undefined) return undefined;
        return this.pageIds
          .filter(
            (id) => (this.allSelected ? !this.value.ids.includes(id) : this.value.ids.includes(id)),
          );
      },
      set(selectedList) {
        let newIds = this.value.ids
          .filter((id) => !this.pageIds.includes(id)).concat(
            this.allSelected ? this.pageIds.filter(
              (item) => !selectedList.includes(item),
            ) : selectedList,
          );
        if (this.allSelected && newIds.length === this.count.data) {
          this.allSelected = false;
          newIds = [];
        }
        this.$emit('input', {
          ids: newIds, include: !this.allSelected,
        });
      },
    },
    selectionCount() {
      if (!this.value) return 0;
      if (this.allSelected) {
        return this.count.data - this.value.ids.length;
      }
      return this.value.ids.length;
    },
    sortedData() {
      return _orderBy(this.staticData, [(item) => {
        if (!this.staticSort) return 1;
        if (this.view.sort && !this.view.sort.field) return 1;
        let value = item[this.view.sort.field] || '';
        if (Array.isArray(value)) {
          value = value.join('');
        }

        if (this.isDateType(this.view.sort.field)) {
          const dateValue = Date.parse(value);
          if (dateValue) {
            value = dateValue;
          }
        }

        return value;
      }], [this.view.sort && this.view.sort.desc ? 'desc' : 'asc']);
    },
    searchValue() {
      return this.view.query.search;
    },
    searchValueLower() {
      return this.searchValue.toLowerCase();
    },
    filteredData() {
      if (!this.searchValue) return this.sortedData;
      return this.sortedData.filter((item) => {
        const { adapters, ...rest } = item;
        const searchableKeys = Object.keys(rest);
        return searchableKeys.find((key) => {
          let val = item[key];
          if (!this.schemaFieldsByName[key]) {
            return false;
          }
          const fieldType = this.schemaFieldsByName[key].type;
          if (fieldType === 'number' && typeof val === 'number') {
            val = val.toFixed(2);
          }
          if (fieldType === 'bool') {
            if (val === true) {
              val = 'Yes';
            } else if (val === false) {
              val = 'No';
            }
          }
          return val.toString().toLowerCase().includes(this.searchValueLower);
        });
      });
    },
    sortable() {
      return (this.staticData && this.staticSort) || this.view.sort;
    },
  },
  watch: {
    refresh(newRate) {
      if (newRate) {
        this.startRefreshTimeout();
      }
    },
  },
  mounted() {
    if (this.staticData) {
      if (this.view.sort && !this.view.sort.field && !_isEmpty(this.fields)) {
        this.updateView({
          module: this.module,
          view: {
            sort: {
              field: this.fields[this.sortColumnIndex].name, desc: false,
            },
            schema_fields: this.fields,
          },
        });
      }
      this.loading = false;
      return;
    }
    if (!this.$route.query.view && this.fields.length) {
      this.fetchContentPages();
    }
    if (this.refresh) {
      this.startRefreshTimeout();
    }
  },
  beforeDestroy() {
    clearTimeout(this.timer);
  },
  created() {
    this.$set(this.content, 'cache_last_updated', '');
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
      updateViewFilter: UPDATE_DATA_VIEW_FILTER,
    }),
    ...mapActions({
      fetchContent: FETCH_DATA_CONTENT,
      resetQueryCache: RESET_QUERY_CACHE,
    }),
    fetchContentPages(loading, getCount, isRefresh, useCacheEntry) {
      if (!isRefresh) {
        this.resetScrollPosition();
      }
      if (this.staticData) {
        this.loading = false;
        return;
      }
      if (loading) {
        this.loading = true;
      }
      if (!this.pageLinkNumbers || this.pageLinkNumbers.length <= 1) {
        return this.fetchContentSegment(0, this.pageSize * ENTITIES_PAGES_LIMIT, getCount, isRefresh, useCacheEntry);
      }
      return this.fetchContentSegment(
        this.pageLinkNumbers[0] * this.pageSize,
        this.pageSize * ENTITIES_PAGES_LIMIT,
        getCount,
        isRefresh,
        useCacheEntry,
      );
    },
    fetchContentSegment(skip, limit, getCount, isRefresh, useCacheEntry) {
      return this.fetchContent({
        module: this.module,
        endpoint: this.endpoint,
        skip,
        limit,
        getCount,
        isRefresh,
        isExperimentalAPI: this.experimentalApi,
        fields: this.fetchFields,
        useCacheEntry,
      }).then(() => {
        if (!this.content.fetching) {
          this.loading = false;
        }
      }).catch(() => {
        this.loading = false;
      });
    },
    onClickSize(size) {
      if (size === this.pageSize) return;
      this.updateModuleView({ pageSize: size, page: 0 });
      this.fetchContentPages(false, false);
    },
    onClickPage(page) {
      if ((page === this.page) || (page < 0 || page > this.pageCount)) {
        return;
      }
      this.updateModuleView({ page });
      this.fetchContentPages(false, false);
    },
    onClickSort(fieldName) {
      const { field, desc } = this.view.sort;
      const sort = { field: fieldName, desc: true };
      if (field === fieldName) {
        if (desc) {
          sort.desc = false;
        } else {
          sort.field = '';
        }
      }
      this.updateModuleView({ sort, page: 0 });
      this.fetchContentPages(true, false);
    },
    updateModuleView(view) {
      this.updateView({ module: this.module, view });
    },
    startRefreshTimeout() {
      if (this.staticData) {
        return;
      }
      const fetchAuto = () => {
        this.fetchContentPages(false, true, undefined, this.useCache).then(() => {
          if (this._isDestroyed) return;
          this.timer = setTimeout(fetchAuto, this.refresh * 1000);
        });
      };
      this.timer = setTimeout(fetchAuto, this.refresh * 1000);
    },
    selectAllData() {
      this.allSelected = true;
    },
    clearAllData() {
      this.allSelected = false;
    },
    onClickAll(selected) {
      this.enableSelectAll = selected;
    },
    updateColFilters(colFilters) {
      this.updateViewFilter({ module: this.module, ...colFilters });
      this.fetchContentPages(false, false);
    },
    resetScrollPosition() {
      this.$refs.table.$el.scrollTop = 0;
    },
    onConfirmSearch() {
      if (this.staticData) {
        return;
      }
      this.fetchContentPages(true, true);
    },
    getSchemaFieldFormat(field) {
      if (this.view.schema_fields) {
        const item = _find(this.view.schema_fields, _matchesProperty('name', field));
        return item && item.format;
      }
      return null;
    },
    isDateType(field) {
      const fieldFormat = this.getSchemaFieldFormat(field);
      return fieldFormat === 'date-time' || fieldFormat === 'date' || fieldFormat === 'time';
    },
    resetCache: _debounce(async function resetCache() {
      const filter = _get(this.view, 'query.filter', null);
      await this.resetQueryCache({
        module: this.module,
        filter: filter && filter.length ? filter : null,
      });
      this.fetchContentPages(true, true);
    }, 400, { leading: true, trailing: false }),
  },
};
</script>

<style lang="scss">
  .x-data-table {
    height: 100%;

    .separator {
      background-color: $theme-black;
      top: -0.01em;
      margin: 0 10px;
    }

    .last-updated-title {
      margin: 0 5px 0 5px;
    }

    .reset-cache {
      padding-left: 10px;
    }

    .selection {
      display: flex;
      align-items: center;
      margin-left: 12px;
    }

    .refresh-data {
      .x-button {
        padding: 0 5px;
      }
    }

    .x-pagination {
      justify-content: space-between;
      display: flex;
      line-height: 28px;

      .number-of-results-title {
        text-transform: uppercase;
      }

      .x-sizes {
        display: flex;
        width: 320px;
        justify-content: space-between;

        .active, .x-link:hover {
          cursor: pointer;
          color: $theme-orange;
          transition: color 0.4s;
        }

        .active:hover {
          cursor: default;
        }
      }

      .x-pages {
        display: flex;
        width: 360px;
        min-height: 28px;
        justify-content: space-evenly;
        flex: 0 1 auto;
        position: relative;
        background: $theme-white;
        border-bottom: 2px solid $theme-white;
        border-radius: 2px;

        .active, .x-link:hover {
          cursor: pointer;
          font-weight: 500;
          transition: font-weight 0.4s;
        }

        .active:hover {
          cursor: default;
        }

        &:after {
          content: '';
          position: absolute;
          transform: rotate(-45deg);
          border: 20px solid transparent;
          border-left: 20px solid $theme-white;
          border-radius: 2px;
          left: -20px;
          top: -20px;
        }
      }
    }
  }
  .x-query {
    ~ .x-data-table {
      height: calc(100% - 64px);
    }
  }
  .x-search-input {
    ~ .x-data-table {
      height: calc(100% - 30px);
    }
  }
</style>
