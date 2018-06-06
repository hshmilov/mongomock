import {REQUEST_API} from '../actions'
import { pluginMeta } from '../../static.js'

export const FETCH_ADAPTERS = 'FETCH_ADAPTERS'
export const UPDATE_ADAPTERS = 'UPDATE_ADAPTERS'
export const UPDATE_CURRENT_ADAPTER = 'UPDATE_CURRENT_ADAPTER'

export const SAVE_ADAPTER_SERVER = 'SAVE_ADAPTER_SERVER'
export const UPDATE_ADAPTER_SERVER = 'UPDATE_ADAPTER_SERVER'
export const ARCHIVE_SERVER = 'ARCHIVE_SERVER'
export const REMOVE_SERVER = 'REMOVE_SERVER'

export const UPDATE_ADAPTER_STATUS = 'UPDATE_ADAPTER_STATUS'


export const adapter = {
	state: {
		/* All adapters */
		adapterList: {
			fetching: false, data: [], error: ''
		},

		currentAdapter: null
	},
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
					let pluginTitle = adapter.plugin_name
					let pluginDescription = ''
					if (pluginMeta[adapter.plugin_name]) {
						pluginDescription = pluginMeta[adapter.plugin_name].description
						pluginTitle = pluginMeta[adapter.plugin_name].title
					}
					state.adapterList.data.push({
						...adapter,
						id: adapter.unique_plugin_name,
						title: pluginTitle,
						description: pluginDescription,
						supported_features: adapter.supported_features
					})
				})
				if (state.currentAdapter && state.currentAdapter.id) {
					state.currentAdapter = state.adapterList.data.find(
						adapter => adapter.unique_plugin_name === state.currentAdapter.id)
				}
			}
			if (payload.error) {
				state.adapterList.error = payload.error
			}
		},
		[ UPDATE_CURRENT_ADAPTER ] (state, adapterId) {
			state.currentAdapter = state.adapterList.data.find(adapter => adapter.unique_plugin_name === adapterId)
		},
		[ UPDATE_ADAPTER_SERVER ] (state, payload) {
			if (!payload.uuid) {
				state.currentAdapter.clients = [ payload, ...state.currentAdapter.clients]
				return
			}
			state.currentAdapter.clients.forEach((client, index) => {
				if (client.uuid === payload.uuid) {
					state.currentAdapter.clients[index] = payload
				}
			})
		},
		[ REMOVE_SERVER ] (state, serverId) {
			state.currentAdapter = {
				...state.currentAdapter,
				clients: state.currentAdapter.clients.filter((server) => {
					return server.uuid !== serverId
				})
			}
		},
		[ UPDATE_ADAPTER_STATUS ] (state, adapterId) {
			state.adapterList.data = state.adapterList.data.map((item) => {
				if (item.id !== adapterId) return item
				return { ...item, status: 'warning' }
			})
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
		[ SAVE_ADAPTER_SERVER ] ({dispatch, commit}, payload) {
			/*
				Call API to save given server controls to adapter by the given adapter id,
				either adding a new server or updating and existing one, if id is provided with the controls
			 */
			if (!payload || !payload.adapterId || !payload.serverData) { return }
			let rule = `adapters/${payload.adapterId}/clients`
			if (payload.uuid !== 'new') {
				rule += '/' + payload.uuid
			}
			commit(UPDATE_ADAPTER_SERVER, {
				client_config: payload.serverData,
				uuid: (payload.uuid !== 'new') ? payload.uuid: '',
				status: 'warning'
			})
			commit(UPDATE_ADAPTER_STATUS, payload.adapterId)

			return dispatch(REQUEST_API, {
				rule: rule,
				method: 'PUT',
				data: payload.serverData
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
