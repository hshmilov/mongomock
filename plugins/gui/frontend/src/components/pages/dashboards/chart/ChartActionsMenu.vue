<template>
  <div class="chart-actions">
    <XRoleGateway
      :permission-category="$permissionConsts.categories.Dashboard"
      :permission-section="$permissionConsts.categories.Charts"
    >
      <template slot-scope="{ canAdd, canUpdate, canDelete }">
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
            <XIcon
              family="symbol"
              type="verticalDots"
              class="verticaldots-expression-handle"
            />
          </span>
          <AMenu
            slot="overlay"
            :class="`chart-menu-${chart.uuid}`"
          >
            <AMenuItem
              v-if="(canUpdate || permitAllActions) && chart.user_id !== '*'"
              id="edit_chart"
              key="0"
              @click="$emit('edit')"
            >
              Edit
            </AMenuItem>
            <AMenuItem
              v-if="canDelete || permitAllActions"
              id="remove_chart"
              key="1"
              @click="$emit('remove')"
            >
              Delete
            </AMenuItem>
            <AMenuItem
              v-if="exportable"
              id="export_chart"
              key="2"
              @click="$emit('export', {trend: false})"
            >
              Export to CSV
            </AMenuItem>
            <AMenuItem
              v-if="trend"
              id="export_trend_chart"
              key="3"
              @click="$emit('export', {trend: true})"
            >
              Export to CSV - Timeline
            </AMenuItem>
            <AMenuItem
              v-if="canAdd || canUpdate"
              id="move_or_copy_chart"
              key="4"
              @click="$emit('move-or-copy')"
            >
              Move or Copy
            </AMenuItem>
            <AMenuItem
              id="refresh_chart"
              key="5"
              @click="$emit('refresh')"
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
                      'sort-active': isSortByValue,
                    }"
                  >
                    {{ getSortTitle(ChartSortTypeEnum.value) }}
                  </span>
                </span>
                <AMenuItem
                  :id="getSortOrderId(ChartSortTypeEnum.value, ChartSortOrderEnum.desc)"
                  key="6"
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
                      'sort-active': isSortByValue && isSortOrderDesc,
                    }"
                  >
                    {{ ChartSortOrderLabelEnum.desc }}
                  </span>
                </AMenuItem>
                <AMenuItem
                  :id="getSortOrderId(ChartSortTypeEnum.value, ChartSortOrderEnum.asc)"
                  key="7"
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
                      'sort-active': isSortByValue && isSortOrderAsc,
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
                      'sort-active': isSortByName,
                    }"
                  >
                    {{ getSortTitle(ChartSortTypeEnum.name) }}
                  </span>
                </span>
                <AMenuItem
                  :id="getSortOrderId(ChartSortTypeEnum.name, ChartSortOrderEnum.desc)"
                  key="8"
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
                      'sort-active': isSortByName && isSortOrderDesc,
                    }"
                  >
                    {{ ChartSortOrderLabelEnum.desc }}
                  </span>
                </AMenuItem>
                <AMenuItem
                  :id="getSortOrderId(ChartSortTypeEnum.name, ChartSortOrderEnum.asc)"
                  key="9"
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
                      'sort-active': isSortByName && isSortOrderAsc,
                    }"
                  >
                    {{ ChartSortOrderLabelEnum.asc }}
                  </span>
                </AMenuItem>
              </ASubMenu>
            </ASubMenu>
          </AMenu>
        </ADropdown>
      </template>
    </XRoleGateway>
  </div>
</template>

<script>
import _capitalize from 'lodash/capitalize';
import {
  Menu as AMenu,
  Dropdown as ADropdown,
} from 'ant-design-vue';

import {
  ChartSortTypeEnum,
  ChartSortOrderEnum,
  ChartSortOrderLabelEnum,
} from '@constants/dashboard';

export default {
  name: 'XChartActionsMenu',
  components: {
    AMenu,
    AMenuItem: AMenu.Item,
    ASubMenu: AMenu.SubMenu,
    ADropdown,
  },
  props: {
    chart: {
      type: Object,
      default: () => ({}),
    },
    sortable: {
      type: Boolean,
      default: false,
    },
    sort: {
      type: Object,
      default: () => ({}),
    },
    exportable: {
      type: Boolean,
      default: false,
    },
    trend: {
      type: Boolean,
      default: false,
    },
    permitAllActions: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    isSortByName() {
      return this.sort.type === ChartSortTypeEnum.name;
    },
    isSortByValue() {
      return this.sort.type === ChartSortTypeEnum.value;
    },
    isSortOrderDesc() {
      return this.sort.order === ChartSortOrderEnum.desc;
    },
    isSortOrderAsc() {
      return this.sort.order === ChartSortOrderEnum.asc;
    },
  },
  created() {
    this.ChartSortTypeEnum = ChartSortTypeEnum;
    this.ChartSortOrderEnum = ChartSortOrderEnum;
    this.ChartSortOrderLabelEnum = ChartSortOrderLabelEnum;
  },
  methods: {
    getPopupContainer() {
      const container = document.querySelector('.ant-tabs-tabpane-active .x-spaces__content');
      return container;
    },
    sortClick(sort) {
      this.$emit('sort-changed', sort);
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
.chart-actions {
  .role-gateway {
    width: unset;
    height: unset;
  }
  .verticaldots-expression-handle {
    font-size: 16px;
    cursor: pointer;
    /* color the 3-dots icon  */
    svg > g {
      stroke: $theme-blue;
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
