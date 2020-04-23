import shortid from 'shortid';
import _omit from 'lodash/omit';
import _size from 'lodash/size';
import _get from 'lodash/get';
import { pluginMeta } from '../../constants/plugin_meta';
import { REQUEST_API } from '../actions';

export const HINT_ADAPTER_UP = 'HINT_ADAPTER_UP';
export const FETCH_ADAPTERS = 'FETCH_ADAPTERS';
export const LAZY_FETCH_ADAPTERS = 'LAZY_FETCH_ADAPTERS';
export const SET_ADAPTERS = 'SET_ADAPTERS';
export const FETCH_ADAPTERS_CLIENT_LABELS = 'FETCH_ADAPTERS_CLIENT_LABELS';
export const SET_ADAPTERS_CLIENT_LABELS = 'SET_ADAPTERS_CLIENT_LABELS';
export const SAVE_ADAPTER_CLIENT = 'SAVE_ADAPTER_CLIENT';
export const TEST_ADAPTER_SERVER = 'TEST_ADAPTER_SERVER';
export const UPDATE_ADAPTER_CLIENT = 'UPDATE_ADAPTER_CLIENT';
export const ARCHIVE_CLIENT = 'ARCHIVE_CLIENT';
export const REMOVE_CLIENT = 'REMOVE_CLIENT';

export const UPDATE_EXISTING_CLIENT = 'UPDATE_EXISTING_CLIENT';
export const ADD_NEW_CLIENT = 'ADD_NEW_CLIENT';

export const CLEAR_ADAPTERS_STATE = 'CLEAR_ADAPTERS_STATE';

export const UPDATE_ADAPTER_STATUS = 'UPDATE_ADAPTER_STATUS';

