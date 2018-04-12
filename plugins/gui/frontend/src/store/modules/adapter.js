import {REQUEST_API} from '../actions'
import { pluginMeta } from '../../static.js'

export const FETCH_ADAPTERS = 'FETCH_ADAPTERS'
export const UPDATE_ADAPTERS = 'UPDATE_ADAPTERS'
export const FETCH_ADAPTER_SERVERS = 'FETCH_ADAPTER_SERVERS'
export const SET_ADAPTER_SERVERS = 'SET_ADAPTER_SERVERS'
export const SAVE_ADAPTER_SERVER = 'SAVE_ADAPTER_SERVER'
export const ADD_ADAPTER_SERVER = 'ADD_ADAPTER_SERVER'
export const UPDATE_ADAPTER_SERVER = 'UPDATE_ADAPTER_SERVER'
export const ARCHIVE_SERVER = 'ARCHIVE_SERVER'
export const REMOVE_SERVER = 'REMOVE_SERVER'
export const adapter = {
	state: {
		/* All adapters */
		adapterList: {
			fetching: false, data: [], error: ''
		},

		/* Statically defined fields that should be presented for each adapter, in this order  */
		adapterFields: [
			{path: 'unique_plugin_name', name: '', hidden: true},
			{path: 'plugin_name', name: 'Name', type: 'status-icon-logo-text'},
			{path: 'description', name: 'Description'},
			{path: 'status', name: '', hidden: true}
		],

		/* Data about a specific adapter that is currently being configured */
		currentAdapter: {
			fetching: false, data: {}, error: ''
		}
	},
	getters: {},
	mutations: {
		[ UPDATE_ADAPTERS ] (state, payload) {
			/*
				Called first before API request for adapters, in order to update state to fetching
				Called again after API call returns with either error or result controls, that is added to adapters list
			 */
			state.adapterList.fetching = payload.fetching
			if (payload.data) {
				state.adapterList.data = []
				payload.data.forEach((adapter) => {
					let pluginText = adapter.plugin_name
					let pluginDescription = ''
					if (pluginMeta[adapter.plugin_name]) {
						pluginText = pluginMeta[adapter.plugin_name].title
						pluginDescription = pluginMeta[adapter.plugin_name].description
					}
					state.adapterList.data.push({
						...adapter,
						id: adapter.unique_plugin_name,
						plugin_name: {
							text: pluginText,
							logo: adapter.plugin_name,
							status: adapter.status
						},
						description: pluginDescription,
						supported_features: adapter.supported_features
					})
				})
			}
			if (payload.error) {
				state.adapterList.error = payload.error
			}
		},
		[ SET_ADAPTER_SERVERS ] (state, payload) {
			/*
				Called first before API request for a specific adapter, in order to update state to fetching
				Called again after API call returns with either error or controls which is assigned to current adapter
			 */
			state.currentAdapter.fetching = payload.fetching
			state.currentAdapter.error = payload.error
			if (payload.data) {
				state.currentAdapter.data = {
					...state.currentAdapter.data, ...payload.data,
					clients: payload.data.clients.map((client) => {
						client['date_fetched'] = undefined
						return client
					})
				}

			}
		},
		[ ADD_ADAPTER_SERVER ] (state, payload) {
			state.currentAdapter.data = {...state.currentAdapter.data}
			state.currentAdapter.data.clients.push({...payload})
		},
		[ UPDATE_ADAPTER_SERVER ] (state, payload) {
			state.currentAdapter.data = {...state.currentAdapter.data}
			state.currentAdapter.data.clients.forEach((client, index) => {
				if (client.uuid === payload.uuid) {
					state.currentAdapter.data.clients[index] = {...payload}
				}
			})
		},
		[ REMOVE_SERVER ] (state, serverId) {
			state.currentAdapter.data = {
				...state.currentAdapter.data,
				clients: state.currentAdapter.data.clients.filter((server) => {
					return server.uuid !== serverId
				})
			}
		}
	},
	actions: {
		[ FETCH_ADAPTERS ] ({dispatch}, payload) {
			/*
				Fetch all adapters, according to given filter
			 */
			let param = ''
			if (payload && payload.filter) {
				param = `?filter=${JSON.stringify(payload.filter)}`
			}
			return dispatch(REQUEST_API, {
				rule: `adapters${param}`,
				type: UPDATE_ADAPTERS
			})
		},
		[ FETCH_ADAPTER_SERVERS ] ({dispatch}, adapterId) {
			/*
				Fetch a single adapter with all its clients and schema and stuff, according to given id
			 */
			if (!adapterId) { return }
			dispatch(REQUEST_API, {
				rule: `adapters/${adapterId}/clients`,
				type: SET_ADAPTER_SERVERS
			})
		},
		[ SAVE_ADAPTER_SERVER ] ({dispatch, commit}, payload) {
			/*
				Call API to save given server controls to adapter by the given adapter id,
				either adding a new server or updating and existing one, if id is provided with the controls
			 */
			if (!payload || !payload.adapterId || !payload.serverData) { return }
			let rule = `adapters/${payload.adapterId}/clients`
			if (payload.uuid !== 'new') {
				rule += '/' + payload.uuid

                commit(UPDATE_ADAPTER_SERVER, {
                    client_config: payload.serverData,
                    uuid: payload.uuid,
                    status: 'warning',
                })
			}
			else {
                commit(ADD_ADAPTER_SERVER, {
                    status: 'warning',
                    client_config: payload.serverData
                })
			}

			dispatch(REQUEST_API, {
				rule: rule,
				method: 'PUT',
				data: payload.serverData
			}).then(() => {
				dispatch(FETCH_ADAPTER_SERVERS, payload.adapterId)
			})
		},
		[ ARCHIVE_SERVER ] ({dispatch, commit}, payload) {
			if (!payload.adapterId || !payload.serverId) { return }
			dispatch(REQUEST_API, {
				rule: `adapters/${payload.adapterId}/clients/${payload.serverId}`,
				method: 'DELETE'
			}).then((response) => {
				if (response.data !== '') {
					return
				}
				commit(REMOVE_SERVER, payload.serverId)
			})
		}
	}
}
