<template>
  <XRoleGateway
    :permission-category="$permissionConsts.categories.Settings"
    :permission-section="$permissionConsts.categories.Users"
  >
    <template slot-scope="{ canAdd, canUpdate, canDelete }">
      <div class="x-users-management">
        <XModalAssignRole
          :value="modal"
          :count="selectedRowsCount"
          @close="modal = false"
          @assignrole="assignSelectedUsersRole"
        />
        <XTable
          v-model="selectedRows"
          title="Users"
          module="auth/allUsers"
          endpoint="settings/users"
          :fields="tableColumnsSchema"
          :multiple-row-selection="canUpdate || canDelete"
          :on-click-row="canUpdate ? openSidePanel : undefined"
          :read-only="readOnlyRows"
        >
          <template slot="actions">
            <XActionsMenu
              :disabled="!isActionEnabled"
              @delete="deleteSelectedUsers"
              @assign="openModalAssignRole"
            />
            <XButton
              type="primary"
              :disabled="!canAdd"
              @click="onCreateNewUser"
            >Add User</XButton>
          </template>
        </XTable>
        <XUsersPanel
          v-model="isPanelOpen"
          :panel-type="panelType"
          :user-id="editUserId"
          :title="UserSidePanelTitle"
          @close="onPanelClose"
          @delete="callDeleteUser"
          @reset-password="onResetPassword"
        />
        <XModalResetPassword
          v-if="resetPasswordInfo"
          :user-id="resetPasswordInfo ? resetPasswordInfo.userId : ''"
          :user-email="resetPasswordInfo ? resetPasswordInfo.email : ''"
          :invite="resetPasswordInfo ? resetPasswordInfo.invite : false"
          :user-name="resetPasswordInfo ? resetPasswordInfo.userName : ''"
          @close="closeResetPassword"
        />
      </div>
    </template>
  </XRoleGateway>
</template>

<script>

import {
  GET_ALL_USERS, REMOVE_USERS,
  GET_SYSTEM_USERS_MAP,
  GET_SYSTEM_ROLES_MAP,
  GET_ADMIN_USER_ID,
  UPDATE_USERS_ROLE,
  GET_ALL_ROLES,
} from '@store/modules/auth';
import { mapActions, mapGetters, mapMutations } from 'vuex';

import _capitalize from 'lodash/capitalize';

import XTable from '@neurons/data/Table.vue';
import XButton from '@axons/inputs/Button.vue';
import { SHOW_TOASTER_MESSAGE } from '@store/mutations';
import XUsersPanel from './side-panels/user-panel.vue';
import XActionsMenu from './actions-menu.vue';
import XModalAssignRole from './modal-assign-role.vue';
import XModalResetPassword from './modal-reset-password.vue';

export default {
  name: 'XUsersManagement',
  components: {
    XTable,
    XButton,
    XUsersPanel,
    XActionsMenu,
    XModalAssignRole,
    XModalResetPassword,
  },
  data() {
    return {
      modal: false,
      isPanelOpen: false,
      panelType: 'new',
      UserSidePanelTitle: 'New User',
      selectedRows: { ids: [], include: true },
      resetPasswordInfo: null,
      tableColumnsSchema: [{
        name: 'user_name', title: 'User Name', type: 'string',
      }, {
        name: 'first_name', title: 'First Name', type: 'string',
      }, {
        name: 'last_name', title: 'Last Name', type: 'string',
      }, {
        name: 'email', title: 'Email', type: 'string',
      }, {
        name: 'role_id',
        title: 'Role',
        type: 'string',
        cellRenderer: (roleId) => {
          const role = this.rolesMap[roleId] || {};
          return role.name || 'Owner';
        },
      }, {
        name: 'source',
        title: 'Source',
        type: 'string',
        cellRenderer: (source) => (source.toLowerCase() !== 'internal' ? source.toUpperCase() : _capitalize(source)),
      }, {
        name: 'last_login', title: 'Last Login', type: 'string', format: 'date-time',
      }, {
        name: 'last_updated', title: 'Last Updated', type: 'string', format: 'date-time',
      }],
    };
  },
  computed: {
    ...mapGetters({
      usersMap: GET_SYSTEM_USERS_MAP,
      rolesMap: GET_SYSTEM_ROLES_MAP,
      adminUserUuid: GET_ADMIN_USER_ID,
    }),
    editUserId() {
      return this.isPanelOpen ? this.selectedRows.ids[0] : undefined;
    },
    selectedRowsCount() {
      return this.selectedRows.ids.length;
    },
    zeroSelectedRows() {
      return this.selectedRowsCount === 0;
    },
    isActionEnabled() {
      // batch actions not allowed on admin user that was created by the system
      if (!this.selectedRows.include) {
        return false;
      }
      return !this.zeroSelectedRows && !this.selectedRows.ids.includes(this.adminUserUuid);
    },
    readOnlyRows() {
      // only admin user that was created by the system can open it's own panels
      return this.$isAdmin() ? [] : [this.adminUserUuid];
    },
  },
  created() {
    this.fetchAllUsers();
    this.fetchAllRoles();
  },
  methods: {
    ...mapMutations({
      showSnackbar: SHOW_TOASTER_MESSAGE,
    }),
    ...mapActions({
      fetchAllUsers: GET_ALL_USERS,
      fetchAllRoles: GET_ALL_ROLES,
      removerUsers: REMOVE_USERS,
      assignUsersRole: UPDATE_USERS_ROLE,
    }),
    onCreateNewUser() {
      this.panelType = 'new';
      this.isPanelOpen = true;
      this.selectedRows = { ids: [], include: true };
    },
    openSidePanel(selectedId) {
      const user = this.usersMap[selectedId];
      const { source } = user;

      this.UserSidePanelTitle = user.user_name;
      this.panelType = source === 'internal' ? source : 'external';
      this.isPanelOpen = !this.isPanelOpen;
      this.selectedRows = { ids: [selectedId], include: true };
    },
    onPanelClose() {
      this.isPanelOpen = false;
      this.UserSidePanelTitle = 'New User';
    },
    deleteSelectedUsers() {
      this.$safeguard.show({
        text: this.selectedRowsCount > 1
          ? `The ${this.selectedRowsCount} users will be deleted from the Axonius system`
          : 'The user will be deleted from the Axonius system',
        confirmText: 'Yes, Delete',
        onConfirm: async () => {
          await this.removerUsers(this.selectedRows);
          this.showSnackbar({ message: 'Users removed.' });
          this.selectedRows = { ids: [], include: true };
        },
      });
    },
    openModalAssignRole() {
      this.modal = true;
    },
    callDeleteUser() {
      this.modal = false;
      this.deleteSelectedUsers();
    },
    assignSelectedUsersRole(roleId) {
      this.assignUsersRole({ ...this.selectedRows, roleId });
      this.modal = false;
    },
    onResetPassword(resetPasswordInfo) {
      /*
      The reset password info structure:
      {
        userId - the new or updated user uuid,
        email - the email saved in the user,
        invite - should the mail be sent as an invitation,
        onClose - what function to call after the reset password is closed
      }
       */
      this.resetPasswordInfo = resetPasswordInfo;
    },
    async closeResetPassword() {
      await this.resetPasswordInfo.onClose();
      this.resetPasswordInfo = null;
    },
  },
};
</script>

<style lang="scss">
 .x-users-management {
   height: 100%;
   .table-header {
     background-color: $theme-white;
   }
 }
</style>
