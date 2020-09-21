import shortid from 'shortid';
import _size from 'lodash/size';
import _get from 'lodash/get';
import { pluginMeta } from '../../constants/plugin_meta';
import { REQUEST_API } from '../actions';
import { CHANGE_PLUGIN_CONFIG } from '@store/modules/settings';

export const HINT_ADAPTER_UP = 'HINT_ADAPTER_UP';
export const FETCH_ADAPTERS = 'FETCH_ADAPTERS';
export const FETCH_ADAPTER_CONNECTIONS = 'FETCH_ADAPTER_CONNECTIONS';
export const SET_ADAPTER_CONNECTIONS = 'SET_ADAPTER_CONNECTIONS';
export const SET_ADAPTER_SCHEMA = 'SET_ADAPTER_SCHEMA';
export const FETCH_SELECTABLE_INSTANCES = 'FETCH_SELECTABLE_INSTANCES';
export const LAZY_FETCH_SELECTABLE_INSTANCES = 'LAZY_FETCH_SELECTABLE_INSTANCES'
export const LAZY_FETCH_ADAPTERS = 'LAZY_FETCH_ADAPTERS';
export const SET_ADAPTERS = 'SET_ADAPTERS';
export const SET_SELECTABLE_INSTANCES = 'SET_SELECTABLE_INSTANCES';
export const FETCH_ADAPTERS_CLIENT_LABELS = 'FETCH_ADAPTERS_CLIENT_LABELS';
export const SET_ADAPTERS_CLIENT_LABELS = 'SET_ADAPTERS_CLIENT_LABELS';
export const LAZY_FETCH_ADAPTERS_CLIENT_LABELS = 'LAZY_FETCH_ADAPTERS_CLIENT_LABELS';
export const SAVE_ADAPTER_CLIENT = 'SAVE_ADAPTER_CLIENT';
export const TEST_ADAPTER_SERVER = 'TEST_ADAPTER_SERVER';
export const ARCHIVE_CLIENT = 'ARCHIVE_CLIENT';
export const REMOVE_CLIENT = 'REMOVE_CLIENT';
export const LOAD_ADAPTER_CONFIG = 'LOAD_ADAPTER_CONFIG'

export const UPDATE_EXISTING_CLIENT = 'UPDATE_EXISTING_CLIENT';
export const ADD_NEW_CLIENT = 'ADD_NEW_CLIENT';


