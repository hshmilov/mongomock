<template>
  <XRoleGateway
    :permission-category="$permissionConsts.categories.Dashboard"
    :permission-section="$permissionConsts.categories.Charts"
  >
    <template slot-scope="{ canAdd, canUpdate, canDelete }">
      <div class="actions">
        <span
          v-if="isChartFilterable"
          class="actions__search"
          @click="$emit('toggleShowSearch')"
        >
          <VIcon
            size="15"
            class="cardSearch-expression-handle"
          >$vuetify.icons.cardSearch</VIcon>
        </span>
        <ADropdown
          class="actions__menu"
          :trigger="['click']"
          placement="bottomRight"
          :get-popup-container="getPopupContainer"
        >
          <span
            class="ant-dropdown-link card_menu"
            href="#"
          >
            <VIcon
              size="15"
              class="verticaldots-expression-handle"
            >$vuetify.icons.verticaldots</VIcon>
          </span>
          <AMenu slot="overlay">
            <AMenuItem
              v-if="canUpdate && chart.user_id !== '*'"
              id="edit_chart"
              key="0"
              @click="$emit('edit')"
            >
              Edit
            </AMenuItem>
            <AMenuItem
              v-if="canDelete"
              id="remove_chart"
              key="1"
              @click="$emit('remove')"
            >
              Remove
            </AMenuItem>
            <AMenuItem
              v-if="chart.metric==='segment'"
              id="export_chart"
              key="2"
              @click="() => exportCSV(chart.uuid, chart.name, chart.historical)"
            >
              Export to CSV
            </AMenuItem>
            <AMenuItem
              v-if="canAdd || canUpdate"
              id="move_or_copy_chart"
              key="3"
              @click="openMoveOrCopy"
            >
              Move or Copy
            </AMenuItem>
            <AMenuItem
              id="refresh_chart"
              key="4"
              @click="fetchChartData"
            >
              Refresh
            </AMenuItem>
            <ASubMenu
              v-if="sortable"
              id="sort_chart"
              title="Sort"
            >
              <ASubMenu
                :id="getSortTypeId(ChartSortTypeEnum.value)"
              >
                <span slot="title">
                  <span
                    class="sort-title"
                    :class="{
                      'sort-active': isSortMethodActive(
                        ChartSortTypeEnum.value
                      ),
                    }"
                  >
                    {{ getSortTitle(ChartSortTypeEnum.value) }}
                  </span>
                </span>
                <AMenuItem
                  :id="getSortOrderId(ChartSortTypeEnum.value, ChartSortOrderEnum.desc)"
                  key="5"
                  @click="
                    sortClick({
                      type: ChartSortTypeEnum.value,
                      order: ChartSortOrderEnum.desc
                    })
                  "
                >
                  <span
                    class="sort-title"
                    :class="{
                      'sort-active': isSortOrderActive(
                        ChartSortTypeEnum.value,
                        ChartSortOrderEnum.desc
                      ),
                    }"
                  >
                    {{ ChartSortOrderLabelEnum.desc }}
                  </span>
                </AMenuItem>
                <AMenuItem
                  :id="getSortOrderId(ChartSortTypeEnum.value, ChartSortOrderEnum.asc)"
                  key="6"
                  @click="
                    sortClick({
                      type: ChartSortTypeEnum.value,
                      order: ChartSortOrderEnum.asc
                    })
                  "
                >
                  <span
                    class="sort-title"
                    :class="{
                      'sort-active': isSortOrderActive(
                        ChartSortTypeEnum.value,
                        ChartSortOrderEnum.asc
                      ),
                    }"
                  >
                    {{ ChartSortOrderLabelEnum.asc }}
                  </span>
                </AMenuItem>
              </ASubMenu>
              <ASubMenu
                :id="getSortTypeId(ChartSortTypeEnum.name)"
              >
                <span slot="title">
                  <span
                    class="sort-title"
                    :class="{
                      'sort-active': isSortMethodActive(
                        ChartSortTypeEnum.name
                      ),
                    }"
                  >
                    {{ getSortTitle(ChartSortTypeEnum.name) }}
                  </span>
                </span>
                <AMenuItem
                  :id="getSortOrderId(ChartSortTypeEnum.name, ChartSortOrderEnum.desc)"
                  key="7"
                  @click="
                    sortClick({
                      type: ChartSortTypeEnum.name,
                      order: ChartSortOrderEnum.desc
                    })
                  "
                >
                  <span
                    class="sort-title"
                    :class="{
                      'sort-active': isSortOrderActive(
                        ChartSortTypeEnum.name,
                        ChartSortOrderEnum.desc
                      ),
                    }"
                  >
                    {{ ChartSortOrderLabelEnum.desc }}
                  </span>
                </AMenuItem>
                <AMenuItem
                  :id="getSortOrderId(ChartSortTypeEnum.name, ChartSortOrderEnum.asc)"
                  key="8"
                  @click="
                    sortClick({
                      type: ChartSortTypeEnum.name,
                      order: ChartSortOrderEnum.asc
                    })
                  "
                >
                  <span
                    class="sort-title"
                    :class="{
                      'sort-active': isSortOrderActive(
                        ChartSortTypeEnum.name,
                        ChartSortOrderEnum.asc
                      ),
                    }"
                  >
                    {{ ChartSortOrderLabelEnum.asc }}
                  </span>
                </AMenuItem>
              </ASubMenu>
            </ASubMenu>
          </AMenu>
        </ADropdown>
      </div>
    </template>
  </XRoleGateway>
