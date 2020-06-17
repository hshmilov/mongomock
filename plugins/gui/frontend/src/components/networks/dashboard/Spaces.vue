<template>
  <div class="x-spaces">
    <XRoleGateway
      :permission-category="$permissionConsts.categories.Dashboard"
      :permission-section="$permissionConsts.categories.Spaces"
    >
      <template slot-scope="{ canAdd, canDelete }">
        <XTabs
          v-if="spaces.length"
          ref="tabs"
          :extendable="canAdd"
          :active-tab-url="true"
          @add="addNewSpace"
          @click="selectSpace"
        >
          <XTab
            :id="defaultSpace.uuid"
            :title="defaultSpace.name"
            :selected="currentSpace === defaultSpace.uuid"
            :editable="canAdd"
          >
            <span slot-scope="{ active }">
              <div class="space_action_bar">
                <XSpaceOptionsMenu
                  v-if="canAdd"
                  :editable="canAdd"
                  parent-selector=".space_action_bar"
                  @edit="openEditSpace(defaultSpace)"
                  @remove="confirmRemoveSpace(defaultSpace.uuid)"
                />
              </div>
              <XDefaultSpace
                v-if="active"
                :panels="defaultSpace.panels"
                :panels-order="defaultSpace.panels_order"
                @add="() => addNewPanel(defaultSpace.uuid)"
                @edit="editPanel"
              />
            </span>
          </XTab>
          <XTab
            v-if="$can($permissionConsts.categories.Dashboard,
                       $permissionConsts.actions.Add,
                       $permissionConsts.categories.Charts)"
            :id="personalSpace.uuid"
            :title="personalSpace.name"
            :selected="currentSpace === personalSpace.uuid"
          >
            <span slot-scope="{ active }">
              <div class="space_action_bar" />
              <XPanels
                v-if="active"
                :panels="personalSpace.panels"
                :panels-order="personalSpace.panels_order"
                @add="() => addNewPanel(personalSpace.uuid)"
                @edit="editPanel"
              />
            </span>
          </XTab>
          <XTab
            v-for="space in customSpaces"
            :id="space.uuid"
            :key="space.uuid"
            :title="space.name"
            :selected="currentSpace === space.uuid"
            :editable="canAdd"
            :removable="canDelete"
          >
            <span slot-scope="{ active }">
              <div class="space_action_bar">
                <XSpaceOptionsMenu
                  v-if="canAdd || canDelete"
                  :editable="canAdd"
                  :removable="canDelete"
                  parent-selector=".space_action_bar"
                  @edit="openEditSpace(space)"
                  @remove="confirmRemoveSpace(space.uuid)"
                />
              </div>
              <XPanels
                v-if="active"
                :panels="space.panels"
                :panels-order="space.panels_order"
                @add="() => addNewPanel(space.uuid, true)"
                @edit="editPanel"
              />
            </span>
          </XTab>
        </XTabs>
      </template>
    </XRoleGateway>
    <XWizard
      v-if="wizard.active"
      :space="wizard.space"
      :panel="wizard.panel"
      @close="closeWizard"
      @update="updateDashboard"
    />
    <MoveOrCopy
      v-if="moveOrCopyActive"
    />
    <XEditSpaceModal
      v-if="spaceEditModalActive"
      :space="selectedSpace"
      @confirm="onUpdateSpace"
      @cancel="closeAndResetEditSpace"
    />
  </div>
</template>

<script>
import { mapState, mapMutations, mapActions } from 'vuex';
import _get from 'lodash/get';
import {
  SAVE_DASHBOARD_SPACE, CHANGE_DASHBOARD_SPACE, REMOVE_DASHBOARD_SPACE,
  SET_CURRENT_SPACE, RESET_DASHBOARD_SORT,
} from '@store/modules/dashboard';
import XEditSpaceModal from '@networks/dashboard/EditSpaceModal.vue';
import XSpaceOptionsMenu from '@networks/dashboard/SpaceOptionsMenu.vue';
import XTabs from '../../axons/tabs/Tabs.vue';
import XTab from '../../axons/tabs/Tab.vue';
import XDefaultSpace from './DefaultSpace.vue';
import XPanels from './Panels.vue';
import XWizard from './Wizard.vue';
import MoveOrCopy from './MoveOrCopy.vue';

