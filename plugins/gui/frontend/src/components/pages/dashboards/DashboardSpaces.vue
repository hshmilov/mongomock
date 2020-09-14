<template>
  <div class="x-spaces">
    <XRoleGateway
      :permission-category="$permissionConsts.categories.Dashboard"
      :permission-section="$permissionConsts.categories.Spaces"
    >
      <template slot-scope="{ canDelete, canAdd }">
        <ATabs
          v-if="spaces.length"
          :active-key="activeSpace"
          :animated="false"
          @change="onSpaceChange"
        >

          <template #tabBarExtraContent>
            <div
              class="space_action_bar"
            >
              <XButton
                v-if="canAdd"
                id="new_space_btn"
                type="primary"
                @click="displaySpaceFormModal = true"
              >
                Add Space
              </XButton>
            </div>
          </template>
          <ATabPane
            v-for="space in spacesTabs"
            :id="space.key"
            :key="space.key"
          >
            <!-- Display actions-menu for active tab (Space) -->
            <div
              :id="space.key"
              slot="tab"
              class="x-spaces__tab"
            >
              <span :title="space.title">{{ space.title }}</span>
              <div
                class="edit-space-menu"
              >
                <XSpaceOptionsMenu
                  v-if="getSpaceActionsDescriptor(canAdd, canDelete).supported && space.key === activeSpace"
                  :supported-actions="getSpaceActionsDescriptor(canAdd, canDelete).features"
                  @edit="onEditActiveSpace"
                  @remove="onRemoveActiveSpace"
                />
              </div>
            </div>

            <!-- Space Content -->
            <div
              v-if="spaceContentsLoading"
              class="x-spaces__spinner"
            >
              <ASpin size="large" />
            </div>
            <XSpaceContent
              v-else-if="!spaceContentsLoading && isActiveSpaceContent(space.key)"
              v-model="charts"
              :active-space-id="activeSpace"
              :can-add-chart="canAddCharts || isPersonalSpace"
              :is-axonius-dashboard="defaultSpaceUuid === activeSpace"
              @add-new-chart="isChartModalVisible = true"
              @chart-changed="onChartChanged"
              @chart-removed="onChartRemoved"
              @chart-duplicated="insertNewChart"
            />
          </ATabPane>
        </ATabs>
      </template>
    </XRoleGateway>
    <XEditSpaceModal
      v-if="displaySpaceFormModal"
      :space="spaceToEdit"
      @confirm="onConfirmSpaceModal"
      @cancel="onCancelSpaceModal"
    />
    <XChartsWizard
      v-if="isChartModalVisible"
      :space="activeSpace"
      :is-personal-space="isPersonalSpace"
      @add="insertNewChart"
      @close="isChartModalVisible = false"
    />
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';
import {
  Tabs as ATabs,
  Spin as ASpin,
} from 'ant-design-vue';
import XSpaceOptionsMenu from '@networks/dashboard/SpaceOptionsMenu.vue';
import XEditSpaceModal from '@networks/dashboard/EditSpaceModal.vue';
import XButton from '@axons/inputs/Button.vue';
import XWizard from '@networks/dashboard/Wizard.vue';

import {
  FETCH_DASHBOARD_SPACES,
  SAVE_DASHBOARD_SPACE,
  CHANGE_DASHBOARD_SPACE,
  REMOVE_DASHBOARD_SPACE,
  SAVE_REORDERED_PANELS,
} from '@store/modules/dashboard';
import { SpaceTypesEnum, ChartViewEnum, ChartComponentByViewEnum } from '@constants/dashboard';
import { getCurrentSpaceData } from '@api/dashboard';
import _isNil from 'lodash/isNil';
import XSpaceContent from './SpaceContent.vue';