export const adapters = {
  state: {
    adapters: {
      fetching: false,
      data: [],
      error: '',
    },
    instances: [],
    clients: [],
    connectionLabels: [],
  },
  mutations: {
    [SET_ADAPTERS](state, payload) {
      // Called first before API request for adapters,
      // in order to update state to fetching.
      // Called again after API call returns with either error or result controls,
      // that is added to adapters list

      const newStateAdapters = [];
      const newStateInstances = [];
      let newStateClients = [];

      function getAllClientsData(aggregatedInstanceData, currentInstance) {
        const { clients: currentInstanceClients } = currentInstance;
        const currentInstanceClientsCount = currentInstanceClients.length;

        let instanceSuccessClients = 0;
        let instanceFailClients = 0;


        currentInstanceClients.forEach((c) => {
          const { status } = c;
          instanceSuccessClients = status === 'success' ? instanceSuccessClients + 1 : instanceSuccessClients;
          instanceFailClients = status === 'error' ? instanceFailClients + 1 : instanceFailClients;
        });

        const {
          countClients, successClients, errorClients, clients,
        } = aggregatedInstanceData;
        return {
          clients: [...clients, ...currentInstanceClients],
          countClients: countClients + currentInstanceClientsCount,
          errorClients: errorClients + instanceFailClients,
          successClients: successClients + instanceSuccessClients,
        };
      }


      const { data, fetching, error } = payload;
      state.adapters.fetching = fetching;

      if (data) {
        for (const [name, currentAdapter] of Object.entries(data)) {
          let adapter = {};
          let instance = {};

          const adapterMetaData = pluginMeta[name] || {};


          // get all clients data from all Instances
          const aggregatedClientsData = currentAdapter.reduce(getAllClientsData, {
            clients: [],
            successClients: 0,
            errorClients: 0,
            countClients: 0,
          });

          const {
            countClients, successClients, errorClients, clients: clientsList,
          } = aggregatedClientsData;

          // Itterate through Instances
          currentAdapter.forEach((a) => {
            const {
              config, node_id, node_name, schema, status, supported_features,
            } = a;
            adapter = {
              id: name,
              title: adapterMetaData.title || name,
              description: adapterMetaData.description || '',
              link: adapterMetaData.link,
              config,
              status: countClients && countClients === successClients ? 'success' : countClients ? 'warning' : '',
              schema,
              supported_features,
              clients: clientsList.map((c) => c.uuid),
              countClients,
              successClients,
              errorClients,
              instances: currentAdapter.map((a) => a.node_id),
            };

            instance = {
              node_id,
              node_name,
            };

            if (!newStateInstances.find((i) => i.node_id === node_id)) {
              newStateInstances.push(instance);
            }
            newStateClients = [...newStateClients, ...clientsList];
          });
          newStateAdapters.push(adapter);
        }

        // It is essential to replace the data in the state here so it is not accumulated
        state.adapters.data = newStateAdapters;
        state.instances = newStateInstances;
        state.clients = newStateClients;

        state.adapters.data.sort((first, second) => {
          // Sort by adapters plugin name (the one that is shown in the gui).
          const firstText = first.title.toLowerCase();
          const secondText = second.title.toLowerCase();
          if (firstText < secondText) return -1;
          if (firstText > secondText) return 1;
          return 0;
        });
      }

      if (error) {
        state.adapters.error = payload.error;
      }
    },
    [ADD_NEW_CLIENT](state, payload) {
      const { adapterId, ...newClient } = payload;

      const newAdaptersList = state.adapters.data.map((adapter) => {
        if (adapterId !== adapter.id) {
          return adapter;
        }
        return {
          ...adapter,
          client: adapter.clients.push(newClient.uuid),
          status: 'warning',
        };
      });
      newClient.adapter_name = adapterId;
      state.adapters.data = newAdaptersList;
      state.clients.push(newClient);
    },
    [UPDATE_EXISTING_CLIENT](state, payload) {
      // update exsiting client
      const { adapterId, uuidToSwap = payload.uuid, ...updatedClient } = payload;
      const clientStatus = updatedClient.status;
      const newAdaptersList = state.adapters.data.map((adapter) => {
        if (adapterId !== adapter.id) {
          return adapter;
        }

        const { clients } = adapter;

        const replaceClientAtIndex = clients.findIndex((c) => uuidToSwap === c);
        const newClientsList = clients.map((c, index) => {
          if (index !== replaceClientAtIndex) {
            return c;
          }
          return updatedClient.uuid;
        });

        const { errorClients, successClients } = adapter;
        return {
          ...adapter,
          countClients: adapter.countClients + 1,
          errorClients: clientStatus !== 'success' ? errorClients + 1 : errorClients,
          successClients: successClients === 'success' ? successClients + 1 : successClients,
          clients: newClientsList,
        };
      });

      state.adapters.data = newAdaptersList;
      _omit(updatedClient, ['uuidToSwap']);
      updatedClient.adapter_name = adapterId;
      state.clients = state.clients.map((client) => {
        if (client.uuid === uuidToSwap) {
          return updatedClient;
        }
        return client;
      });
    },
    [REMOVE_CLIENT](state, { clientId, adapterId }) {
      const newAdaptersList = state.adapters.data.map((adapter) => {
        if (adapterId !== adapter.id) {
          return adapter;
        }

        const { clients } = adapter;

        const replaceClientAtIndex = clients.findIndex((c) => clientId === c);
        const newClientsList = clients.filter((c, index) => index !== replaceClientAtIndex);

        return {
          ...adapter,
          clients: newClientsList,
        };
      });

      state.adapters.data = newAdaptersList;
      state.clients = state.clients.filter((c) => c.uuid !== clientId);
    },
    [UPDATE_ADAPTER_STATUS](state, adapterId) {
      state.adapters.data = state.adapters.data.map((adapter) => {
        if (adapter.id !== adapterId) {
          return adapter;
        }
        return {
          ...adapter,
          status: 'warning',
        };
      });
    },
    [SET_ADAPTERS_CLIENT_LABELS](state, payload) {
      const { data } = payload;
      if (data) {
        state.connectionLabels = data;
      }
    },
  },
  actions: {
    [FETCH_ADAPTERS]({ dispatch }, payload) {
      // Fetch all adapters, according to given filter
      let param = '';
      if (payload && payload.filter) {
        param = `?filter=${JSON.stringify(payload.filter)}`;
      }
      return dispatch(REQUEST_API, {
        rule: `adapters${param}`,
        type: SET_ADAPTERS,
      });
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
      const instance = getters.getInstancesMap.get(instanceId);
      const isNewClient = payload.uuid === 'new';
      const uniqueTmpId = isNewClient ? shortid.generate() : null;

      // why is that? the status can be changed, and the client can be added,
      // right after the API response with the status 200
      // that way, if the server operation failed, the data will remain not updated.
      // Moreover, why is it looks like the client id is being changed after update?!
      // if we want to change the status we can use designated mutation
      const client = {
        client_id: payload.clientId,
        adapterId: payload.adapterId,
        client_config: serverData,
        uuid: isNewClient ? uniqueTmpId : payload.uuid,
        status: 'warning',
        node_id: instance.node_id,
        error: null,
      };

      if (isNewClient) {
        commit(ADD_NEW_CLIENT, client);
      } else {
        commit(UPDATE_EXISTING_CLIENT, client);
      }

      const baseRulePath = 'adapters/connections';
      return dispatch(REQUEST_API, {
        rule: isNewClient ? baseRulePath : `${baseRulePath}/${payload.uuid}`,
        method: isNewClient ? 'PUT' : 'POST',
        data: {
          adapter: payload.adapterId,
          connection: payload.serverData,
          connection_label: payload.connectionLabel,
          instance: instanceId,
          instance_prev: instanceIdPrev,
        },
      })
        .then((response) => {
          commit(UPDATE_EXISTING_CLIENT, {
            client_id: response.data.client_id,
            adapterId: payload.adapterId,
            client_config: payload.serverData,
            uuidToSwap: isNewClient ? uniqueTmpId : payload.uuid,
            uuid: response.data.id,
            status: response.data.status,
            node_id: instance.node_id,
            error: response.data.error,
          });
          dispatch(FETCH_ADAPTERS_CLIENT_LABELS);
          return response;
        });
    },
    [TEST_ADAPTER_SERVER]({ dispatch }, payload) {
      // Call API to test connectivity to given connection configuration
      if (!payload || !payload.adapterId || !payload.serverData) {
        return Promise.resolve();
      }

      return dispatch(REQUEST_API, {
        rule: 'adapters/connections/test',
        method: 'post',
        data: {
          connection: payload.serverData,
          instance: payload.instanceName,
          adapter: payload.adapterId,
        },
      });
    },
    [ARCHIVE_CLIENT]({ dispatch, commit }, payload) {
      const {
        adapterId, serverId: clientId, deleteEntities, nodeId,
      } = payload;
      if (!adapterId || !clientId) {
        return Promise.resolve();
      }
      let param = '';
      if (deleteEntities) {
        param = '?deleteEntities=True';
      }
      return dispatch(REQUEST_API, {
        rule: `adapters/connections/${clientId}${param}`,
        method: 'DELETE',
        data: {
          adapter: adapterId,
          instance: nodeId,
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
        rule: 'adapters/connections/labels',
        type: SET_ADAPTERS_CLIENT_LABELS,
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
    getClientsMap: (state) => state.clients.reduce((map, client) => {
      map.set(client.uuid, client);
      return map;
    }, new Map()),
    getInstancesMap: (state) => state.instances.reduce((map, instance) => {
      map.set(instance.node_id, instance);
      return map;
    }, new Map()),
    getAdapterById: (state, getters) => (id) => {
      const pluginNameIndex = getters.getAdaptersMap;
      return pluginNameIndex.get(id);
    },
  },
};
