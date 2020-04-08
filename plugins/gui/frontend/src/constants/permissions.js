import _values from 'lodash/values';
import _remove from 'lodash/remove';
import _keys from 'lodash/keys';
import _includes from 'lodash/includes';
import _get from 'lodash/get';

export const RESTRICTED_ROLE_NAME = 'Restricted User';

export const PermissionCategory = {
  Settings: 'settings',
  Users: 'users',
  Roles: 'roles',
  Audit: 'audit',
  Dashboard: 'dashboard',
  Spaces: 'spaces',
  Charts: 'charts',
  DevicesAssets: 'devices_assets',
  UsersAssets: 'users_assets',
  SavedQueries: 'saved_queries',
  Instances: 'instances',
  Adapters: 'adapters',
  Connections: 'connections',
  Enforcements: 'enforcements',
  Tasks: 'tasks',
  Reports: 'reports',
  Compliance: 'compliance',
};

export const PermissionAction = {
  View: 'get',
  Add: 'put',
  Update: 'post',
  Delete: 'delete',
  GetUsersAndRoles: 'get_users_and_roles',
  ResetApiKey: 'reset_api_key',
  RunManualDiscovery: 'run_manual_discovery',
  Run: 'run',
  Open: 'open',
};

export const PermissionCategoryState = {
  full: 'Full Access',
  partial: 'Partial Access',
  none: 'No Access',
};

export const PermissionsStructure = [
  {
    name: 'settings',
    category: 'permissions.settings',
    actions: [
      'permissions.settings.get',
      'permissions.settings.get_users_and_roles',
      'permissions.settings.users.put',
      'permissions.settings.users.post',
      'permissions.settings.roles.put',
      'permissions.settings.users.delete',
      'permissions.settings.roles.post',
      'permissions.settings.roles.delete',
      'permissions.settings.reset_api_key',
      'permissions.settings.post',
      'permissions.settings.run_manual_discovery',
      'permissions.settings.audit.get',
    ],
  },
  {
    name: 'dashboard',
    category: 'permissions.dashboard',
    actions: [
      'permissions.dashboard.get',
      'permissions.dashboard.charts.delete',
      'permissions.dashboard.charts.put',
      'permissions.dashboard.charts.post',
      'permissions.dashboard.spaces.put',
      'permissions.dashboard.spaces.delete',
    ],
  },
  {
    name: 'devices_assets',
    category: 'permissions.devices_assets',
    actions: [
      'permissions.devices_assets.get',
      'permissions.devices_assets.post',
      'permissions.devices_assets.saved_queries.run',
      'permissions.devices_assets.saved_queries.post',
      'permissions.devices_assets.saved_queries.delete',
      'permissions.devices_assets.saved_queries.put',
    ],
  },
  {
    name: 'users_assets',
    category: 'permissions.users_assets',
    actions: [
      'permissions.users_assets.get',
      'permissions.users_assets.post',
      'permissions.users_assets.saved_queries.run',
      'permissions.users_assets.saved_queries.post',
      'permissions.users_assets.saved_queries.delete',
      'permissions.users_assets.saved_queries.put',
    ],
  },
  {
    name: 'reports',
    category: 'permissions.reports',
    actions: [
      'permissions.reports.get',
      'permissions.reports.put',
      'permissions.reports.post',
      'permissions.reports.delete',
    ],
  },
  {
    name: 'instances',
    category: 'permissions.instances',
    actions: [
      'permissions.instances.get',
      'permissions.instances.post',
    ],
  },
  {
    name: 'adapters',
    category: 'permissions.adapters',
    actions: [
      'permissions.adapters.get',
      'permissions.adapters.connections.put',
      'permissions.adapters.connections.post',
      'permissions.adapters.post',
      'permissions.adapters.connections.delete',
    ],
  },
  {
    name: 'enforcements',
    category: 'permissions.enforcements',
    actions: [
      'permissions.enforcements.get',
      'permissions.enforcements.post',
      'permissions.enforcements.put',
      'permissions.enforcements.tasks.get',
      'permissions.enforcements.delete',
      'permissions.enforcements.run',
    ],
  },
  {
    name: 'compliance',
    category: 'permissions.compliance',
    actions: [
      'permissions.compliance.get',
    ],
  },
];

export const getPermissionsStructure = (shouldShowCloudCompliance) => {
  const permissionStructure = [...PermissionsStructure];
  if (!shouldShowCloudCompliance) {
    _remove(permissionStructure, (permission) => permission.name === 'compliance');
  }
  return permissionStructure;
};

const getAccessMsg = (actionsNumber, permittedActions) => {
  let displayAccessMessage = PermissionCategoryState.none;
  if (permittedActions === actionsNumber) {
    displayAccessMessage = PermissionCategoryState.full;
  } else if (permittedActions) {
    displayAccessMessage = PermissionCategoryState.partial;
  }
  return displayAccessMessage;
};

export const getPermissionState = (labels, category, role) => {
  if (!role.permissions) {
    return PermissionCategoryState.none;
  }
  // extract category related actions
  const actionsUnderCurrentCategory = _keys(labels).filter((action) => _includes(action, category) && action !== `permissions.${category}`);
  // count permitted actions based on role permissions
  let permittedActions = 0;
  actionsUnderCurrentCategory.forEach((action) => {
    const result = _get(role, action);
    if (result === true) {
      permittedActions += 1;
    }
  });
  // get a display message
  return getAccessMsg(
    actionsUnderCurrentCategory.length,
    permittedActions,
  );
};