export default {
  name: 'XDashboardSpaces',
  components: {
    XButton,
    XEditSpaceModal,
    XSpaceOptionsMenu,
    ATabs,
    ATabPane: ATabs.TabPane,
    XChartsWizard: XWizard,
    XSpaceContent,
    ASpin,
  },
  data() {
    const canAddCharts = this.$can(this.$permissionConsts.categories.Dashboard,
      this.$permissionConsts.actions.Add,
      this.$permissionConsts.categories.Charts);

    return {
      displaySpaceFormModal: false,
      spaceToEdit: undefined,
      canAddCharts,
      isChartModalVisible: false,
      activeSpaceData: null,
      spacesLoading: true,
      ChartViewEnum,
    };
  },
  computed: {
    ...mapState({
      spaces(state) {
        return state.dashboard.spaces.data || [];
      },
    }),
    spacesTabs() {
      const defaultSpaceTab = {
        key: this.defaultSpaceUuid,
        title: this.defaultSpace.name,
      };

      const customSpacesTabs = this.spaces.reduce((spaces, space) => {
        if (space.type === SpaceTypesEnum.custom) {
          return [...spaces, { key: space.uuid, title: space.name }];
        }
        return spaces;
      }, []);

      const personalSpaceTab = { key: this.personalSpaceUuid, title: this.personalSpace.name };

      return [defaultSpaceTab, personalSpaceTab, ...customSpacesTabs];
    },
    defaultSpace() {
      return this.spaces.find((space) => space.type === SpaceTypesEnum.default);
    },
    personalSpace() {
      return this.spaces.find((space) => space.type === SpaceTypesEnum.personal);
    },
    defaultSpaceUuid() {
      return this.defaultSpace && this.defaultSpace.uuid;
    },
    personalSpaceUuid() {
      return this.personalSpace && this.personalSpace.uuid;
    },
    activeSpace() {
      // return the currentActiveSpace (tab) uuid, which is normally reflected in URL.
      // empty uuid param is mapped to the default space.
      return this.$route.params.spaceId || this.defaultSpaceUuid;
    },
    isPersonalSpace() {
      return this.activeSpace === this.personalSpaceUuid;
    },
    charts: {
      get() {
        const getChartConfigById = (chartId) => this.activeSpaceData.charts.find((chart) => chart.uuid === chartId);
        const spaceCharts = this.activeSpaceData ? this.activeSpaceData.panels_order : [];
        return spaceCharts.filter(getChartConfigById).map(getChartConfigById);
      },
      set(value) {
        const spaceChartsOrderById = value.map((c) => c.uuid);
        this.reorderSpaceCharts({ panels_order: spaceChartsOrderById, spaceId: this.activeSpace });

        this.activeSpaceData = {
          ...this.activeSpaceData,
          panels_order: spaceChartsOrderById,
        };
      },
    },
    spaceContentsLoading() {
      return this.spacesLoading && !this.charts.length;
    },
  },
  watch: {
    activeSpace: {
      immediate: true,
      handler: 'repeatedlyFetchActiveSpace',
    },
  },
  async created() {
    this.ChartComponentByViewEnum = ChartComponentByViewEnum;
    await this.fetchDashboardSpaces();
    this.repeatedlyFetchSpaces();
  },
  destroyed() {
    clearTimeout(this.fetchSpacesInterval);
    clearTimeout(this.fetchAcativeSpaceInterval);
  },
  methods: {
    ...mapActions({
      fetchDashboardSpaces: FETCH_DASHBOARD_SPACES,
      createNewSpace: SAVE_DASHBOARD_SPACE,
      deleteSpace: REMOVE_DASHBOARD_SPACE,
      updateSpace: CHANGE_DASHBOARD_SPACE,
      reorderSpaceCharts: SAVE_REORDERED_PANELS,
    }),
    repeatedlyFetchSpaces() {
      this.fetchSpacesInterval = setTimeout(async () => {
        if (this._isDestroyed) return;
        await this.fetchDashboardSpaces();
        this.repeatedlyFetchSpaces();
      }, 30000);
    },
    repeatedlyFetchActiveSpace(spaceId, calledFirstTime = true) {
      if (!spaceId) return;

      if (calledFirstTime) {
        this.fetchActiveSpaceData(spaceId);
      }
      if (this.fetchAcativeSpaceInterval) {
        // clear previous space's scheduled fetch cycle
        clearTimeout(this.fetchAcativeSpaceInterval);
      }

      this.fetchAcativeSpaceInterval = setTimeout(async () => {
        if (this._isDestroyed) return;
        await this.fetchActiveSpaceData(spaceId, true);
        this.repeatedlyFetchActiveSpace(spaceId, false);
      }, 30000);
    },
    isActiveSpaceContent(spaceId) {
      // because there's no way to force inactive tab panes
      // to be destroyed, we render only the contents of active tabs.
      if (!this.charts.length) return true;
      return this.charts[0].space === spaceId;
    },
    // space actions
    async fetchActiveSpaceData(spaceId, hideSpinner = false) {
      if (!hideSpinner) {
        this.spacesLoading = true;
        this.activeSpaceData = null;
      }
      const res = await getCurrentSpaceData(spaceId);
      this.activeSpaceData = res;
      this.spacesLoading = false;
    },
    onEditActiveSpace() {
      this.spaceToEdit = this.activeSpaceData
      || this.spaces.find((s) => s.uuid === this.activeSpace);
      this.displaySpaceFormModal = true;
    },
    onRemoveActiveSpace() {
      this.$safeguard.show({
        text: `
            <div>This space will be completely deleted from the system and</div>
            <div>no other user will be able to use it.</div>
            <div>Deleting the space is an irreversible action.</div>
            <div>Do you want to continue?</div>
          `,
        confirmText: 'Delete Space',
        onConfirm: async () => {
          await this.deleteSpace(this.activeSpace);
          this.$router.push({ path: '/' });
        },
      });
    },
    async onConfirmSpaceModal(spaceFormData) {
      if (!_isNil(this.spaceToEdit)) {
        await this.updateSpace(spaceFormData);
        this.activeSpaceData = {
          ...this.activeSpaceData,
          ...spaceFormData,
        };
      } else {
        const spaceId = await this.createNewSpace(spaceFormData);
        this.$router.push({ name: 'Dashboard', params: { spaceId } });
      }
      this.onCancelSpaceModal();
    },
    onCancelSpaceModal() {
      this.displaySpaceFormModal = false;
      this.spaceToEdit = undefined;
    },
    onSpaceChange(targetSpaceUuid) {
      if (targetSpaceUuid === this.defaultSpaceUuid) {
        this.$router.push({ path: '/' });
      } else {
        this.$router.push({ name: 'Dashboard', params: { spaceId: targetSpaceUuid } });
      }
    },
    getSpaceActionsDescriptor(canAdd, canDelete) {
      const features = [];
      switch (this.activeSpace) {
        case this.personalSpaceUuid:
          return { supported: false };
        case this.defaultSpaceUuid:
          if (canAdd) features.push('edit');
          return { supported: canAdd, features };
        default:
          if (canAdd) features.push('edit');
          if (canDelete) features.push('remove');

          return { supported: canAdd || canDelete, features };
      }
    },
    // charts events callbacks
    insertNewChart(chart) {
      this.isChartModalVisible = false;
      this.activeSpaceData = {
        ...this.activeSpaceData,
        panels_order: [...this.activeSpaceData.panels_order, chart.uuid],
        charts: [...this.activeSpaceData.charts, chart],
      };
    },
    onChartChanged(chart) {
      const updatedChartIndex = this.activeSpaceData.charts.findIndex((c) => c.uuid === chart.uuid);
      if (updatedChartIndex >= 0) {
        this.activeSpaceData.charts.splice(updatedChartIndex, 1,
          { ...this.activeSpaceData.charts[updatedChartIndex], ...chart });
      }
    },
    onChartRemoved(chartId) {
      this.activeSpaceData.panels_order = this.activeSpaceData.panels_order.filter((uuid) => uuid !== chartId);
    },
  },
};
</script>

