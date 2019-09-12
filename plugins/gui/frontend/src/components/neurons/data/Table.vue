<template>
  <div
    class="x-data-table"
    :class="{ multiline }"
  >
    <x-table-wrapper
      :title="tableTitle"
      :count="count.data_to_show"
      :loading="loading"
      :error="content.error"
    >
      <div
        v-if="selectionCount"
        slot="state"
        class="selection"
      >
        <div>[ {{ selectionCount }} selected.</div>
        <x-button
          v-if="enableSelectAll && !allSelected"
          link
          @click="selectAllData"
        >Select all</x-button>
        <x-button
          v-else-if="allSelected"
          link
          @click="clearAllData"
        >Clear all</x-button>
        <div>]</div>
      </div>
      <slot
        slot="actions"
        name="actions"
      />
      <x-table
        slot="table"
        v-model="pageSelection"
        :data="pageData"
        :fields="viewFieldsPaths"
        :page-size="view.pageSize"
        :sort="view.sort"
        :col-filters="view.colFilters"
        :id-field="idField"
        :expandable="expandable"
        :filterable="filterable"
        :on-click-row="onClickRow"
        :on-click-col="onClickSort"
        :on-click-all="onClickAll"
        @filter="updateColFilters"
      >
        <slot
          slot-scope="props"
          v-bind="props"
        />
      </x-table>
    </x-table-wrapper>
    <div class="x-pagination">
      <div class="x-sizes">
        <div class="title">results per page:</div>
        <div
          v-for="size in [20, 50, 100]"
          :key="size"
          class="x-link"
          :class="{active: size === view.pageSize}"
          @click="onClickSize(size)"
          @keyup.enter="onClickSize(size)"
        >{{ size }}</div>
      </div>
      <div class="x-pages">
        <div
          :class="{'x-link': view.page > 0}"
          @click="onClickPage(0)"
          @keyup.enter="onClickPage(0)"
        >&lt;&lt;</div>
        <div
          :class="{'x-link': view.page - 1 >= 0}"
          @click="onClickPage(view.page - 1)"
          @keyup.enter="onClickPage(view.page - 1)"
        >&lt;</div>
        <div
          v-for="number in pageLinkNumbers"
          :key="number"
          class="x-link"
          :class="{active: (number === view.page)}"
          @click="onClickPage(number)"
          @keyup.enter="onClickPage(number)"
        >{{ number + 1 }}</div>
        <div
          :class="{'x-link': view.page + 1 <= pageCount}"
          @click="onClickPage(view.page + 1)"
          @keyup.enter="onClickPage(view.page + 1)"
        >&gt;</div>
        <div
          :class="{'x-link': view.page < pageCount}"
          @click="onClickPage(pageCount)"
          @keyup.enter="onClickPage(pageCount)"
        >&gt;&gt;</div>
      </div>
    </div>
  </div>
</template>

