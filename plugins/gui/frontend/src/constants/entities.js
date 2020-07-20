import _find from 'lodash/find';
import _matchesProperty from 'lodash/matchesProperty';
import { PermissionCategory } from '@constants/permissions';


export const entities = [
  {
    name: 'devices', title: 'Devices', permissionCategory: PermissionCategory.DevicesAssets,
  }, {
    name: 'users', title: 'Users', permissionCategory: PermissionCategory.UsersAssets,
  },
];

export const getEntityPermissionCategory = (entity) => {
  const { permissionCategory } = _find(entities, _matchesProperty('name', entity));
  return permissionCategory;
};

export const EntitiesEnum = {
  devices: 'devices',
  users: 'users',
};

export const defaultFields = {
  devices: [
    'adapters', 'specific_data.data.name', 'specific_data.data.hostname', 'specific_data.data.last_seen',
    'specific_data.data.network_interfaces.mac', 'specific_data.data.network_interfaces.ips',
    'specific_data.data.os.type',
    'labels',
  ],
  users: [
    'adapters', 'specific_data.data.image', 'specific_data.data.username', 'specific_data.data.domain',
    'specific_data.data.is_admin', 'specific_data.data.last_seen', 'labels',
  ],
};

export const defaultFieldsExplorer = {
  devices: [
    'adapters', 'specific_data.data.hostname', 'specific_data.data.name', 'specific_data.data.device_serial',
    'specific_data.data.network_interfaces.ips', 'specific_data.data.network_interfaces.mac',
    'specific_data.data.last_used_users', 'labels',
  ],
  users: [
    'adapters', 'specific_data.data.username', 'specific_data.data.mail', 'specific_data.data.first_name',
    'specific_data.data.last_name', 'labels',
  ],
};

export const guiPluginName = 'gui';

export const initCustomData = (module) => ({
  action_if_exists: 'update',
  association_type: 'Tag',
  data: {
    id: 'unique',
  },
  entity: module,
  name: guiPluginName,
  plugin_name: guiPluginName,
  plugin_unique_name: guiPluginName,
  type: 'adapterdata',
  id: 'gui_unique',
});

export const defaultViewForReset = (module, fields) => ({
  module,
  view: {
    enforcement: null,
    query: {
      filter: '',
      expressions: [],
      search: null,
      meta: {
        uniqueAdapters: false,
        enforcementFilter: null,
      },
    },
    sort: {
      field: '',
      desc: true,
    },
    fields,
    colFilters: {},
    colExcludedAdapters: {},
    page: 0,
  },
  selectedView: null,
});

export const ModalActionsEnum = {
  tag: 'tag',
  delete: 'delete',
  link: 'link',
  unlink: 'unlink',
  enforce: 'enforce',
  filter_out_from_query_result: 'filter_out',
  add_custom_data: 'add_custom_data',
};

export const ActionModalComponentByNameEnum = {
  [ModalActionsEnum.tag]: 'XTagModal',
  [ModalActionsEnum.delete]: 'XDeleteModal',
  [ModalActionsEnum.link]: 'XLinkModal',
  [ModalActionsEnum.unlink]: 'XUnlinkModal',
  [ModalActionsEnum.enforce]: 'XEnforceModal',
  [ModalActionsEnum.filter_out_from_query_result]: 'XFilterOutModal',
  [ModalActionsEnum.add_custom_data]: 'XAddCustomDataModal',
};
