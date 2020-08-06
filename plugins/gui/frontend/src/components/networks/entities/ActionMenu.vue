<template>
  <div>
    <ADropdown
      :trigger="disabled?['']:['click']"
      placement="bottomRight"
      @visibleChange="openCloseMenu"
    >
      <XButton
        class="action"
        :class="actionButtonClass"
        type="link"
      >
        <XIcon
          type="thunderbolt"
        />Actions</XButton>
      <AMenu
        v-if="selectionCount"
        slot="overlay"
      >
        <AMenuItem
          id="tag"
          key="tag_entities"
          @click="handleModalClick(MODAL_ACTIONS.tag)"
        >
          Tag
        </AMenuItem>
        <AMenuItem
          id="delete"
          key="delete_entities"
          @click="handleModalClick(MODAL_ACTIONS.delete)"
        >
          Delete
        </AMenuItem>
        <AMenuItem
          id="link"
          key="link_entities"
          @click="handleModalClick(MODAL_ACTIONS.link)"
        >
          Link {{ module }}
        </AMenuItem>
        <AMenuItem
          id="unlink"
          key="unlink_entities"
          @click="handleModalClick(MODAL_ACTIONS.unlink)"
        >
          Unlink {{ module }}
        </AMenuItem>
        <ASubMenu
          id="enforce_options"
          title="Enforce"
        >
          <AMenuItem
            id="create_enforce"
            key="create_enforce_entities"
            :disabled="createNewEnforcementRestricted"
            @click="openEnforcementPanel"
          >
            Create New Enforcement
            <ATooltip
              v-if="createNewEnforcementRestricted"
              title="You don't have permission to create enforcements"
              placement="bottom"
            >
              <AIcon
                type="info-circle"
                theme="twoTone"
              />
            </ATooltip>
          </AMenuItem>
          <AMenuItem
            id="run_enforce"
            key="run_enforce_entities"
            :disabled="runEnforcementDisabled"
            @click="handleModalClick(MODAL_ACTIONS.enforce)"
          >
            Use Existing Enforcement
            <ATooltip
              v-if="runEnforcementDisabled"
              :title="disabledRunEnforcementTooltip"
              placement="bottom"
            >
              <AIcon
                type="info-circle"
                theme="twoTone"
              />
            </ATooltip>
          </AMenuItem>
        </ASubMenu>
        <AMenuItem
          id="filter_out"
          key="filter_out_from_query_results"
          :disabled="isAllSelected"
          @click="handleModalClick(MODAL_ACTIONS.filter_out_from_query_result)"
        >
          Filter out from query results
          <ATooltip
            v-if="isAllSelected"
            title="Select all is not applicable. Please use the query wizard to filter the query"
            placement="bottom"
          >
            <AIcon
              type="info-circle"
              theme="twoTone"
            />
          </ATooltip>
        </AMenuItem>
        <AMenuItem
          id="add_custom_data"
          key="add_custom_data"
          @click="handleModalClick(MODAL_ACTIONS.add_custom_data)"
        >
          Add custom data
        </AMenuItem>
      </AMenu>
      <AMenu
        v-else
        slot="overlay"
      >
        <AMenuItem
          class="disabled-menu-item"
          disabled
        >
          {{ disabledMenuItemDescription }}
        </AMenuItem>
      </AMenu>
    </ADropdown>
    <Component
      :is="actionModalComponent"
      ref="modalComponent"
      v-bind="actionModalProps"
      @done="onDone"
    />
    <XEnforcementPanel
      v-if="!createNewEnforcementRestricted"
      :visible="isEnforcementPanelOpen"
      :entities="entities"
      :module="module"
      :selection-count="selectionCount"
      @close="closeEnforcementPanel"
      @done="onDone"
    />
    <XEnforcementsFeatureLockTip
      :enabled="showEnforcementsLockTip"
      @close-lock-tip="closeEnforcementsLockTip"
    />
  </div>
</template>

<script>
import { mapActions, mapMutations, mapState } from 'vuex';
import _get from 'lodash/get';
import { SET_ENFORCEMENT } from '@store/modules/enforcements';
import { FETCH_DATA_CONTENT } from '@store/actions';
import {
  Icon, Tooltip, Dropdown, Menu,
} from 'ant-design-vue';
import XIcon from '@axons/icons/Icon';
import XButton from '@axons/inputs/Button.vue';
import XLinkModal from '@neurons/popover/LinkModal.vue';
import XUnlinkModal from '@neurons/popover/UnlinkModal.vue';
import XEnforceModal from '@neurons/popover/EnforceModal.vue';
import XFilterOutModal from '@neurons/popover/FilterOutModal.vue';
import XTagModal from '@neurons/popover/TagModal.vue';
import XDeleteModal from '@neurons/popover/DeleteModal.vue';
import XAddCustomDataModal from '@neurons/popover/AddCustomDataModal.vue';
import { ModalActionsEnum, ActionModalComponentByNameEnum } from '@constants/entities';
import XEnforcementsFeatureLockTip from '../enforcement/EnforcementsFeatureLockTip.vue';
import XEnforcementPanel from './panels/EnforcementPanel.vue';

