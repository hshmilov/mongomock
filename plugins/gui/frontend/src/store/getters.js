import _get from 'lodash/get';
import _isEmpty from 'lodash/isEmpty';
import _snakeCase from 'lodash/snakeCase';
import { pluginMeta } from '../constants/plugin_meta';
import { isObjectListField } from '../constants/utils';

const selectFields = (schema, objectView) => (objectView
  ? schema.filter(isObjectListField)
  : schema);

function getModuleSchemaFields(fieldsSpecific, fieldsGeneric, fieldsSchema, objectView, filterPlugins) {
  if (_isEmpty(fieldsGeneric) || (objectView && _isEmpty(fieldsSchema))) {
    return [];
  }
  const plugins = Object.keys(fieldsSpecific)
    .map((name) => {
      const title = pluginMeta[name] ? pluginMeta[name].title : name
      return {
        title,
        name,
      };
    });
  const aggregated = {
    name: 'axonius',
    title: 'Aggregated',
    fields: selectFields(fieldsGeneric, objectView),
  };
  if (filterPlugins) {
    aggregated.plugins = plugins;
  }
  const sortedPluginFields = plugins.map((plugin) => ({
    ...plugin,
    fields: selectFields(fieldsSpecific[plugin.name], objectView),
  })).sort((first, second) => {
    // Sort by adapters plugin name (the one that is shown in the gui).
    const firstText = first.title.toLowerCase();
    const secondText = second.title.toLowerCase();
    if (firstText < secondText) return -1;
    if (firstText > secondText) return 1;
    return 0;
  });
  return [aggregated, ...sortedPluginFields];
}

export const CONNECTION_LABEL_SCHEMA = {
  name: 'specific_data.connection_label',
  title: 'Adapter Connection Label',
  type: 'string',
  enum: [],
  source: {
    key: 'all-connection-labels',
    options: {
      'allow-custom-option': false
    }
  }
}

export const GET_MODULE_SCHEMA = 'GET_MODULE_SCHEMA'
export const getModuleSchema = (state) => (module, objectView = false, filterPlugins = false) => {
  const fields = _get(state[module], 'fields.data' , {})
  return getModuleSchemaFields(fields.specific , fields.generic, fields.schema , objectView, filterPlugins);
}

export const GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL = 'GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL'
export const getModuleSchemaWithConnectionLabel = (state) => (module, objectView = false, filterPlugins = false) => {
  const fields = _get(state[module], 'fields.data', {})
  return getModuleSchemaFields(fields.specific , [CONNECTION_LABEL_SCHEMA,
    ...fields.generic], fields.schema, objectView, filterPlugins);
}

export const GET_DATA_SCHEMA_LIST = 'GET_DATA_SCHEMA_LIST';
export const getDataSchemaList = (state) => (module) => {
  const fields = state[module].fields.data;
  if (!fields.generic || !fields.generic.length) return [];

  let allFieldsList = [CONNECTION_LABEL_SCHEMA, ...fields.generic];
  if (fields.specific) {
    allFieldsList = Object.entries(fields.specific).reduce((aggregatedList, [specificName, currentList]) => {
      currentList.map((field) => field.logo = (singleAdapter(state) ? undefined : specificName));
      return aggregatedList.concat(currentList);
    }, allFieldsList);
  }
  return allFieldsList;
};

export const GET_DATA_SCHEMA_BY_NAME = 'GET_DATA_SCHEMA_BY_NAME';
export const getDataSchemaByName = (state) => (module) => getDataSchemaList(state)(module).reduce((map, schema) => {
  map[schema.name] = schema;
  return map;
}, {});

export const SINGLE_ADAPTER = 'SINGLE_ADAPTER';
export const singleAdapter = (state) => {
  if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return false;
  return state.configuration.data.system.singleAdapter;
};

export const AUTO_QUERY = 'AUTO_QUERY';
export const autoQuery = (state) => {
  if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return true;
  return state.configuration.data.system.autoQuery;
};

export const EXACT_SEARCH = 'EXACT_SEARCH';
export const exactSearch = (state) => {
  if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return false;
  return state.configuration.data.system.exactSearch;
};

export const REQUIRE_CONNECTION_LABEL = 'REQUIRE_CONNECTION_LABEL'
export const requireConnectionLabel = (state) => {
  if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return false
  return state.configuration.data.system.requireConnectionLabel
}

export const IS_EXPIRED = 'IS_EXPIRED';
export const isExpired = (state) => state.expired.data && state.auth.currentUser.data.user_name !== '_axonius';

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

export const GET_FOOTER_MESSAGE = 'GET_FOOTER_MESSAGE';
export const getFooterMessage = (state) => state.footer.message;

export const configuredAdaptersFields = (state) => (entity, customFieldsToInclude = []) => {
  // entity can be 'devices' either 'users'
  const entityState = state[entity];

  const genericFields = entityState.fields.data.generic.map((f) => f.name);
  const adaptersSpecificFields = entityState.fields.data.specific;

  const configuredAdaptesSchemas = Object.values(adaptersSpecificFields);
  const specificFields = configuredAdaptesSchemas.reduce((fields, currentAdaptersFields) => [
    ...fields,
    ...currentAdaptersFields.map((field) => field.name),
  ], Object.keys(adaptersSpecificFields));

  return new Set([...genericFields, ...specificFields, ...customFieldsToInclude]);
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