import { SpaceTypesEnum } from '../../../constants/dashboard';

export default {
  name: 'XSpaces',
  components: {
    XEditSpaceModal,
    XSpaceOptionsMenu,
    XTabs,
    XTab,
    XDefaultSpace,
    XPanels,
    XWizard,
    MoveOrCopy,
  },
  props: {
    spaces: {
      type: Array,
      required: true,
    },
  },
  data() {
    return {
      wizard: {
        active: false,
        space: '',
      },
      processing: false,
      editCustomSpace: false,
      moveOrCopy: {
        space: '',
      },
      spaceEditModalActive: false,
    };
  },
  computed: {
    ...mapState({
      moveOrCopyActive(state) {
        return state.dashboard.moveOrCopyActive;
      },
      currentSpace(state) {
        return state.dashboard.currentSpace || _get(this.defaultSpace, 'uuid');
      },
    }),
    defaultSpace() {
      return this.spaces.find((space) => space.type === SpaceTypesEnum.default);
    },
    personalSpace() {
      return this.spaces.find((space) => space.type === SpaceTypesEnum.personal);
    },
    customSpaces() {
      return this.spaces.filter((space) => space.type === SpaceTypesEnum.custom);
    },
    selectedSpace() {
      return this.spaces.find((space) => space.uuid === this.currentSpace);
    },
    newSpaceName() {
      for (let i = this.customSpaces.length - 1; i >= 0; i--) {
        const matches = this.customSpaces[i].name.match('Space (\\d+)');
        if (matches && matches.length > 1) {
          return `Space ${parseInt(matches[1], 10) + 1}`;
        }
      }
      return 'Space 1';
    },
  },
  methods: {
    ...mapMutations({
      selectSpace: SET_CURRENT_SPACE,
      resetDashboardSort: RESET_DASHBOARD_SORT,
    }),
    ...mapActions({
      saveSpace: SAVE_DASHBOARD_SPACE,
      updateSpace: CHANGE_DASHBOARD_SPACE,
      removeSpace: REMOVE_DASHBOARD_SPACE,
    }),
    addNewPanel(spaceId, isCustomSpace) {
      this.editCustomSpace = isCustomSpace;
      this.wizard.active = true;
      this.wizard.space = spaceId;
    },
    closeWizard() {
      this.wizard.active = false;
      this.wizard.space = '';
      this.wizard.panel = null;
      this.editCustomSpace = false;
    },
    editPanel(panel) {
      this.wizard.active = true;
      this.wizard.panel = { ...panel };
      this.wizard.space = this.currentSpace;
    },
    addNewSpace() {
      if (this.processing) return;
      this.processing = true;
      this.saveSpace(this.newSpaceName).then((spaceId) => {
        this.$nextTick(() => {
          this.openEditSpace();
          this.$refs.tabs.selectTab(spaceId);
          this.processing = false;
        });
      });
    },
    async onUpdateSpace(spaceData) {
      await this.updateSpace(spaceData);
      this.closeAndResetEditSpace();
    },
    updateDashboard(uuid) {
      this.resetDashboardSort({ uuid });
    },
    openEditSpace() {
      this.spaceEditModalActive = true;
    },
    closeAndResetEditSpace() {
      this.spaceEditModalActive = false;
    },
    confirmRemoveSpace(spaceId) {
      this.$safeguard.show({
        text: `
            <div>This space will be completely deleted from the system and</div>
            <div>no other user will be able to use it.</div>
            <div>Deleting the space is an irreversible action.</div>
            <div>Do you want to continue?</div>
          `,
        confirmText: 'Delete Space',
        onConfirm: () => {
          this.removeSpace(spaceId);
          this.$refs.tabs.selectTab(this.defaultSpace.uuid);
        },
      });
    },
  },
};
</script>

<style lang="scss">
    .x-spaces {
      height: calc(100% - 54px);
      .space_action_bar {
        display: flex;
        flex-direction: row-reverse;
        min-height: 30px;
        padding: 0 15px;
        .ant-dropdown-menu {
          min-width: 150px;
        }
      }
    }
</style>