export const adapters = {
  state: {
    adapters: {
      fetching: false,
      data: [],
      error: '',
    },
    adapterSchemas: {},
    instances: {
      fetching: false,
      data: [],
      error: '',
    },
    clients: {},
    connectionLabels: [],
    tableFilter: {
      searchText: '',
      showOnlyConfigured: false,
    }
  },
  mutations: {
    [SET_ADAPTERS](state, payload) {
      // Called first before API request for adapters,
      // in order to update state to fetching.
      // Called again after API call returns with either error or result controls,
      // that is added to adapters list

      const newStateAdapters = [];
      const newStateInstances = new Map();

      const { data, fetching, error } = payload;
      state.adapters.fetching = fetching;

      if (error) {
        state.adapters.error = payload.error;
        return;
      }

      if (data) {
        // eslint-disable-next-line no-restricted-syntax
        for (const [name, currentAdapter] of Object.entries(data)) {
          let adapter = {};
          let instance = {};

          const adapterMetaData = pluginMeta[name] || {};


          const adapterInstancesIds = currentAdapter.map((adapterInstance) => adapterInstance.node_id);
          const adaptersClients = currentAdapter.reduce((clientsStat, adapterData) => ({
            count: clientsStat.count + adapterData.clients_count.total_count,
            success: clientsStat.success + adapterData.clients_count.success_count,
            error: clientsStat.success + adapterData.clients_count.error_count,
            inactive: clientsStat.inactive + adapterData.clients_count.inactive_count,
          }), {
            count: 0, success: 0, error: 0, inactive: 0,
          });

          let adapterStatus;
          if (adaptersClients.error) {
            adapterStatus = 'error';
          } else if (adaptersClients.success) {
            adapterStatus = 'success';
          } else if (adaptersClients.inactive) {
            adapterStatus = 'processing';
          }

          // Itterate through Instances
          // eslint-disable-next-line no-loop-func
          currentAdapter.forEach((a) => {
            const {
              config, node_id: instanceId, node_name: instanceName, schema,
              supported_features, unique_plugin_name
            } = a;
            adapter = {
              id: name,
              status: adapterStatus,
              title: adapterMetaData.title || name,
              description: adapterMetaData.description || '',
              link: adapterMetaData.link,
              config,
              schema,
              supported_features,
              instances: adapterInstancesIds,
              successClients: adaptersClients.success,
              errorClients: adaptersClients.error,
              inactiveClients: adaptersClients.inactive,
              clientsCount: adaptersClients.count,
              pluginUniqueName: unique_plugin_name,
            };

            instance = {
              node_id: instanceId,
              node_name: instanceName,
            };

            if (!newStateInstances.has(instanceId)) {
              newStateInstances.set(instanceName, instance);
            }
          });
          newStateAdapters.push(adapter);
        }

        // It is essential to replace the data in the state here so it is not accumulated
        state.adapters.data = newStateAdapters;
        state.instances.data = Array.from(newStateInstances.values());

        state.adapters.data.sort((first, second) => {
          // Sort by adapters plugin name (the one that is shown in the gui).
          const firstText = first.title.toLowerCase();
          const secondText = second.title.toLowerCase();
          if (firstText < secondText) return -1;
          if (firstText > secondText) return 1;
          return 0;
        });
      }
    },
    [SET_SELECTABLE_INSTANCES](state, payload) {
      const { data, fetching, error } = payload;
      state.instances.fetching = fetching;
      if (error) {
        state.instances.error = payload.error;
        return;
      }
      state.instances.data = data;
    },
    [SET_ADAPTER_CONNECTIONS](state, payload) {
      const { connections, adapterName } = payload;
      state.clients = {
        ...state.clients,
        [adapterName]: connections,
      };
    },
    [SET_ADAPTER_SCHEMA](state, payload) {
      const { schema, adapterName } = payload;

      if (!state.adapterSchemas[adapterName]) {
        state.adapterSchemas = {
          ...state.adapterSchemas,
          [adapterName]: schema,
        };
      }
    },
    [ADD_NEW_CLIENT](state, payload) {
      const { adapterId, ...newClient } = payload;

      const currentAdapterClientsList = state.clients[adapterId] || [];
      state.clients = {
        ...state.clients,
        [adapterId]: [...currentAdapterClientsList, { ...newClient, adapter_name: adapterId }],
      };
    },
    [UPDATE_EXISTING_CLIENT](state, payload) {
      // update exsiting client
      const { adapterId, uuidToSwap = payload.uuid, ...updatedClient } = payload;
      const adapterClientsList = state.clients[adapterId].map((client) => {
        if (client.uuid === uuidToSwap) {
          return {
            ...updatedClient,
            adapter_name: adapterId,
          };
        }
        return client;
      });
      state.clients = {
        ...state.clients,
        [adapterId]: adapterClientsList,
      };
    },
    [REMOVE_CLIENT](state, { clientId, adapterId }) {
      const adapterClientsList = state.clients[adapterId].filter((c) => c.uuid !== clientId);

      state.clients = {
        ...state.clients,
        [adapterId]: adapterClientsList,
      };
    },
    [SET_ADAPTERS_CLIENT_LABELS](state, payload) {
      const { data } = payload;
      if (data) {
        state.connectionLabels = data;
      }
    },
    setAdaptersTableFilter(state, payload) {
      state.tableFilter = {
        ...state.tableFilter,
        ...payload,
      };
    },
  },
  actions: {
    [FETCH_ADAPTERS]({ dispatch }, payload) {
      // Fetch all adapters, according to given filter
      let param = '';
      if (payload && payload.filter) {
        param = `?filter=${JSON.stringify(payload.filter)}&api_format=false`;
      } else {
        param = '?api_format=false';
      }
      return dispatch(REQUEST_API, {
        rule: `adapters${param}`,
        type: SET_ADAPTERS,
      });
    },
    [FETCH_SELECTABLE_INSTANCES]({ dispatch }) {
      return dispatch(REQUEST_API, {
        rule: 'instances/selectable_instances',
        type: SET_SELECTABLE_INSTANCES,
      });
    },
    [FETCH_ADAPTER_CONNECTIONS]({ dispatch, commit }, adapterName) {
      return new Promise((resolve, reject) => {
        dispatch(REQUEST_API, {
          rule: `adapters/${adapterName}/connections`,
          payload: { adapterName },
        })
          .then((res) => {
            commit(SET_ADAPTER_CONNECTIONS, { adapterName, connections: res.data.clients || [] });
            commit(SET_ADAPTER_SCHEMA, { schema: res.data.schema, adapterName });
            resolve(res.data);
          })
          .catch((ex) => reject(ex));
      });
    },
    [LAZY_FETCH_SELECTABLE_INSTANCES]({ dispatch, state }) {
      const instancesData = _get(state, 'instances.data', []);
      if (_size(instancesData)) {
        return Promise.resolve();
      }
      return dispatch(FETCH_SELECTABLE_INSTANCES);
    },
    [LAZY_FETCH_ADAPTERS]({ dispatch, state }) {
      const adaptersData = _get(state, 'adapters.data', []);
      if (_size(adaptersData)) {
        return Promise.resolve();
      }
      return dispatch(FETCH_ADAPTERS);
    },
    [SAVE_ADAPTER_CLIENT]({ dispatch, commit, getters }, payload) {
      // Call API to save given server controls to adapters by the given adapters id,
      // either adding a new server or updating and existing one,
      // if id is provided with the controls
      if (!payload || !payload.adapterId || !payload.serverData) {
        return Promise.resolve();
      }
      const { serverData, instanceId, instanceIdPrev } = payload;
      const newAssociatedInstance = getters.getInstancesMap.get(instanceId || instanceIdPrev);
      const oldAssociatedInstance = instanceIdPrev ? getters.getInstancesMap.get(instanceIdPrev) : '';
      const isNewClient = payload.uuid === 'new';
      const uniqueTmpId = isNewClient ? shortid.generate() : null;
      const isInstanceMode = getters.getInstancesMap.size > 1;

      // why is that? the status can be changed, and the client can be added,
      // right after the API response with the status 200
      // that way, if the server operation failed, the data will remain not updated.
      // Moreover, why is it looks like the client id is being changed after update?!
      // if we want to change the status we can use designated mutation
      const client = {
        client_id: payload.clientId,
        adapterId: payload.adapterId,
        client_config: serverData.client_config,
        connection_discovery: serverData.connection_discovery,
        connectionLabel: payload.connectionLabel,
        uuid: isNewClient ? uniqueTmpId : payload.uuid,
        active: payload.active,
        status: 'processing',
        node_id: newAssociatedInstance.node_id,
        error: null,
      };

      commit(isNewClient ? ADD_NEW_CLIENT : UPDATE_EXISTING_CLIENT, client);
      return new Promise(async (resolve, reject) => {
        const baseRulePath = `adapters/${payload.adapterId}/connections`;
        try {
          const response = await dispatch(REQUEST_API, {
            rule: isNewClient ? baseRulePath : `${baseRulePath}/${payload.uuid}`,
            method: isNewClient ? 'PUT' : 'POST',
            data: {
              connection: payload.serverData.client_config,
              connection_discovery: serverData.connection_discovery,
              connection_label: payload.connectionLabel,
              instance: newAssociatedInstance.node_id,
              instance_prev: instanceIdPrev,
              instance_name: newAssociatedInstance ? newAssociatedInstance.node_name : '' ,
              instance_prev_name: !isNewClient && oldAssociatedInstance
                ? oldAssociatedInstance.node_name : undefined,
              is_instances_mode: isInstanceMode,
              save_and_fetch: payload.fetchData,
              active: payload.active,
            },
          });

          commit(UPDATE_EXISTING_CLIENT, {
            client_id: response.data.client_id,
            adapterId: payload.adapterId,
            client_config: serverData.client_config,
            connection_discovery: serverData.connection_discovery,
            uuidToSwap: isNewClient ? uniqueTmpId : payload.uuid,
            uuid: response.data.id,
            active: response.data.active,
            status: response.data.status,
            node_id: newAssociatedInstance.node_id,
            node_name: newAssociatedInstance.node_name,
            error: response.data.error,
          });

          dispatch(FETCH_ADAPTERS_CLIENT_LABELS);

          resolve(response);
        } catch (err) {
          reject(err);
        }
      });
    },
    [TEST_ADAPTER_SERVER]({ dispatch }, payload) {
      // Call API to test connectivity to given connection configuration
      if (!payload || !payload.adapterId || !payload.serverData) {
        return Promise.resolve();
      }

      return dispatch(REQUEST_API, {
        rule: `adapters/${payload.adapterId}/connections/test`,
        method: 'post',
        data: {
          connection: payload.serverData.client_config,
          instance: payload.instanceName,
          adapter: payload.adapterId,
        },
      });
    },
    [ARCHIVE_CLIENT]({ dispatch, commit, getters }, payload) {
      const {
        adapterId, serverId: clientId, deleteEntities, nodeId,
      } = payload;
      if (!adapterId || !clientId) {
        return Promise.resolve();
      }
      const instance = getters.getInstancesMap.get(nodeId);
      const isInstanceMode = getters.getInstancesMap.size > 1;

      let param = '';
      if (deleteEntities) {
        param = '?deleteEntities=True';
      }
      return dispatch(REQUEST_API, {
        rule: `adapters/${adapterId}/connections/${clientId}${param}`,
        method: 'DELETE',
        data: {
          adapter: adapterId,
          instance: nodeId,
          instance_name: instance ? instance.node_name : '',
          is_instances_mode: isInstanceMode,
          connection: null,
        },
      }).then((response) => {
        if (response.status !== 200) {
          return;
        }
        commit(REMOVE_CLIENT, {
          clientId,
          adapterId,
        });
        dispatch(FETCH_ADAPTERS_CLIENT_LABELS);
      });
    },
    [HINT_ADAPTER_UP]({ dispatch }, adapterId) {
      dispatch(REQUEST_API, {
        rule: `adapters/hint_raise/${adapterId}`,
        method: 'POST',
      });
    },
    [FETCH_ADAPTERS_CLIENT_LABELS]({ dispatch }) {
      return dispatch(REQUEST_API, {
        rule: 'adapters/labels',
        type: SET_ADAPTERS_CLIENT_LABELS,
      });
    },
    [LAZY_FETCH_ADAPTERS_CLIENT_LABELS]({ dispatch, state }) {
      const connectionLabelsData = _get(state, 'connectionLabels', []);
      if (_size(connectionLabelsData)) {
        return Promise.resolve();
      }
      return dispatch(FETCH_ADAPTERS_CLIENT_LABELS);
    },
    [LOAD_ADAPTER_CONFIG]({ dispatch }, payload) {
      /*
          Call API to save given config to adapters by the given adapters unique name
       */
      if (!payload || !payload.pluginId || !payload.configName) return null;

      const rule = `adapters/${payload.pluginId}/${payload.configName}`;
      return dispatch(REQUEST_API, {
        rule,
        type: CHANGE_PLUGIN_CONFIG,
        payload,
      });
    },
  },
  getters: {
    getAdaptersMap: (state) => {
      const byId = new Map();

      state.adapters.data.forEach((currentAdapter) => {
        byId.set(currentAdapter.id, currentAdapter);
      });

      return byId;
    },
    getInstancesMap: (state) => state.instances.data.reduce((map, instance) => {
      map.set(instance.node_id, instance);
      return map;
    }, new Map()),
    getAdapterById: (state, getters) => (id) => {
      const pluginNameIndex = getters.getAdaptersMap;
      return pluginNameIndex.get(id);
    },
    getConfiguredAdapters: (state) => {
      // configured adapter is one that has at least 1 client configured
      return state.adapters.data.filter((adapter) => adapter.clientsCount);
    },
  },
};
