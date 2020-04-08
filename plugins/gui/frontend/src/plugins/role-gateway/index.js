import _get from 'lodash/get';
import _find from 'lodash/find';
import _matchesProperty from 'lodash/matchesProperty';

import { PermissionCategory, PermissionAction } from '@constants/permissions';
import { entities } from '@constants/entities';
import RoleGateway from './RoleGateway.vue';

/* eslint-disable no-param-reassign */
function getCurrentUserPermissions() {
  return this.$store.getters.getCurrentUserPermissions;
}

// eslint-disable-next-line no-unused-vars
function isRoleEnabled(permissionCategory, permissionField, permissionSection = null) {
  // get current user permission from application state

  // the $isAdmin method is coming from this plugin itself
  const isAdmin = this.$isAdmin();
  if (isAdmin) {
    return true;
  }
  const userPermissions = getCurrentUserPermissions.call(this);
  const path = [permissionCategory];
  if (permissionSection) {
    path.push(permissionSection);
  }
  path.push(permissionField);
  return _get(userPermissions, path, false);

  // check user permission level per resource against the required permissions
  // const requiredPermissionScore = PermissionsLevelScore[permissionLevel];
  // const userPermissionScore = PermissionsLevelScore[userPermissions[permissionType]];
  //
  // return userPermissionScore >= requiredPermissionScore;
}

const RoleGatewayPlugin = {

  install(Vue) {
    // register XRoleGateway globally
    Vue.component('XRoleGateway', RoleGateway);

    Vue.prototype.$permissionConsts = {
      categories: PermissionCategory,
      actions: PermissionAction,
    };
    Vue.prototype.$can = function roleGatewayCan(permissionCategory,
      permissionFieldAction,
      permissionSection) {
      return isRoleEnabled.call(this, permissionCategory, permissionFieldAction, permissionSection);
    };

    Vue.prototype.$cannot = function roleGatewayCannot(permissionCategory,
      permissionAction,
      permissionSection) {
      return !isRoleEnabled.call(this, permissionCategory, permissionAction, permissionSection);
    };

    Vue.prototype.$isAdmin = function roleGatewayIsAdmin() {
      return this.$store.getters.IS_USER_ADMIN;
    };

    Vue.prototype.$isAxoniusUser = function roleGatewayIsOwner() {
      return this.$store.getters.IS_AXONIUS_USER;
    };

    Vue.prototype.$canViewEntity = function roleGatewayCanViewEntity(entity) {
      if (!entity) return false;
      const entityObject = _find(entities, _matchesProperty('name', entity));
      if (!entityObject) {
        // Return true if this isn't an entity
        return true;
      }
      const { permissionCategory } = entityObject;
      return isRoleEnabled.call(this, permissionCategory, PermissionAction.View);
    };

    Vue.prototype.$canEditEntity = function roleGatewayCanEditEntity(entity) {
      if (!entity) return false;
      const entityObject = _find(entities, _matchesProperty('name', entity));
      if (!entityObject) {
        // Return true if this isn't an entity
        return true;
      }
      const { permissionCategory } = entityObject;
      return isRoleEnabled.call(this, permissionCategory, PermissionAction.Update);
    };
  },
};

export default RoleGatewayPlugin;
