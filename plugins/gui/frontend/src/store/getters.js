import _get from 'lodash/get';
import _isEmpty from 'lodash/isEmpty';
import _snakeCase from 'lodash/snakeCase';
import { defaultFields } from '@constants/entities';
import { pluginMeta } from '../constants/plugin_meta';
import { isObjectListField } from '../constants/utils';
import { DEFAULT_DATE_FORMAT } from './modules/constants';

const selectFields = (schema, objectView) => (objectView
  ? schema.filter(isObjectListField)
  : schema);

function sortPlugins(first, second) {
  // Sort by adapters plugin name (the one that is shown in the gui).
  const firstText = first.title.toLowerCase();
  const secondText = second.title.toLowerCase();
  if (firstText < secondText) return -1;
  if (firstText > secondText) return 1;
  return 0;
}

function getConnectionLabelSchema(fieldPrefix) {
  return {
    name: `${fieldPrefix}.connection_label`,
    title: 'Adapter Connection Label',
    type: 'string',
    enum: [],
    source: {
      key: 'all-connection-labels',
      options: {
        'allow-custom-option': false,
      },
    },
  };
}

function getModuleSchemaFields(fieldsSpecific, fieldsGeneric, fieldsSchema,
  objectView, filterPlugins, includeConnectionLabel) {
  if (_isEmpty(fieldsGeneric) || (objectView && _isEmpty(fieldsSchema))) {
    return [];
  }
  const plugins = Object.keys(fieldsSpecific)
    .map((name) => {
      const title = pluginMeta[name] ? pluginMeta[name].title : name;
      return {
        title,
        name,
      };
    });
  const aggregated = {
    name: 'axonius',
    title: 'Aggregated',
    fields: selectFields([...(includeConnectionLabel
      ? [getConnectionLabelSchema('specific_data')] : []), ...fieldsGeneric], objectView),
  };
  if (filterPlugins) {
    aggregated.plugins = plugins.sort(sortPlugins);
  }
  const sortedPluginFields = plugins.map((plugin) => ({
    ...plugin,
    fields: selectFields([...(includeConnectionLabel
      ? [getConnectionLabelSchema(`adapters_data.${plugin.name}`)] : []), ...fieldsSpecific[plugin.name]], objectView),
  })).sort(sortPlugins);
  return [aggregated, ...sortedPluginFields];
}

export const GET_MODULE_SCHEMA = 'GET_MODULE_SCHEMA';
export const getModuleSchema = (state) => (module, objectView = false, filterPlugins = false) => {
  const fields = _get(state[module], 'fields.data', {});
  return getModuleSchemaFields(fields.specific, fields.generic, fields.schema, objectView, filterPlugins, false);
};

export const GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL = 'GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL';
export const getModuleSchemaWithConnectionLabel = (state) => (module, objectView = false, filterPlugins = false) => {
  const generic = _get(state[module], 'fields.data.generic', []);
  const specific = _get(state[module], 'fields.data.specific', []);
  const schema = _get(state[module], 'fields.data.schema', {});

  return getModuleSchemaFields(specific, generic, schema, objectView, filterPlugins, true);
};

export const GET_MODULE_FIELDS = 'GET_MODULE_FIELDS';
export const getModuleFields = (state) => (module) => {
  const excludedFields = ['adapter_list_length'];
  const generic = _get(state[module], 'fields.data.generic', []);
  const specific = _get(state[module], 'fields.data.specific', []);
  const allFields = [generic, ...Object.values(specific)].flat().map((field) => field.name);
  return allFields.filter((name) => !excludedFields.includes(name));
};

export const GET_DATA_SCHEMA_LIST = 'GET_DATA_SCHEMA_LIST';
export const getDataSchemaList = (state) => (module) => {
  const fields = state[module].fields.data;
  if (!fields.generic || !fields.generic.length) return [];

  const genericFieldsList = [getConnectionLabelSchema('specific_data'), ...fields.generic];
  if (!fields.specific) {
    return genericFieldsList;
  }
  const addFieldLogo = (logo) => (field) => ({ ...field, logo });
  return Object.entries(fields.specific)
    .reduce((fieldsList, [specificName, currentList]) => fieldsList
      .concat([getConnectionLabelSchema(`adapters_data.${specificName}`), ...currentList]
        .map(addFieldLogo(specificName))), genericFieldsList);
};

