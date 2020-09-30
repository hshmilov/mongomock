<template>
  <div class="x-users-management-actions-menu">
    <XRoleGateway
      :permission-category="$permissionConsts.categories.Settings"
      :permission-section="$permissionConsts.categories.Users"
    >
      <template slot-scope="{ canUpdate, canDelete }">
        <ADropdown
          class="user-management_actions__menu"
          :disabled="disabled || (!canDelete && !canUpdate)"
          :trigger="['click']"
          placement="bottomCenter"
        >
          <XButton type="link">Actions</XButton>
          <AMenu
            slot="overlay"
          >
            <AMenuItem
              v-if="canDelete"
              @click="callDeleteUsers"
              id="delete_users"
              key="0"
            >Delete Users</AMenuItem>
            <AMenuItem
              v-if="canUpdate"
              @click="callAssignRole"
              id="assign_role"
              key="1"
            >Assign Role</AMenuItem>
          </AMenu>
        </ADropdown>
      </template>
    </XRoleGateway>
  </div>
</template>

<script>
import { Menu, Dropdown } from 'ant-design-vue';

export default {
  name: 'XActionsMenu',
  components: {
    ADropdown: Dropdown,
    AMenu: Menu,
    AMenuItem: Menu.Item,
  },
  props: {
    disabled: {
      type: Boolean,
      default: true,
    },
  },
  methods: {
    callDeleteUsers() {
      this.$emit('delete');
    },
    callAssignRole() {
      this.$emit('assign');
    },
  },
};
</script>

<style lang="scss">
  .x-users-management-actions-menu__list .v-list-item__title {
    font-size: 14px;
  }
</style>
