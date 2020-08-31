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
        v-if="dropDownOpened"
        slot="overlay"
      >
        <AMenuItem
          id="edit_user_columns"
          key="0"
          @click="() => openColumnEditor('user')"
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
        <AMenuItem
          v-if="canUpdateSettings"
          id="edit_system_default"
          key="3"
          @click="() => openColumnEditor('system')"
        >
          {{ editSystemDefaultMenuTitle }}
        </AMenuItem>
      </AMenu>
    </ADropdown>
    <XButton
      type="link"
      class="entityMenu"
      :disabled="disableExportCsv || exportInProgress"
      @click.stop.prevent="openCsvExportConfig"
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
    <XEditUserColumnsModal
      v-if="columnEditor.user"
      :module="module"
      :user-fields-groups.sync="userFieldsGroupsSync"
      @done="done"
      @close="closeColumnEditor"
      @reset-user-fields="resetColumnsToUserDefault"
    />
    <XEditSystemColumnsModal
      v-if="columnEditor.system"
      :module="module"
      @done="done"
      @close="closeColumnEditor"
    />
    <XCsvExportConfig
      v-if="showCsvExportConfig"
      @close-csv-export-config="closeCsvExportConfig"
      @run-csv-export-config="exportTableToCSV"
    />
  </div>
</template>

<script>
import {
  mapMutations, mapActions, mapState, mapGetters,
} from 'vuex';
import { Dropdown, Menu } from 'ant-design-vue';
import _get from 'lodash/get';
import _snakeCase from 'lodash/snakeCase';
import { SHOW_TOASTER_MESSAGE, UPDATE_DATA_VIEW, CLEAR_DATA_VIEW_FILTERS } from '@store/mutations';
import { FETCH_DATA_CONTENT_CSV } from '@store/actions';
import {
  FILL_USER_FIELDS_GROUPS_FROM_TEMPLATES,
  GET_SYSTEM_COLUMNS,
} from '@store/getters';
import XEditUserColumnsModal from './EditUserColumnsModal.vue';
import XEditSystemColumnsModal from './EditSystemColumnsModal.vue';
import XCsvExportConfig from './CsvExportConfig.vue';
import XButton from '../../axons/inputs/Button.vue';

export default {
  name: 'XOptionMenu',
  components: {
    XEditUserColumnsModal,
    XEditSystemColumnsModal,
    XCsvExportConfig,
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
      default: () => ({}),
    },
    disableExportCsv: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      exportInProgress: false,
      columnEditor: {
        user: false,
        system: false,
      },
      dropDownOpened: false,
      showCsvExportConfig: false,
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
      getSystemColumns: GET_SYSTEM_COLUMNS,
    }),
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
    editSystemDefaultMenuTitle() {
      return !this.querySearchTemplate
        ? 'Edit System Default'
        : 'Edit System Search Default';
    },
    columnButtonClass() {
      return {
        menuOpened: this.dropDownOpened,
      };
    },
    canUpdateSettings() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.Update);
    },
    columnsGroupName() {
      return !this.querySearchTemplate ? 'default' : _snakeCase(this.querySearchTemplate.name);
    },
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
      showToasterMessage: SHOW_TOASTER_MESSAGE,
      clearViewFilters: CLEAR_DATA_VIEW_FILTERS,
    }),
    ...mapActions({
      fetchContentCSV: FETCH_DATA_CONTENT_CSV,
    }),
    openColumnEditor(type) {
      this.dropDownOpened = false;
      this.columnEditor[type] = true;
    },
    closeColumnEditor() {
      this.columnEditor = { user: false, system: false };
    },
    resetColumnsToUserDefault() {
      let fieldsForReset = this.userFieldsGroups.default;
      if (this.querySearchTemplate) {
        fieldsForReset = this.userFieldsGroups[_snakeCase(this.querySearchTemplate.name)];
        if (!fieldsForReset) {
          fieldsForReset = this.getSystemColumns(this.module, _snakeCase(this.querySearchTemplate.name));
        }
      }
      this.updateTableColumns(fieldsForReset);
      this.clearViewFilters({ module: this.module });
    },
    resetColumnsToSystemDefault() {
      const fieldsForReset = this.getSystemColumns(this.module, this.columnsGroupName);
      this.updateTableColumns(fieldsForReset);
      this.clearViewFilters({ module: this.module });
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
    exportTableToCSV(delimiter, maxRows) {
      this.closeCsvExportConfig();
      this.exportInProgress = true;
      this.fetchContentCSV({
        module: this.module,
        delimiter,
        maxRows,
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
    openCsvExportConfig() {
      this.showCsvExportConfig = true;
    },
    closeCsvExportConfig() {
      this.showCsvExportConfig = false;
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
