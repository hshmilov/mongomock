import RoleGateway from './RoleGateway.vue';

/* eslint-disable no-param-reassign */
function getCurrentUserPermissions() {
  return this.$store.getters.getCurrentUserPermissions;
}

const PermissionsLevelScore = {
  Restricted: 0,
  ReadOnly: 1,
  ReadWrite: 2,
};

function isRoleEnabled(permissionType, permissionLevel) {
  // get current user permission from application state

  // the $isAdmin method is comming from this plugin itself
  const isAdmin = this.$isAdmin();
  if (isAdmin) {
    return true;
  }
  const userPermissions = getCurrentUserPermissions.call(this);

  // check user permission level per resource against the required permissions
  const requiredPermissionScore = PermissionsLevelScore[permissionLevel];
  const userPermissionScore = PermissionsLevelScore[userPermissions[permissionType]];

  return userPermissionScore >= requiredPermissionScore;
}

const RoleGatewayPlugin = {

  install(Vue) {
    // register XRoleGateway globally
    Vue.component('XRoleGateway', RoleGateway);

    Vue.prototype.$can = function roleGatewayCan(permissionType, permissionLevel) {
      return isRoleEnabled.call(this, permissionType, permissionLevel);
    };

    Vue.prototype.$cannot = function roleGatewayCannot(permissionType, permissionLevel) {
      return !isRoleEnabled.call(this, permissionType, permissionLevel);
    };

    Vue.prototype.$isAdmin = function roleGatewayIsAdmin() {
      return this.$store.getters.IS_USER_ADMIN;
    };
  },
};

export default RoleGatewayPlugin;