<script>
  import xTableWrapper from '../../axons/tables/TableWrapper.vue'
  import xTable from '../../axons/tables/Table.vue'
  import xButton from '../../axons/inputs/Button.vue'

  import { GET_DATA_SCHEMA_BY_NAME } from '../../../store/getters'
  import { UPDATE_DATA_VIEW, UPDATE_DATA_VIEW_FILTER } from '../../../store/mutations'
  import { FETCH_DATA_CONTENT } from '../../../store/actions'
  import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'

  export default {
    name: 'XDataTable',
    components: { xTableWrapper, xTable, xButton },
    props: {
      module: {
        type: String,
        required: true
      },
      idField: {
        type: String,
        default: 'uuid'
      },
      endpoint: {
        type: String,
        default: ''
      },
      value: {
        type: Object,
        default: undefined
      },
      title: {
        type: String,
        default: ''
      },
      staticFields: {
        type: Array,
        default: null
      },
      staticData: {
        type: Array,
        default: null
      },
      expandable: {
        type: Boolean,
        default: false
      },
      filterable: {
        type: Boolean,
        default: false
      },
      onClickRow: {
        type: Function,
        default: undefined
      }
    },
    data () {
      return {
        loading: true,
        enableSelectAll: false,
        allSelected: false
      }
    },
    computed: {
      ...mapState({
        moduleState (state) {
          return this.module.split('/').reduce((moduleState, key) => {
            return moduleState[key]
          }, state)
        },
        refresh (state) {
          if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return 0
          return state.configuration.data.system.refreshRate
        },
        multiline (state) {
          if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return 0
          return state.configuration.data.system.multiLine
        }
      }),
      ...mapGetters({
        getFieldSchemaByName: GET_DATA_SCHEMA_BY_NAME
      }),
      tableTitle () {
        if (this.title) return this.title
        return this.module.charAt(0).toUpperCase() + this.module.slice(1).toLowerCase()
      },
      content () {
        if (this.staticData) return {fetching: false}
        return this.moduleState.content
      },
      data () {
        if (this.staticData) return this.staticData
        return this.content.data
      },
      count () {
        if (this.staticData) return {data_to_show: this.staticData.length}
        return this.moduleState.count
      },
      view () {
        return this.moduleState.view
      },
      schemaFieldsByName () {
        return this.getFieldSchemaByName(this.module)
      },
      viewFields () {
        if (!this.view.fields) {
          return this.staticFields || []
        }
        let schemaFieldsByName = this.schemaFieldsByName
        if (!schemaFieldsByName || !Object.keys(schemaFieldsByName).length) {
          return []
        }
        return this.view.fields.map(fieldName => schemaFieldsByName[fieldName]).filter(field => field)
      },
      viewFieldsPaths () {
        return this.viewFields.map(field => {
          return {
            ...field,
            path: (field.path ? field.path : []).concat([field.name])
          }
        })
      },
      ids () {
        return this.data.map(item => item[this.idField])
      },
      pageData () {
        let pageId = this.view.page
        if (!this.staticData) {
          this.pageLinkNumbers.forEach((number, index) => {
            if (number === this.view.page) {
              pageId = index
            }
          })
        }
        return this.data.slice(pageId * this.view.pageSize, (pageId + 1) * this.view.pageSize)
      },
      pageIds () {
        return this.pageData.map(item => item[this.idField])
      },
      pageCount () {
        let count = this.count.data || this.count.data_to_show
        if (!count) return 0
        return Math.ceil(count / this.view.pageSize) - 1
      },
      pageLinkNumbers () {
        // Page numbers that can be navigated to, should include 3 before current and 3 after
        let firstPage = this.view.page - 3
        let lastPage = this.view.page + 3
        if (this.view.page <= 3) {
          // For the case that current page is up to 3, page numbers should be first 7 available
          firstPage = 0
          lastPage = Math.min(firstPage + 6, this.pageCount)
        } else if (this.view.page >= (this.pageCount - 3)) {
          // For the case that current page is up to 3 from last, page numbers should be last 7 available
          lastPage = this.pageCount
          firstPage = Math.max(lastPage - 6, 0)
        }
        return Array.from({ length: lastPage - firstPage + 1 }, (x, i) => i + firstPage)
      },
      pageSelection: {
        get() {
          if (this.value === undefined) return undefined
          return this.pageIds.filter(id => this.allSelected? !this.value.ids.includes(id): this.value.ids.includes(id))
        },
        set (selectedList) {
          let newIds = this.value.ids.filter(id => !this.pageIds.includes(id)).concat(
                  this.allSelected ? this.pageIds.filter(item => !selectedList.includes(item)) : selectedList)
          if (this.allSelected && newIds.length === this.count.data) {
            this.allSelected = false
            newIds = []
          }
          this.$emit('input', {
            ids: newIds, include: !this.allSelected
          })
        }
      },
      selectionCount () {
        if (!this.value) return 0
        if (this.allSelected) {
          return this.count.data - this.value.ids.length
        }
        return this.value.ids.length
      }
    },
    watch: {
      loading (newLoading) {
        if (newLoading) return
        if (this.data && this.data.length) {
          this.$emit('data', this.data[0][this.idField])
        } else {
          this.$emit('data')
        }
      },
      refresh (newRate) {
        if (newRate) {
          this.startRefreshTimeout()
        }
      }
    },
    mounted () {
      if (this.staticData) {
        this.loading = false
        return
      }
      if (!this.$route.query.view) {
        this.fetchContentPages()
      }
      if (this.refresh) {
        this.startRefreshTimeout()
      }
    },
    beforeDestroy () {
      clearTimeout(this.timer)
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW,
        updateViewFilter: UPDATE_DATA_VIEW_FILTER
      }),
      ...mapActions({
        fetchContent: FETCH_DATA_CONTENT
      }),
      fetchContentPages (loading, isRefresh) {
        if (this.staticData) {
          this.loading = false
          return
        }
        if (!this.pageLinkNumbers || !this.pageLinkNumbers.length) {
          return this.fetchContentSegment(0, this.view.pageSize)
        }
        if (loading) {
          this.loading = true
        }
        return this.fetchContentSegment(
          this.pageLinkNumbers[0] * this.view.pageSize,
          this.pageLinkNumbers.length * this.view.pageSize,
          isRefresh
        )
      },
      fetchContentSegment (skip, limit, isRefresh) {
        return this.fetchContent({
          module: this.module, endpoint: this.endpoint,
          skip, limit, isRefresh
        }).then(() => {
          if (!this.content.fetching) {
            this.loading = false
          }
        }).catch(() => this.loading = false)
      },
      onClickSize (size) {
        if (size === this.view.pageSize) return
        this.updateModuleView({ pageSize: size })
        this.fetchContentPages()
      },
      onClickPage (page) {
        if ((page === this.view.page) || (page < 0 || page > this.pageCount)) {
          return
        }
        if (Math.abs(page - this.view.page) > 3) {
          this.loading = true
        }
        this.updateModuleView({ page: page })
        this.$nextTick(this.fetchContentPages)
      },
      onClickSort (fieldName) {
        let sort = { ...this.view.sort }
        if (sort.field !== fieldName) {
          sort.field = fieldName
          sort.desc = true
        } else if (sort.desc) {
          sort.desc = false
        } else {
          sort.field = ''
        }
        this.updateModuleView({ sort, page: 0 })
        this.fetchContentPages(true)
      },
      updateModuleView (view) {
        this.updateView({ module: this.module, view })
      },
      startRefreshTimeout () {
        if (this.staticData) {
          return
        }
        const fetchAuto = () => {
          this.fetchContentPages(false, true).then(() => {
            if (this._isDestroyed) return
            this.timer = setTimeout(fetchAuto, this.refresh * 1000)
          })
        }
        this.timer = setTimeout(fetchAuto, this.refresh * 1000)
      },
      selectAllData () {
        this.allSelected = true
        this.$emit('input', { ids: [], include: false })
      },
      clearAllData () {
        this.allSelected = false
        this.$emit('input', { ids: [], include: true })
      },
      onClickAll (selected) {
        this.enableSelectAll = selected
      },
      updateColFilters(colFilters) {
        this.updateViewFilter({ module: this.module, view: {colFilters} })
      }
    }
  }
</script>

<style lang="scss">
    .x-data-table {
        height: calc(100% - 66px);

        .selection {
            display: flex;
            align-items: center;
            margin-left: 12px;
        }

        &.multiline .x-table-row .array {
            display: block;
            height: auto;

            .item {
                margin-right: 0;
            }
        }

        .x-cross .first, .x-cross .second {
            top: 0px;
        }

        .x-pagination {
            justify-content: space-between;
            display: flex;
            line-height: 28px;

            .title {
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
</style>