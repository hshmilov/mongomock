import { REQUEST_API } from '../actions'
import { pluginMeta } from '../../constants/plugin_meta.js'
import shortid from 'shortid'

export const HINT_ADAPTER_UP = 'HINT_ADAPTER_UP'
export const FETCH_ADAPTERS = 'FETCH_ADAPTERS'
export const INSERT_ADAPTERS = 'INSERT_ADAPTERS'

export const SAVE_ADAPTER_CLIENT = 'SAVE_ADAPTER_CLIENT'
export const TEST_ADAPTER_SERVER = 'TEST_ADAPTER_SERVER'
export const UPDATE_ADAPTER_CLIENT = 'UPDATE_ADAPTER_CLIENT'
export const ARCHIVE_CLIENT = 'ARCHIVE_CLIENT'
export const REMOVE_CLIENT = 'REMOVE_CLIENT'

export const UPDATE_EXISTING_CLIENT = 'UPDATE_EXISTING_CLIENT'
export const ADD_NEW_CLIENT = 'ADD_NEW_CLIENT'

export const CLEAR_ADAPTERS_STATE = 'CLEAR_ADAPTERS_STATE'

export const UPDATE_ADAPTER_STATUS = 'UPDATE_ADAPTER_STATUS'

export const adapters = {
	state: {
		adapters: {
			fetching: false, data: [], error: ''
		},
		instances: [],
		clients: [],
	},
	mutations: {
		[INSERT_ADAPTERS](state, payload) {

			/*
				Called first before API request for adapters, in order to update state to fetching
				Called again after API call returns with either error or result controls, that is added to adapters list
			 */

			const newStateAdapters = []
			const newStateInstances = []
			let newStateClients = []

			function getAllClientsData(aggregatedInstanceData, currentInstance) {

				const { clients: currentInstanceClients } = currentInstance
				const currentInstanceClientsCount = currentInstanceClients.length

				let instanceSuccessClients = 0
				let instanceFailClients = 0


				currentInstanceClients.forEach(c => {
					const { status } = c
					instanceSuccessClients = status === 'success' ? instanceSuccessClients + 1 : instanceSuccessClients
					instanceFailClients = status === 'error' ? instanceFailClients + 1 : instanceFailClients
				})

				const { countClients, successClients, errorClients, clients } = aggregatedInstanceData
				return {
					clients: [...clients, ...currentInstanceClients],
					countClients: countClients + currentInstanceClientsCount,
					errorClients: errorClients + instanceFailClients,
					successClients: successClients + instanceSuccessClients
				}
			}


			const { data, fetching, error } = payload
			state.adapters.fetching = fetching

			if (data) {
				for (let [name, currentAdapter] of Object.entries(data)) {
					let adapter = {}
					let instance = {}

					const adapterMetaData = pluginMeta[name] || {}
					

					// get all clients data from all Instances
					const aggregatedClientsData = currentAdapter.reduce(getAllClientsData, { clients: [], successClients: 0, errorClients: 0, countClients: 0 })

					const { countClients, successClients, errorClients, clients: clientsList } = aggregatedClientsData

					// Itterate through Instances
					currentAdapter.forEach(a => {
						const { config, node_id, node_name, schema, status, supported_features } = a
						adapter = {
							id: name,
							title: adapterMetaData.title || name,
							description: adapterMetaData.description || '',
							link: adapterMetaData.link,
							config,
							status: countClients && countClients === successClients ? 'success' : countClients ? 'warning' : '',
							schema,
							supported_features,
							clients: clientsList.map(c => c.uuid),
							countClients,
							successClients,
							errorClients,
							instances: currentAdapter.map(a => a.node_id)
						}

						instance = { node_id, node_name }
						
						if (!newStateInstances.find(i => i.node_id === node_id)) {
							newStateInstances.push(instance)
						}
						newStateClients = [...newStateClients, ...clientsList]
					})
					newStateAdapters.push(adapter)
				}

				//** It is essential to replace the data in the state here. If not, data will be accumulated  */
				state.adapters.data = newStateAdapters
				state.instances = newStateInstances
				state.clients = newStateClients

				state.adapters.data.sort((first, second) => {
					// Sort by adapters plugin name (the one that is shown in the gui).
					let firstText = first.title.toLowerCase()
					let secondText = second.title.toLowerCase()
					if (firstText < secondText) return -1
					if (firstText > secondText) return 1
					return 0
				})
			}

			if (error) {
				state.adapters.error = payload.error
			}
		},
		[ADD_NEW_CLIENT](state, payload){
			const { adapterId, ...newClient } = payload

			const newAdaptersList = state.adapters.data.map(adapter => {
				if (adapterId !== adapter.id) {
					return adapter
				}
				return  {
					...adapter,
					client: adapter.clients.push(newClient.uuid),
					status: 'warning'
				}
			})

			state.adapters.data = newAdaptersList
			state.clients.push(newClient)

		},
		[UPDATE_EXISTING_CLIENT](state, payload){
			// update exsiting client
			const { adapterId, uuidToSwap = payload.uuid, status: clientStatus, ...updatedClient } = payload

			const newAdaptersList = state.adapters.data.map(adapter => {
				if (adapterId !== adapter.id) {
					return adapter
				}

				const { clients } = adapter

				const replaceClientAtIndex = clients.findIndex(c => uuidToSwap === c)
				const newClientsList = clients.map((c, index) => {
					if (index !== replaceClientAtIndex) {
						return c
					}
					return updatedClient.uuid
				})

				const { errorClients, successClients } = adapter
				return {
					...adapter,
					countClients: adapter.countClients + 1,
					errorClients: clientStatus !== 'success' ? errorClients + 1 : errorClients,
					successClients: successClients === 'success' ? successClients + 1 : successClients,
					clients: newClientsList
				}
			})

			state.adapters.data = newAdaptersList

			state.clients.push({...updatedClient, status: clientStatus})
		},
		[REMOVE_CLIENT](state, { clientId, adapterId }) {

			const newAdaptersList = state.adapters.data.map(adapter => {
				if (adapterId !== adapter.id) {
					return adapter
				}

				const { clients } = adapter

				const replaceClientAtIndex = clients.findIndex(c => clientId === c)
				const newClientsList = clients.filter((c, index) => index !== replaceClientAtIndex)

				return {
					...adapter,
					clients: newClientsList
				}
			})

			state.adapters.data = newAdaptersList
			state.clients = state.clients.filter(c => c.uuid !== clientId)
		},
		[UPDATE_ADAPTER_STATUS](state, adapterId) {
			state.adapters.data = state.adapters.data.map((adapter) => {
				if (adapter.id !== adapterId) {
					return adapter
				} 
				return { ...adapter, status: 'warning' }
			})
		}
	},
	actions: {
		[FETCH_ADAPTERS]({ dispatch, commit }, payload) {
			/*
				Fetch all adapters, according to given filter
			 */
			let param = ''
			if (payload && payload.filter) {
				param = `?filter=${JSON.stringify(payload.filter)}`
			}
			return dispatch(REQUEST_API, {
				rule: `adapters${param}`,
				type: INSERT_ADAPTERS
			})
		},
		[SAVE_ADAPTER_CLIENT]({ dispatch, commit, getters }, payload) {
			/*
				Call API to save given server controls to adapters by the given adapters id,
				either adding a new server or updating and existing one, if id is provided with the controls
			 */
			const { serverData } = payload
			const { instanceName: instanceId } = serverData

			const instance = getters.getInstancesMap.get(instanceId)
			if (!payload || !payload.adapterId || !payload.serverData) { 
				return 
			}

			const isNewClient = payload.uuid === 'new'
			const baseRulePath = `adapters/${payload.adapterId}/clients`
			let rule = isNewClient ? baseRulePath : `${baseRulePath}/${payload.uuid}`
			const uniqueTmpId = isNewClient ? shortid.generate() : null

			// why is that? the status can be changed, and the client can be added, right after the API response with
			// the status 200
			// that way, if the server operation failed, the data will remain not updated.
			// Moreover, why is it looks like the client id is being changed after update?!
			// if we want to change the status we can use designated mutation

			const client = {
				adapterId: payload.adapterId,
				client_config: payload.serverData,
				uuid: isNewClient ? uniqueTmpId : payload.uuid,
				...instance,
				status: 'warning'
			}

			if (isNewClient) {
				commit(ADD_NEW_CLIENT, client)
			} else {
				commit(UPDATE_EXISTING_CLIENT, client)
			}

			return dispatch(REQUEST_API, {
				rule: rule,
				method: 'PUT',
				data: payload.serverData
			}).then(response => {
				commit(UPDATE_EXISTING_CLIENT, {
					adapterId: payload.adapterId,
					uuidToSwap: isNewClient ? uniqueTmpId : payload.uuid,
					uuid: response.data.id,
					status: response.data.status,
					client_config: payload.serverData,
					error: response.data.error,
					node_id: instance.node_id
				})
				return response
			})
		},
		[TEST_ADAPTER_SERVER]({ dispatch }, payload) {
            /*
                Call API to test connectivity to given server controls to adapters by the given adapters id,
                either adding a new server or updating and existing one, if id is provided with the controls
             */
			if (!payload || !payload.adapterId || !payload.serverData) { return }
			let rule = `adapters/${payload.adapterId}/clients`

			return dispatch(REQUEST_API, {
				rule: rule,
				method: 'post',
				data: payload.serverData
			})
		},
		[ARCHIVE_CLIENT]({ dispatch, commit }, payload) {
			const { adapterId, serverId: clientId, deleteEntities, nodeId } = payload 
			if (!adapterId || !clientId) { 
				return 
			}
			let param = ''
			if (deleteEntities) {
				param = '?deleteEntities=True'
			}
			dispatch(REQUEST_API, {
				rule: `adapters/${adapterId}/clients/${clientId}${param}`,
				method: 'DELETE',
				data: { instanceName: nodeId }
			}).then((response) => {
				if (response.data !== '') {
					return
				}
				commit(REMOVE_CLIENT, { clientId, adapterId })
			})
		},
		[ HINT_ADAPTER_UP ] ({dispatch, commit}, adapterId) {
			dispatch(REQUEST_API, {
				rule: `adapters/hint_raise/${adapterId}`,
				method: 'POST',
			})
		}
	},
	getters: {
		getAdaptersMap: state => {
			const byId = new Map()

			state.adapters.data.forEach(currentAdapter => {
				byId.set(currentAdapter.id, currentAdapter)
			})

			return byId
		},
		getClientsMap: (state) => {
			return state.clients.reduce((map, client) => {
				map.set(client.uuid, client)
				return map
			}, new Map())
		},
		getInstancesMap: (state) => {
			return state.instances.reduce((map, instance) => {
				map.set(instance.node_id, instance)
				return map
			}, new Map())
		},
		getAdapterById: (state, getters) => id => {
			const pluginNameIndex = getters.getAdaptersMap
			return pluginNameIndex.get(id)
		}
	}
}
