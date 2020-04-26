<template>
  <div class="x-option-menu">
    <ADropdown
      :trigger="['click']"
      placement="bottomRight"
      @visibleChange="openCloseMenu"
    >
      <XButton
        class="entityMenu"
        :class="columnButtonClass"
        type="link"
      >
        <VIcon
          size="18"
          class="entityColumn-expression-handle"
        >$vuetify.icons.entityColumn</VIcon>
        Edit Columns</XButton>
      <AMenu
        slot="overlay"
      >
        <AMenuItem
          id="edit_columns"
          key="0"
          @click="openColumnEditor"
        >
          Edit Columns
        </AMenuItem>
        <AMenuItem
          id="reset_user_default"
          key="1"
          @click="resetColumnsToUserDefault"
        >
          {{ resetToUserDefaultMenuTitle }}
        </AMenuItem>
        <AMenuItem
          id="reset_system_default"
          key="2"
          @click="resetColumnsToSystemDefault"
        >
          {{ resetToSystemDefaultMenuTitle }}
        </AMenuItem>
      </AMenu>
    </ADropdown>
    <XButton
      type="link"
      class="entityMenu"
      :disabled="disableExportCsv || exportInProgress"
      @click.stop.prevent="exportTableToCSV"
    >
      <div v-if="exportInProgress">
        <VProgressCircular
          indeterminate
          color="primary"
          :width="2"
          :size="16"
        />
        Exporting...
      </div>
      <div v-else>
        <VIcon
          size="18"
          class="entityExport-expression-handle"
        >$vuetify.icons.entityExport</VIcon>
        Export CSV</div>
    </XButton>
    <XFieldConfig
      v-if="showColumnEditor"
      :module="module"
      :user-fields-groups.sync="userFieldsGroupsSync"
      @done="done"
      @close="closeColumnEditor"
      @reset-user-fields="resetColumnsToUserDefault"
    />
  </div>
</template>

<script>
import { mdiDotsHorizontal } from '@mdi/js';

import {
  mapMutations, mapActions, mapState, mapGetters,
} from 'vuex';
import { Dropdown, Menu } from 'ant-design-vue';
import _get from 'lodash/get';
import _snakeCase from 'lodash/snakeCase';
import { SHOW_TOASTER_MESSAGE, UPDATE_DATA_VIEW } from '@store/mutations';
import { FETCH_DATA_CONTENT_CSV } from '@store/actions';
import { defaultFields } from '@constants/entities';
import { FILL_USER_FIELDS_GROUPS_FROM_TEMPLATES } from '@store/getters';
import XButton from '../../axons/inputs/Button.vue';
import XFieldConfig from './FieldConfig.vue';

export default {
  name: 'XOptionMenu',
  components: {
    XFieldConfig,
    XButton,
    ADropdown: Dropdown,
    AMenu: Menu,
    AMenuItem: Menu.Item,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    userFieldsGroups: {
      type: Object,
      default: () => ({ default: defaultFields[this.module] }),
    },
    disableExportCsv: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      exportInProgress: false,
      showColumnEditor: false,
      dropDownOpened: false,
    };
  },
  computed: {
    ...mapState({
      querySearchTemplate(state) {
        return _get(state[this.module].view, 'query.meta.searchTemplate', false);
      },
      templateViews(state) {
        return state[this.module].views.template.content.data || [];
      },
    }),
    ...mapGetters({
      fillUserFieldGroups: FILL_USER_FIELDS_GROUPS_FROM_TEMPLATES,
    }),
    dotsIcon() {
      return mdiDotsHorizontal;
    },
    userFieldsGroupsSync: {
      get() {
        return this.userFieldsGroups;
      },
      set(value) {
        this.$emit('update:user-fields-groups', value);
      },
    },
    resetToUserDefaultMenuTitle() {
      return this.querySearchTemplate ? 'Reset Columns to User Search Default' : 'Reset Columns to User Default';
    },
    resetToSystemDefaultMenuTitle() {
      return this.querySearchTemplate ? 'Reset Columns to System Search Default' : 'Reset Columns to System Default';
    },
    columnButtonClass() {
      return {
        menuOpened: this.dropDownOpened,
      };
    },
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
      showToasterMessage: SHOW_TOASTER_MESSAGE,
    }),
    ...mapActions({
      fetchContentCSV: FETCH_DATA_CONTENT_CSV,
    }),
    openColumnEditor() {
      this.dropDownOpened = false;
      this.showColumnEditor = true;
    },
    closeColumnEditor() {
      this.showColumnEditor = false;
    },
    resetColumnsToUserDefault() {
      let fieldsForReset = this.userFieldsGroups.default;
      if (this.querySearchTemplate) {
        const allFieldsGroup = this.fillUserFieldGroups(this.module, this.userFieldsGroups);
        fieldsForReset = allFieldsGroup[_snakeCase(this.querySearchTemplate.name)];
      }
      this.updateTableColumns(fieldsForReset);
    },
    resetColumnsToSystemDefault() {
      let fieldsForReset = defaultFields[this.module];
      if (this.querySearchTemplate) {
        const template = this.templateViews
          .find((item) => item.name === this.querySearchTemplate.name);
        fieldsForReset = _get(template, 'view.fields', []);
      }
      this.updateTableColumns(fieldsForReset);
    },
    updateTableColumns(fields) {
      this.updateView({
        module: this.module,
        view: {
          fields,
        },
      });
      this.done();
    },
    exportTableToCSV() {
      this.exportInProgress = true;
      this.fetchContentCSV({
        module: this.module,
      }).then(() => {
        this.exportInProgress = false;
      });
    },
    openCloseMenu(visible) {
      this.dropDownOpened = visible;
    },
    done() {
      this.dropDownOpened = false;
      this.$emit('done');
    },
  },
};
</script>

<style lang="scss">
.x-option-menu {
  .v-progress-circular {
    margin-right: 4px;
  }

  &__content {
    .v-list--dense .v-list-item__title {
      font-weight: 300;
    }
  }
}
</style>
