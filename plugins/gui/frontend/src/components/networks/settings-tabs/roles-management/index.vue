<template>
  <XRoleGateway
    :permission-category="$permissionConsts.categories.Settings"
    :permission-section="$permissionConsts.categories.Roles"
  >
    <template slot-scope="{ canAdd }">
      <div class="x-roles-table">
        <XTableWrapper
          title="Roles"
          :count="formattedRoles.length"
        >
          <template slot="actions">
            <XButton
              id="add-role-btn"
              type="primary"
              :disabled="!canAdd"
              @click="handleAddRole"
            >Add Role</XButton>
          </template>
          <template slot="table">
            <XTable
              v-model="rolesRowsSelections"
              module="auth"
              :on-click-row="openEditRolePanel"
              :data="formattedRoles"
              :fields="rolesTableFieldsSchema"
              :multiple-row-selection="false"
            />
          </template>
        </XTableWrapper>
      </div>
      <XRolePanel
        v-model="isPanelOpen"
        :role="currentRole"
        @input="(value) => !value && closePanel()"
        @duplicate="handleDuplicateRole"
      />
    </template>>
  </XRoleGateway>
</template>

<script>
import { mapGetters, mapState, mapActions } from 'vuex';
import XTable from '@axons/tables/Table.vue';
import XTableWrapper from '@axons/tables/TableWrapper.vue';
import XButton from '@axons/inputs/Button.vue';
import _find from 'lodash/find';
import _cloneDeep from 'lodash/cloneDeep';
import {
  GET_ALL_ROLES,
  REMOVE_ROLE,
  GET_PERMISSION_STRUCTURE,
} from '@store/modules/auth';
import { LAZY_FETCH_LABELS, GET_LABELS } from '@store/modules/labels';
import { getPermissionState, RESTRICTED_ROLE_NAME } from '@constants/permissions';
import XRolePanel from './panels/RolePanel';

export default {
  name: 'XRolesTable',
  components: {
    XTable, XButton, XTableWrapper, XRolePanel,
  },
  data() {
    return {
      isPanelOpen: false,
      currentRole: {},
      selection: [],
      roleToDuplicate: null,
    };
  },
  computed: {
    ...mapState({
      roles(state) {
        return state.auth.allRoles.data;
      },
    }),
    ...mapGetters({
      getLabels: GET_LABELS, getPermissionsStructure: GET_PERMISSION_STRUCTURE,
    }),
    allRoleNames() {
      try {
        let names = this.roles.map((role) => role.name);
        names = names.map((q) => q.toLocaleLowerCase());
        return new Set(names);
      } catch (ex) {
        return new Set();
      }
    },
    formattedRoles() {
      if (!this.roles) {
        return [];
      }
      return this.roles.map((role) => ({
        uuid: role.uuid,
        name: role.name,
        ...this.formatRole(role),
      }));
    },
    numberOfSelections() {
      return this.selection.length ? this.selection.length : 0;
    },
    userCannotDeleteRoles() {
      return this.$cannot(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.Delete, this.$permissionConsts.categories.Roles);
    },
    rolesRowsSelections: {
      get() {
        return this.userCannotDeleteRoles ? undefined : this.selection;
      },
      set(newSelections) {
        this.selection = newSelections;
      },
    },
    getPermissionCategories() {
      if (!this.getLabels) {
        return [];
      }
      const permissionCategoriesLabels = [];
      this.getPermissionsStructure.forEach((permissionCategory) => {
        const permissionLabelKey = permissionCategory.category;
        permissionCategoriesLabels.push({
          name: permissionCategory.name,
          title: this.getLabels[permissionLabelKey],
          type: 'string',
        });
      });
      return permissionCategoriesLabels;
    },
    rolesTableFieldsSchema() {
      return [
        {
          name: 'name',
          title: 'Role',
          type: 'string',
        },
        ...this.getPermissionCategories,
      ];
    },
    baseRolePermissions() {
      return _find(this.roles, (role) => role.name === RESTRICTED_ROLE_NAME
        && role.predefined).permissions;
    },
  },
  async created() {
    await this.fetchLabels();
    this.fetchAllRoles();
  },
  methods: {
    ...mapActions({
      fetchAllRoles: GET_ALL_ROLES,
      removeRole: REMOVE_ROLE,
      fetchLabels: LAZY_FETCH_LABELS,
    }),
    openEditRolePanel(selectedRoleId) {
      if (selectedRoleId) {
        this.selection = [selectedRoleId];
      }
      this.currentRole = _cloneDeep(_find(this.roles, { uuid: this.selection[0] }));
      this.isPanelOpen = true;
    },
    handleAddRole() {
      const restrictedPermissions = this.baseRolePermissions;
      this.currentRole = {
        name: '',
        permissions: _cloneDeep(restrictedPermissions),
      };
      this.isPanelOpen = true;
    },
    getNewRoleName(baseName, isCopy) {
      let name = baseName;
      let counter = 1;
      while (this.allRoleNames.has(name.toLocaleLowerCase())) {
        name = isCopy ? `Copy ${counter} ${baseName}` : `${baseName} ${counter}`;
        counter += 1;
      }
      return name;
    },
    handleDuplicateRole() {
      const roleToDuplicate = _cloneDeep(_find(this.roles, { uuid: this.selection[0] }));
      this.currentRole = {
        name: this.getNewRoleName(roleToDuplicate.name, true),
        permissions: roleToDuplicate.permissions,
      };
      this.isPanelOpen = true;
    },
    closePanel() {
      this.currentRole = {};
      this.selection = [];
      this.isPanelOpen = false;
    },
    formatRole(role) {
      const formattedPermissions = {};
      this.getPermissionsStructure.forEach((category) => {
        formattedPermissions[category.name] = getPermissionState(this.getLabels,
          category.name, role);
      });
      return formattedPermissions;
    },
  },
};
</script>

<style lang="scss">
  .x-roles-table {
    height: 100%;

    .table-header {
      background: $theme-white;
    }

    .duplicate-role-btn {
      width: 150px;
    }

  }

</style>
