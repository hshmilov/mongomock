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
        <VIcon
          size="18"
          class="entityAction-expression-handle"
        >$vuetify.icons.entityAction</VIcon>
        Actions</XButton>
      <AMenu
        v-if="selectionCount"
        slot="overlay"
      >
        <AMenuItem
          v-for="item in menuChildren"
          :id="item.title"
          :key="item.title"
          :disabled="item.disableLink"
          @click="activate(item)"
        >
          {{ item.title }}
          <ATooltip
            v-if="item.disableLink"
            :title="item.disabledDescription"
            placement="bottom"
          >
            <AIcon
              type="info-circle"
              theme="twoTone"
            />
          </ATooltip>
        </AMenuItem>
      </AMenu>
      <AMenu
        v-else
        slot="overlay"
      >
        <AMenuItem
          class="disabledMenuItem"
          disabled
        >
          {{ disabledMenuItemDescription }}
        </AMenuItem>
      </AMenu>
    </ADropdown>
    <XTagModal
      title="Tag"
      :module="module"
      :entities="entities"
      :entities-meta="entitiesMeta"
      @done="() => $emit('done', false)"
    />
    <XActionMenuItem
      title="Delete"
      :handle-save="deleteEntities"
      :message="`Deleted ${module}`"
      action-text="Delete"
    >
      <div class="warn-delete">
        You are about to delete {{ selectionCount }} {{ module }}.
      </div>
      <div>These {{ module }} could reappear in further scans
        if they are not removed or detached.</div>
      <div>Are you sure you want to delete these {{ module }}?</div>
    </XActionMenuItem>
    <slot />
    <XActionMenuItem
      :title="`Add custom data`"
      :handle-save="saveFields"
      :handle-close="initCustomFields"
      :message="`Custom data saved`"
      action-text="Save"
    >
      <XCustomFields
        v-model="customAdapterData"
        :module="module"
        :fields="fields"
      />
    </XActionMenuItem>
  </div>
</template>

<script>
import { mapState, mapActions, mapMutations } from 'vuex';
import { Icon, Tooltip, Dropdown, Menu } from 'ant-design-vue';
import XActionMenuItem from './ActionMenuItem.vue';
import XCustomFields from '../../networks/entities/view/CustomFields.vue';
import XTagModal from '../popover/TagModal.vue';
import XButton from '../../axons/inputs/Button.vue';

import {
  DELETE_DATA, DISABLE_DATA, SAVE_CUSTOM_DATA, FETCH_DATA_FIELDS,
} from '../../../store/actions';
import { UPDATE_DATA_VIEW } from '../../../store/mutations';

export default {
  name: 'XActionMenu',
  components: {
    XActionMenuItem,
    XTagModal,
    XCustomFields,
    XButton,
    AIcon: Icon,
    ATooltip: Tooltip,
    ADropdown: Dropdown,
    AMenu: Menu,
    AMenuItem: Menu.Item,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    entities: {
      type: Object,
      required: true,
    },
    entitiesMeta: {
      type: Object,
      default: () => {},
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      customAdapterData: [],
      dropDownOpened: false,
    };
  },
  computed: {
    ...mapState({
      dataCount(state) {
        return state[this.module].count.data;
      },
      fields(state) {
        const fields = state[this.module].fields.data;
        if (!fields) return [];
        if (!fields.specific) return fields.generic;
        return fields.specific.gui || fields.generic;
      },
    }),
    selectionCount() {
      if (this.entities.include === undefined || this.entities.include) {
        return this.entities.ids.length;
      }
      return this.dataCount - this.entities.ids.length;
    },
    disabledMenuItemDescription() {
      return `Select ${this.module} to see more actions`;
    },
    actionButtonClass() {
      return {
        entityMenuInactive: this.disabled,
        entityMenu: !this.disabled,
        menuOpened: this.dropDownOpened,
      };
    },
    menuChildren() {
      return this.$children.filter((item) => item.title);
    },
  },
  methods: {
    ...mapActions({
      disableData: DISABLE_DATA,
      deleteData: DELETE_DATA,
      saveCustomData: SAVE_CUSTOM_DATA,
      fetchDataFields: FETCH_DATA_FIELDS,
    }),
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    openCloseMenu(visible) {
      this.dropDownOpened = visible;
    },
    activate(item) {
      if (!item || !item.activate) return;
      this.dropDownOpened = false;
      if (item.itemActiveHandler && typeof item.itemActiveHandler === 'function') {
        const res = item.itemActiveHandler();
        if (!res) return;
      }
      item.activate();
    },
    deleteEntities() {
      return this.deleteData({
        module: this.module, selection: this.entities,
      }).then(() => this.$emit('done'));
    },
    saveFields() {
      return this.saveCustomData({
        module: this.module,
        selection: this.entities,
        data: this.customAdapterData,
      }).then(() => {
        this.fetchDataFields({ module: this.module });
        this.initCustomFields();
      });
    },
    initCustomFields() {
      this.customAdapterData = [];
    },
  },
};
</script>

<style lang="scss">
  /* If the ant menu item is disabled,
     We still want to make it appear in the same color as a regular ant menu item.
     So basically we are overriding the "disabled" behavior with the normal menu item color.
   */
  $ant-menu-item-color: #000000a6;

  .disabledMenuItem {
    color: $ant-menu-item-color;
  }
  .disabledMenuItem:hover {
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