</template>

<script>
import { mapMutations, mapActions } from 'vuex';
import { Menu, Dropdown } from 'ant-design-vue';
import _get from 'lodash/get';
import _capitalize from 'lodash/capitalize';
import {
  MOVE_OR_COPY_TOGGLE,
  FETCH_DASHBOARD_PANEL,
  FETCH_CHART_SEGMENTS_CSV,
} from '../../../store/modules/dashboard';
import {
  ChartSortTypeEnum,
  ChartSortOrderEnum,
  ChartSortOrderLabelEnum,
} from '../../../constants/dashboard';

export default {
  name: 'PanelActions',
  components: {
    ADropdown: Dropdown,
    AMenu: Menu,
    AMenuItem: Menu.Item,
    ASubMenu: Menu.SubMenu,
  },
  props: {
    chart: {
      type: Object,
      default: () => ({}),
    },
    isChartFilterable: {
      type: Boolean,
      default: false,
    },
    sortable: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      filter: '',
      showSearch: false,
      selectedSortType: null,
      selectedSortOrder: null,
    };
  },
  computed: {
    sortType() {
      return this.selectedSortType || _get(this.chart, 'config.sort.sort_by');
    },
    sortOrder() {
      return this.selectedSortOrder || _get(this.chart, 'config.sort.sort_order');
    },
  },
  watch: {
    chart() {
      this.selectedSortType = null;
      this.selectedSortOrder = null;
    },
  },
  created() {
    this.ChartSortTypeEnum = ChartSortTypeEnum;
    this.ChartSortOrderEnum = ChartSortOrderEnum;
    this.ChartSortOrderLabelEnum = ChartSortOrderLabelEnum;
  },
  methods: {
    ...mapMutations({
      moveOrCopyToggle: MOVE_OR_COPY_TOGGLE,
    }),
    ...mapActions({
      fetchDashboardPanel: FETCH_DASHBOARD_PANEL,
      fetchChartSegmentsCSV: FETCH_CHART_SEGMENTS_CSV,
    }),
    getPopupContainer() {
      return document.querySelector('.x-tabs .body');
    },
    openMoveOrCopy() {
      this.moveOrCopyToggle({
        active: true,
        currentPanel: this.chart,
      });
    },
    fetchChartData() {
      this.fetchDashboardPanel({
        uuid: this.chart.uuid,
        spaceId: this.currentSpace,
        skip: 0,
        limit: 100,
        historical: this.chart.historical,
        search: this.filter,
        refresh: true,
        sortBy: this.sortType,
        sortOrder: this.sortOrder,
      });
    },
    exportCSV() {
      this.fetchChartSegmentsCSV({
        uuid: this.chart.uuid,
        name: this.chart.name,
        historical: this.chart.historical,
      });
    },
    isSortMethodActive(type) {
      if (this.selectedSortType) {
        return type === this.selectedSortType;
      }
      return type === this.sortType;
    },
    isSortOrderActive(type, order) {
      if (this.selectedSortType) {
        return (
          type === this.selectedSortType && order === this.selectedSortOrder
        );
      }
      return type === this.sortType && order === this.sortOrder;
    },
    sortClick(sortConfig) {
      this.selectedSortType = sortConfig.type;
      this.selectedSortOrder = sortConfig.order;
      this.chart.selectedSort = sortConfig;
      this.fetchChartData();
    },
    getSortTitle(type) {
      return `Sort by ${_capitalize(type)}`;
    },
    getSortTypeId(type) {
      return `chart_sort_by_${type}`;
    },
    getSortOrderId(type, order) {
      return `chart_sort_order_${type}_${order}`;
    },
  },
};
</script>

<style lang="scss">
  // make menu stay in positon while scrolling
  .x-spaces .x-tabs > .body {
    position: relative;
  }

  .x-card-header {
    display: flex;
    &.hidden {
      display: none;
    }
    > div {
      height: 30px;
      width: 158px;
      &.x-historical-date {
        margin-right: 5px;
      }
    }
  }
  .x-card {
    .role-gateway {
      width: unset;
      .actions {
        &__menu {
          cursor: pointer;
          padding: 8px 0;
        }

        .actions__search {
          cursor: pointer;
          margin-right: 8px;
        }
      }
    }
  }
  .sort-title {
    padding-left: 10px;
  }
  .sort-active {
    padding-left: 0;
  }
  .sort-active::before {
    content: "• ";
  }
</style>
