<template>
  <div class="role-gateway">
    <slot
      :canView="canView"
      :canAdd="canAdd"
      :canUpdate="canUpdate"
      :canDelete="canDelete"
      :allowed="isUserAllowed"
      :admin="isAdmin"
      :is-action-allowed="isActionAllowed"
    />
  </div>
</template>

<script>
import { PermissionAction } from '@constants/permissions';

export default {
  name: 'XRoleGateway',
  props: {
    permissionCategory: {
      type: String,
      default: '',
    },
    permissionAction: {
      type: String,
      default: '',
    },
    permissionSection: {
      type: String,
      default: '',
    },
  },
  computed: {
    canView() {
      return this.isActionAllowed(PermissionAction.View);
    },
    canAdd() {
      return this.isActionAllowed(PermissionAction.Add);
    },
    canUpdate() {
      return this.isActionAllowed(PermissionAction.Update);
    },
    canDelete() {
      return this.isActionAllowed(PermissionAction.Delete);
    },
    isUserAllowed() {
      if (this.isAdmin) {
        return true;
      }
      return this.$can(this.permissionCategory, this.permissionAction, this.permissionSection);
    },
    isAdmin() {
      return this.$isAdmin();
    },
    isAxoniusUser() {
      return this.$isAxoniusUser();
    },
  },
  methods: {
    isActionAllowed(action, subCategory) {
      if (this.isAdmin) {
        return true;
      }
      return this.$can(this.permissionCategory, action, subCategory || this.permissionSection);
    },
  },
};
</script>

<style lang="scss">
  .role-gateway {
    width: 100%;
    height: 100%;
  }
</style>