export const GET_DATA_SCHEMA_BY_NAME = 'GET_DATA_SCHEMA_BY_NAME';
export const getDataSchemaByName = (state) => (module) => getDataSchemaList(state)(module).reduce((map, schema) => {
  map[schema.name] = schema;
  return map;
}, {});

export const AUTO_QUERY = 'AUTO_QUERY';
export const autoQuery = (state) => {
  if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return true;
  return state.configuration.data.system.autoQuery && !state.configuration.data.system.cache_settings.enabled;
};

export const EXACT_SEARCH = 'EXACT_SEARCH';
export const exactSearch = (state) => {
  if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return false;
  return state.configuration.data.system.exactSearch;
};

export const REQUIRE_CONNECTION_LABEL = 'REQUIRE_CONNECTION_LABEL';
export const requireConnectionLabel = (state) => {
  if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return false;
  return state.configuration.data.system.requireConnectionLabel;
};

export const IS_EXPIRED = 'IS_EXPIRED';
export const isExpired = (state) => {
  const username = _get(state, 'auth.currentUser.data.user_name');
  return state.expired.data && username !== '_axonius';
};

export const DATE_FORMAT = 'DATE_FORMAT';
export const dateFormat = (state) => {
  if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return DEFAULT_DATE_FORMAT;
  return state.configuration.data.system.datetime_format;
};

export const GET_CONNECTION_LABEL = 'GET_CONNECTION_LABEL';
export const getConnectionLabel = (state) => (clientId, adapterProps) => {
  if (!clientId) {
    return '';
  }
  const matchClient = (label) => label.client_id === clientId;
  const matchAdapterProps = (label) => Object.keys(adapterProps).reduce((matches, prop) => (
    matches && label[prop] === adapterProps[prop]), true);
  const connectionLabels = _get(state, 'adapters.connectionLabels', []);
  const matchLabel = (label) => matchClient(label) && matchAdapterProps(label)
  const foundLabel = connectionLabels.find(matchLabel);
  return foundLabel ? foundLabel.label : '';
};

const savedQueries = (state, namespace) => {
  const data = state[namespace].views.saved.content.data || [];
  return data.filter((view) => view);
};

export const getSavedQueryById = (state) => (id, namespace) => savedQueries(state, namespace).find((q) => id === q.uuid);

export const GET_SAVED_QUERY_BY_NAME = 'getSavedQueryByName';
export const getSavedQueryByName = (state) => (name, namespace) => {
  const result = savedQueries(state, namespace).find((q) => name === q.name);
  return result ? result.uuid : '';
}

export const GET_FOOTER_MESSAGE = 'GET_FOOTER_MESSAGE';
export const getFooterMessage = (state) => state.footer.message;

export const configuredAdaptersFields = (state) => (entity) => {
  // entity can be 'devices' either 'users'
  const entityState = state[entity];

  const genericFields = _get(entityState, 'fields.data.generic', [])
    .map((f) => f.name);
  const adaptersSpecificFields = _get(entityState, 'fields.data.specific', {});

  const configuredAdaptersSchemas = Object.values(adaptersSpecificFields);
  const specificFields = configuredAdaptersSchemas.reduce((fields, currentAdaptersFields) => [
    ...fields,
    ...currentAdaptersFields.map((field) => field.name),
  ], Object.keys(adaptersSpecificFields));

  return new Set([...genericFields, ...specificFields]);
};

export const FILL_USER_FIELDS_GROUPS_FROM_TEMPLATES = 'FILL_USER_FIELDS_GROUPS_FROM_TEMPLATES';
export const fillUserFieldsGroupsFromTemplates = (state) => (module, userFieldsGroups) => {
  const fieldGroups = state[module].views.template.content.data.reduce((acc, curr) => {
    acc[_snakeCase(curr.name)] = curr.view.fields;
    return acc;
  }, {});
  return {
    ...fieldGroups,
    ...userFieldsGroups,
  };
};

export const GET_SYSTEM_COLUMNS = 'GET_SYSTEM_COLUMNS';
export const getSystemColumns = (state, getters) => (module, columnsGroupName = 'default') => {
  // get db saved system default group
  const fromDb = _get(state, `configuration.data.defaults.system_columns.${module}.table_columns`, {});
  return fromDb[columnsGroupName]
  || (module === 'devices' && getters.FILL_USER_FIELDS_GROUPS_FROM_TEMPLATES(module)[columnsGroupName])
  // get hardcoded system default group
  || defaultFields[module];
};