export default {
  name: 'XEntitiesActionMenu',
  components: {
    XButton,
    AIcon: Icon,
    ATooltip: Tooltip,
    ADropdown: Dropdown,
    AMenu: Menu,
    AMenuItem: Menu.Item,
    ASubMenu: Menu.SubMenu,
    XIcon,
    XLinkModal,
    XUnlinkModal,
    XEnforceModal,
    XFilterOutModal,
    XTagModal,
    XDeleteModal,
    XAddCustomDataModal,
    XEnforcementPanel,
    XEnforcementsFeatureLockTip,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    entities: {
      type: Object,
      default: () => ({}),
    },
    entitiesMeta: {
      type: Object,
      default: () => ({}),
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      isEnforcementPanelOpen: false,
      showEnforcementsLockTip: false,
      dropDownOpened: false,
      actionModalComponent: '',
      actionModalProps: {},
    };
  },
  computed: {
    ...mapState({
      dataCount(state) {
        return state[this.module].count.data;
      },
      enforcementsLocked(state) {
        return !_get(state, 'settings.configurable.gui.FeatureFlags.config.enforcement_center', true);
      },
      noEnforcementSetsDefined(state) {
        return _get(state, 'enforcements.content.data', []).length === 0;
      },
    }),
    runExistingEnforcementRestricted() {
      return this.$cannot(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.View)
              || this.$cannot(this.$permissionConsts.categories.Enforcements,
                this.$permissionConsts.actions.Run);
    },
    createNewEnforcementRestricted() {
      return this.$cannot(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.Add)
              || this.$cannot(this.$permissionConsts.categories.Enforcements,
                this.$permissionConsts.actions.Run);
    },
    actionButtonClass() {
      return {
        entityMenuInactive: this.disabled,
        entityMenu: !this.disabled,
        menuOpened: this.dropDownOpened,
      };
    },
    isAllSelected() {
      return this.entities.include !== undefined && !this.entities.include;
    },
    selectionCount() {
      if (this.entities.include === undefined || this.entities.include) {
        return this.entities.ids.length;
      }
      return this.dataCount - this.entities.ids.length;
    },
    disabledMenuItemDescription() {
      return `Select ${this.module} to see more actions`;
    },
    runEnforcementDisabled() {
      return this.runExistingEnforcementRestricted || this.noEnforcementSetsDefined;
    },
    disabledRunEnforcementTooltip() {
      return this.runExistingEnforcementRestricted ? 'You don\'t have permission to run enforcements'
        : 'No Enforcement Sets are configured';
    },
  },
  created() {
    this.MODAL_ACTIONS = ModalActionsEnum;
  },
  mounted() {
    if (this.noEnforcementSetsDefined && !this.runExistingEnforcementRestricted) {
      this.fetchContent({
        module: 'enforcements',
        getCount: false,
      });
    }
  },
  methods: {
    ...mapActions(
      {
        fetchContent: FETCH_DATA_CONTENT,
      },
    ),
    ...mapMutations({
      setEnforcement: SET_ENFORCEMENT,
    }),
    openCloseMenu(visible) {
      this.dropDownOpened = visible;
    },
    onDone(reset) {
      this.$emit('done', reset);
    },
    handleModalClick(modalName) {
      this.dropDownOpened = false;
      if (modalName === ModalActionsEnum.enforce && this.enforcementsLocked) {
        this.openEnforcementsLockTip();
        return;
      }
      this.actionModalProps = {
        entities: this.entities,
        module: this.module,
        selectionCount: this.selectionCount,
        entitiesMeta: this.entitiesMeta,
      };
      this.actionModalComponent = ActionModalComponentByNameEnum[modalName];
      this.$nextTick(() => {
        this.$refs.modalComponent.activate();
      });
    },
    openEnforcementPanel() {
      this.dropDownOpened = false;
      if (this.enforcementsLocked) {
        this.openEnforcementsLockTip();
      } else {
        // Reset the current enforcement data
        // (it is used in the panel as a template for creating a new one)
        this.setEnforcement();
        this.isEnforcementPanelOpen = true;
      }
    },
    closeEnforcementPanel() {
      this.isEnforcementPanelOpen = false;
    },
    openEnforcementsLockTip() {
      this.showEnforcementsLockTip = true;
    },
    closeEnforcementsLockTip() {
      this.showEnforcementsLockTip = false;
    },
  },
};
</script>

<style lang="scss">
  .x-form.expand .item {
    width: 100%;

    .object {
      width: 100%;
    }
  }
  /* If the ant menu item is disabled,
   We still want to make it appear in the same color as a regular ant menu item.
   So basically we are overriding the "disabled" behavior with the normal menu item color.
 */
  $ant-menu-item-color: #000000a6;

  .disabled-menu-item {
    color: $ant-menu-item-color;
  }
  .disabled-menu-item:hover {
    color: $ant-menu-item-color;
  }
  .ant-tooltip-inner {
    font-weight: bolder;
  }
  .ant-dropdown-menu-item {
    svg {
      margin-left: 4px;
    }
  }
</style>
