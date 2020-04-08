<template>
  <div class="x-users-management-actions-menu">
    <XRoleGateway
      :permission-category="$permissionConsts.categories.Settings"
      :permission-section="$permissionConsts.categories.Users"
    >
      <template slot-scope="{ canUpdate, canDelete }">
        <VMenu offset-y>
          <template v-slot:activator="{ on }">
            <XButton
              :disabled="disabled || (!canDelete && !canUpdate)"
              link
              v-on="on"
            >Actions
            </XButton>
          </template>
          <VList class="x-users-management-actions-menu__list">
            <VListItem
              v-if="canDelete"
              @click="callDeleteUsers"
            >
              <VListItemTitle>
                Delete Users
              </VListItemTitle>
            </VListItem>
            <VListItem
              v-if="canUpdate"
              @click="callAssignRole"
            >
              <VListItemTitle>
                Assign Role
              </VListItemTitle>
            </VListItem>
          </VList>
        </VMenu>
      </template>
    </XRoleGateway>
  </div>
</template>

<script>
import XButton from '@axons/inputs/Button.vue';

export default {
  name: 'XActionsMenu',
  components: { XButton },
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