<style lang="scss">
.x-spaces {
  .ant-tabs-tab {
    max-width: 260px;
    padding: 12px 4px;
    .x-spaces__tab {
      .edit-space-menu {
        width: 22px;
      }
      span {
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }
  }
  height: calc(100% - 54px);
  overflow: hidden;
  &__tab {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;

    .x-button {
      height: 22px;
    }
  }
  .space_action_bar {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    height: 40px;
    min-width: 140px;

    &__menu-wrapper {
      margin-right: 24px;
    }
  }

  .charts {
    display: grid;
    grid-template-columns: repeat(auto-fill, 350px);
    grid-template-rows: repeat(auto-fill, 450px);
    grid-auto-rows: 450px;
    grid-auto-columns: 350px;
    grid-gap: 8px;
    height: 100%;
    width: 100%;

    .x-chart:last-child {
      margin-bottom: 8px;
    }

    // in small-medium screens this rules
    // fixes issues with hidden content and scroll issues
    @media screen
      and (min-device-width: 1200px)
      and (max-device-width: 1600px) {
        justify-content: start;
    }

    .x-chart__new {
      justify-content: center;
      align-items: center;
      .add-button {
        cursor: pointer;
        color: $theme-blue;
        font-size: 100px;
      }
    }
  }

  &__spinner {
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    padding-top: 15%;
  }

  // make dash content scrollable
  .ant-tabs {
    height: 100%;
    .ant-tabs-content {
      height: calc(100% - 61px);
      .ant-tabs-tabpane-active {
        height: 100%;
      }
    }
  }

  &__content {
    position: relative;
    height: 100%;
    overflow: auto;
    padding-bottom: 16px;
  }
}
</style>
