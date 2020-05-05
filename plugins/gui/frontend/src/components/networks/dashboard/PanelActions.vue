<template>
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
      v-if="hasDropDownMenu"
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
          v-if="editable"
          id="edit_chart"
          key="0"
          @click="$emit('edit')"
        >
          Edit
        </AMenuItem>
        <AMenuItem
          v-if="$can($permissionConsts.categories.Dashboard,
                     $permissionConsts.actions.Delete,
                     $permissionConsts.categories.Charts)"
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
          id="move_or_copy_chart"
          key="3"
          @click="openMoveOrCopy"
        >
          Move or Copy
        </AMenuItem>
        <AMenuItem
          id="refresh_chart"
          key="4"
          @click="(skip) => fetchMorePanel(chart.uuid, 0, chart.historical, true)"
        >
          Refresh
        </AMenuItem>
      </AMenu>
    </ADropdown>
  </div>
</template>

<script>
import { mapMutations, mapActions } from 'vuex';
import { Menu, Dropdown } from 'ant-design-vue';
import {
  MOVE_OR_COPY_TOGGLE, FETCH_DASHBOARD_PANEL, FETCH_CHART_SEGMENTS_CSV
} from '../../../store/modules/dashboard';

export default {
  name: 'PanelActions',
  components: {
    ADropdown: Dropdown,
    AMenu: Menu,
    AMenuItem: Menu.Item,
  },
  props: {
    chart: {
      type: Object,
      default: () => ({}),
    },
    editable: {
      type: Boolean,
      default: false,
    },
    hasDropDownMenu: {
      type: Boolean,
      default: false,
    },
    isChartFilterable: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      filter: '',
      showSearch: false,
    };
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
    fetchMorePanel(uuid, skip, historical, refresh) {
      this.fetchDashboardPanel({
        uuid,
        spaceId: this.currentSpace,
        skip,
        limit: 100,
        historical,
        search: this.filter,
        refresh,
      });
    },
    exportCSV(uuid, name, historical) {
      this.fetchChartSegmentsCSV({
        uuid,
        name,
        historical,
      });
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

</style>
