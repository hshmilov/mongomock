<template>
  <div class="role-gateway">
    <slot
      :allowed="isUserAllowed"
      :admin="isAdmin"
    />
  </div>
</template>

<script>
export default {
  name: 'XRoleGateway',
  props: {
    permissionType: {
      type: String,
      default: '',
    },
    permissionLevel: {
      type: String,
      default: '',
    },
  },
  computed: {
    isUserAllowed() {
      if (this.isAdmin) {
        return true;
      }
      return this.$can(this.permissionType, this.permissionLevel);
    },
    isAdmin() {
      return this.$isAdmin();
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
